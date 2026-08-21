"""Agronomy engine behind every irrigation decision.

This module is deliberately dependency-free (standard library + typing only) so
that it can be imported by three different places without circular imports:

1. ``ml/irrigation/generate_sample_dataset.py`` - to synthesise labelled rows.
2. ``ml/irrigation/train.py``                   - indirectly, through the dataset.
3. ``app/ml/irrigation_model.py``               - as the runtime fallback when no
   trained model file is present, and to build the human explanation that is
   shown alongside every machine-learning prediction.

The water balance is a simplified, transparent FAO-56 style calculation:

    net requirement = soil moisture deficit + one day of crop water use
                      - effective rainfall

Every coefficient below is a documented assumption, not a measured constant.
Replace them with values from your local agricultural university when you have
them - they are all collected at the top of the file for exactly that reason.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

# --------------------------------------------------------------------------
# Tunable agronomy assumptions
# --------------------------------------------------------------------------

#: Crop coefficient (Kc) per sugarcane growth stage.
CROP_COEFFICIENT: dict[str, float] = {
    "germination": 0.50,
    "tillering": 0.90,
    "grand_growth": 1.25,
    "maturation": 0.80,
    "ratoon_initiation": 0.85,
}

#: Soil moisture percentage below which irrigation is triggered, per stage.
STAGE_TRIGGER: dict[str, float] = {
    "germination": 60.0,
    "tillering": 50.0,
    "grand_growth": 55.0,
    "maturation": 38.0,
    "ratoon_initiation": 55.0,
}

#: Trigger adjustment per soil type - light soils have little buffer, so they
#: are irrigated at a higher moisture reading.
SOIL_TRIGGER_ADJUST: dict[str, float] = {
    "sandy": 8.0,
    "red": 4.0,
    "loamy": 0.0,
    "mixed": 0.0,
    "clay": -3.0,
    "black": -5.0,
}

#: Total available water (mm) held in a full sugarcane root zone, per soil type.
TOTAL_AVAILABLE_WATER_MM: dict[str, float] = {
    "sandy": 55.0,
    "red": 75.0,
    "loamy": 110.0,
    "mixed": 100.0,
    "clay": 130.0,
    "black": 145.0,
}

#: Fraction of the full root zone developed at each stage.
ROOT_ZONE_FRACTION: dict[str, float] = {
    "germination": 0.45,
    "tillering": 0.75,
    "grand_growth": 1.00,
    "maturation": 1.00,
    "ratoon_initiation": 0.70,
}

#: Multiplier applied to reference evapotranspiration for the sky condition.
WEATHER_ET_FACTOR: dict[str, float] = {
    "clear": 1.00,
    "partly_cloudy": 0.90,
    "cloudy": 0.75,
    "rainy": 0.50,
    "stormy": 0.55,
    "humid": 0.80,
    "dry_wind": 1.15,
}

#: Field application efficiency - how much of the applied water reaches the root zone.
METHOD_EFFICIENCY: dict[str, float] = {
    "flood": 0.55,
    "furrow": 0.65,
    "sprinkler": 0.75,
    "drip": 0.90,
}

#: Assumed application rate (mm of water delivered per hour) used for duration.
METHOD_APPLICATION_RATE_MM_H: dict[str, float] = {
    "flood": 45.0,
    "furrow": 32.0,
    "sprinkler": 12.0,
    "drip": 5.0,
}

#: Fraction of measured rainfall that actually enters the root zone.
RAINFALL_EFFECTIVENESS = 0.75

#: Rain expected over the next 24 h at 100 % forecast probability (mm).
FORECAST_RAIN_AT_FULL_PROBABILITY = 8.0

#: Below this net requirement irrigation is not worth starting.
MIN_USEFUL_IRRIGATION_MM = 5.0

WEATHER_CONDITIONS = tuple(WEATHER_ET_FACTOR)
SOIL_TYPES = tuple(TOTAL_AVAILABLE_WATER_MM)
GROWTH_STAGES = tuple(CROP_COEFFICIENT)
IRRIGATION_METHODS = tuple(METHOD_EFFICIENCY)

#: Column order used when encoding a row for scikit-learn. Keep this stable -
#: the trained model file stores it too and refuses to load on a mismatch.
NUMERIC_FEATURES = [
    "soil_moisture",
    "temperature",
    "humidity",
    "rainfall",
    "rain_probability",
    "wind_speed",
]
CATEGORICAL_FEATURES = ["weather_condition", "soil_type", "growth_stage"]
FEATURE_ORDER = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# --------------------------------------------------------------------------
# Core water balance
# --------------------------------------------------------------------------


def reference_evapotranspiration(
    temperature: float, humidity: float, wind_speed: float, weather_condition: str
) -> float:
    """Simplified reference ET (mm/day).

    This is an intentionally readable temperature / humidity / wind formulation,
    not full Penman-Monteith. It behaves sensibly across the Indian range
    (roughly 2-8 mm/day) and every term is inspectable. Swap in Penman-Monteith
    once you have solar radiation data.
    """
    effective_temp = max(temperature - 5.0, 0.5)
    thermal = 0.35 * math.pow(effective_temp, 0.9)
    dryness = 1.0 - (min(max(humidity, 0.0), 100.0) / 100.0) * 0.60
    wind = 1.0 + 0.02 * min(max(wind_speed, 0.0), 40.0)
    sky = WEATHER_ET_FACTOR.get(weather_condition, 1.0)
    return round(max(0.4, thermal * dryness * wind * sky), 2)


def moisture_trigger(soil_type: str, growth_stage: str) -> float:
    base = STAGE_TRIGGER.get(growth_stage, 50.0)
    adjust = SOIL_TRIGGER_ADJUST.get(soil_type, 0.0)
    return round(min(max(base + adjust, 25.0), 75.0), 1)


def available_water_mm(soil_type: str, growth_stage: str) -> float:
    taw = TOTAL_AVAILABLE_WATER_MM.get(soil_type, 100.0)
    fraction = ROOT_ZONE_FRACTION.get(growth_stage, 0.8)
    return round(taw * fraction, 1)


def effective_rainfall(rainfall: float, rain_probability: float) -> float:
    measured = max(rainfall, 0.0) * RAINFALL_EFFECTIVENESS
    forecast = (min(max(rain_probability, 0.0), 100.0) / 100.0) * FORECAST_RAIN_AT_FULL_PROBABILITY
    return round(measured + forecast, 2)


@dataclass
class WaterBalance:
    """Intermediate physical quantities - surfaced to the UI for transparency."""

    reference_et_mm: float
    crop_coefficient: float
    crop_water_use_mm: float
    moisture_trigger: float
    available_water_mm: float
    deficit_mm: float
    effective_rain_mm: float
    net_requirement_mm: float
    gross_requirement_mm: float
    efficiency: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def compute_water_balance(
    *,
    soil_moisture: float,
    temperature: float,
    humidity: float,
    rainfall: float = 0.0,
    rain_probability: float = 0.0,
    wind_speed: float = 5.0,
    weather_condition: str = "clear",
    soil_type: str = "loamy",
    growth_stage: str = "tillering",
    irrigation_method: str = "furrow",
) -> WaterBalance:
    et0 = reference_evapotranspiration(temperature, humidity, wind_speed, weather_condition)
    kc = CROP_COEFFICIENT.get(growth_stage, 0.9)
    etc = round(et0 * kc, 2)

    trigger = moisture_trigger(soil_type, growth_stage)
    taw = available_water_mm(soil_type, growth_stage)
    deficit = round(max(0.0, (trigger - soil_moisture) / 100.0) * taw, 2)

    rain = effective_rainfall(rainfall, rain_probability)
    net = round(max(0.0, deficit + etc - rain), 2)

    efficiency = METHOD_EFFICIENCY.get(irrigation_method, 0.65)
    gross = round(net / efficiency, 2) if net > 0 else 0.0

    return WaterBalance(
        reference_et_mm=et0,
        crop_coefficient=kc,
        crop_water_use_mm=etc,
        moisture_trigger=trigger,
        available_water_mm=taw,
        deficit_mm=deficit,
        effective_rain_mm=rain,
        net_requirement_mm=net,
        gross_requirement_mm=gross,
        efficiency=efficiency,
    )


# --------------------------------------------------------------------------
# Decision layer
# --------------------------------------------------------------------------


def decide_priority(
    *,
    soil_moisture: float,
    temperature: float,
    net_requirement: float,
    trigger: float,
    growth_stage: str,
    required: bool,
) -> str:
    if not required:
        return "low"
    if (
        soil_moisture <= trigger * 0.45
        or (net_requirement >= 35 and temperature >= 38)
        or (soil_moisture < 20 and growth_stage == "grand_growth")
    ):
        return "critical"
    if soil_moisture <= trigger * 0.70 or net_requirement >= 22:
        return "high"
    if net_requirement >= MIN_USEFUL_IRRIGATION_MM + 3:
        return "medium"
    return "low"


def moisture_status(soil_moisture: float, trigger: float) -> str:
    if soil_moisture >= trigger + 20:
        return "Very wet - risk of waterlogging"
    if soil_moisture >= trigger + 8:
        return "Adequate"
    if soil_moisture >= trigger:
        return "Approaching the irrigation trigger"
    if soil_moisture >= trigger * 0.7:
        return "Below trigger - crop is starting to draw down reserves"
    if soil_moisture >= trigger * 0.45:
        return "Low - visible stress likely"
    return "Critically low"


def recommended_window(temperature: float, wind_speed: float, weather_condition: str) -> str:
    if weather_condition in {"rainy", "stormy"}:
        return "Hold off while it is raining. Recheck 12 h after the rain stops."
    if temperature >= 35 or wind_speed >= 20:
        return "Early morning 5:00-8:00 AM, or evening after 6:00 PM (avoids peak evaporation)"
    if temperature >= 28:
        return "Early morning 6:00-9:00 AM"
    return "Morning 7:00-10:00 AM"


def next_check_hours(priority: str, soil_type: str) -> int:
    base = {"critical": 6, "high": 12, "medium": 24, "low": 48}.get(priority, 24)
    if soil_type in {"sandy", "red"}:
        base = max(4, int(base * 0.7))
    if soil_type in {"black", "clay"}:
        base = int(base * 1.2)
    return base


def water_saving_tips(
    *, irrigation_method: str, soil_type: str, weather_condition: str, priority: str
) -> list[str]:
    tips: list[str] = []
    if irrigation_method == "flood":
        tips.append(
            "Flood irrigation loses roughly 45 % of the applied water. Furrow or alternate-furrow "
            "irrigation is the cheapest immediate improvement."
        )
    if irrigation_method in {"flood", "furrow"}:
        tips.append(
            "Drip irrigation with fertigation typically delivers the same crop water use with "
            "far less applied water. Check state subsidy schemes for micro-irrigation."
        )
    if irrigation_method == "drip":
        tips.append("Check emitters for clogging every fortnight so the water actually reaches each plant.")
    if soil_type in {"sandy", "red"}:
        tips.append("On light soils, irrigate little and often - a single heavy irrigation mostly drains past the roots.")
    if soil_type in {"black", "clay"}:
        tips.append("On heavy soils, confirm water is not standing after irrigation. Waterlogging damages roots and invites root disease.")
    tips.append("Trash mulching between rows cuts surface evaporation and keeps the topsoil cooler.")
    if weather_condition in {"clear", "dry_wind"}:
        tips.append("Irrigate in the early morning or evening. Midday irrigation on a clear, windy day loses the most water to evaporation.")
    if priority in {"low", "medium"}:
        tips.append("Confirm the reading by hand: dig 15-20 cm and squeeze a handful of soil before starting the pump.")
    return tips[:5]


@dataclass
class IrrigationDecision:
    irrigation_required: bool
    priority: str
    water_requirement_mm: float
    gross_requirement_mm: float
    water_volume_liters: float
    water_volume_per_hectare: float
    duration_minutes: int
    recommended_window: str
    next_check_hours: int
    soil_moisture_status: str
    reason: str
    explanation: list[str] = field(default_factory=list)
    water_saving_tips: list[str] = field(default_factory=list)
    rain_forecast_note: str = ""
    balance: WaterBalance | None = None
    feature_contributions: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["balance"] = self.balance.as_dict() if self.balance else None
        return data


def _rain_note(rainfall: float, rain_probability: float, effective_rain: float) -> str:
    if rainfall >= 20:
        return (
            f"Heavy rainfall of {rainfall:.0f} mm was recorded in the last 24 h "
            f"({effective_rain:.1f} mm of it effective). Check drainage before irrigating."
        )
    if rainfall > 0 and rain_probability >= 60:
        return (
            f"{rainfall:.0f} mm has already fallen and there is a {rain_probability:.0f} % chance "
            "of more rain. Waiting is usually the better choice."
        )
    if rain_probability >= 70:
        return f"High chance of rain ({rain_probability:.0f} %) in the next 24 h - consider deferring irrigation."
    if rain_probability >= 40:
        return f"Moderate chance of rain ({rain_probability:.0f} %). Recheck the forecast before starting the pump."
    if rainfall > 0:
        return f"{rainfall:.0f} mm of rainfall recorded, contributing about {effective_rain:.1f} mm to the root zone."
    return "No significant rainfall expected in the next 24 h."


def _build_explanation(
    inputs: dict[str, Any], balance: WaterBalance, required: bool, priority: str
) -> list[str]:
    sm = inputs["soil_moisture"]
    lines = [
        f"Soil moisture is {sm:.0f} %, against an irrigation trigger of {balance.moisture_trigger:.0f} % "
        f"for {inputs['growth_stage'].replace('_', ' ')} on {inputs['soil_type']} soil.",
        f"That leaves a root-zone deficit of about {balance.deficit_mm:.1f} mm "
        f"(root zone holds roughly {balance.available_water_mm:.0f} mm of available water at this stage).",
        f"At {inputs['temperature']:.0f} °C and {inputs['humidity']:.0f} % humidity with "
        f"{inputs['wind_speed']:.0f} km/h wind, reference ET is about {balance.reference_et_mm:.1f} mm/day; "
        f"with a crop coefficient of {balance.crop_coefficient:.2f} the crop uses roughly "
        f"{balance.crop_water_use_mm:.1f} mm/day.",
    ]
    if balance.effective_rain_mm > 0:
        lines.append(
            f"Effective rainfall credited: {balance.effective_rain_mm:.1f} mm "
            f"(measured rain at {int(RAINFALL_EFFECTIVENESS * 100)} % effectiveness plus the forecast contribution)."
        )
    if required:
        lines.append(
            f"Net water requirement: {balance.net_requirement_mm:.1f} mm. Allowing for "
            f"{int(balance.efficiency * 100)} % application efficiency, apply about "
            f"{balance.gross_requirement_mm:.1f} mm in the field."
        )
        lines.append(f"Priority is {priority.upper()} based on how far moisture has fallen below the trigger and the current temperature.")
    else:
        lines.append(
            f"Net requirement is only {balance.net_requirement_mm:.1f} mm, below the "
            f"{MIN_USEFUL_IRRIGATION_MM:.0f} mm threshold where irrigating is worthwhile. Hold and recheck."
        )
    return lines


def _feature_contributions(inputs: dict[str, Any], balance: WaterBalance) -> list[dict[str, Any]]:
    return [
        {
            "feature": "soil_moisture",
            "label": "Soil moisture deficit",
            "value": round(inputs["soil_moisture"], 1),
            "impact": round(balance.deficit_mm, 2),
            "note": f"Moisture {inputs['soil_moisture']:.0f} % vs trigger {balance.moisture_trigger:.0f} %",
        },
        {
            "feature": "crop_water_use",
            "label": "Crop water use (ETc)",
            "value": round(balance.crop_water_use_mm, 2),
            "impact": round(balance.crop_water_use_mm, 2),
            "note": f"ET0 {balance.reference_et_mm:.1f} mm x Kc {balance.crop_coefficient:.2f}",
        },
        {
            "feature": "effective_rain",
            "label": "Effective rainfall",
            "value": round(balance.effective_rain_mm, 2),
            "impact": -round(balance.effective_rain_mm, 2),
            "note": "Rain already in the root zone plus the forecast contribution",
        },
        {
            "feature": "temperature",
            "label": "Temperature",
            "value": round(inputs["temperature"], 1),
            "impact": round((inputs["temperature"] - 25) * 0.08, 2),
            "note": "Higher temperature raises evaporative demand",
        },
        {
            "feature": "humidity",
            "label": "Humidity",
            "value": round(inputs["humidity"], 1),
            "impact": -round((inputs["humidity"] - 50) * 0.04, 2),
            "note": "Higher humidity lowers evaporative demand",
        },
        {
            "feature": "wind_speed",
            "label": "Wind speed",
            "value": round(inputs["wind_speed"], 1),
            "impact": round(inputs["wind_speed"] * 0.03, 2),
            "note": "Wind increases evaporation from soil and leaf surfaces",
        },
    ]


def decide(
    *,
    soil_moisture: float,
    temperature: float,
    humidity: float,
    rainfall: float = 0.0,
    rain_probability: float = 0.0,
    wind_speed: float = 5.0,
    weather_condition: str = "clear",
    soil_type: str = "loamy",
    growth_stage: str = "tillering",
    irrigation_method: str = "furrow",
    area_hectares: float = 1.0,
    net_requirement_override: float | None = None,
) -> IrrigationDecision:
    """Full irrigation decision.

    ``net_requirement_override`` lets the trained regression model supply the
    water requirement while this function still produces the priority, duration,
    volume and human explanation around it.
    """
    inputs = {
        "soil_moisture": soil_moisture,
        "temperature": temperature,
        "humidity": humidity,
        "rainfall": rainfall,
        "rain_probability": rain_probability,
        "wind_speed": wind_speed,
        "weather_condition": weather_condition,
        "soil_type": soil_type,
        "growth_stage": growth_stage,
        "irrigation_method": irrigation_method,
    }

    balance = compute_water_balance(**inputs)

    if net_requirement_override is not None:
        net = round(max(0.0, float(net_requirement_override)), 2)
        balance.net_requirement_mm = net
        balance.gross_requirement_mm = round(net / balance.efficiency, 2) if net > 0 else 0.0

    net = balance.net_requirement_mm
    gross = balance.gross_requirement_mm

    required = net >= MIN_USEFUL_IRRIGATION_MM and soil_moisture < balance.moisture_trigger + 3
    # A strong rain forecast defers anything that is not already urgent.
    deferred_for_rain = False
    if required and rain_probability >= 70 and net < 15 and soil_moisture > balance.moisture_trigger * 0.6:
        required = False
        deferred_for_rain = True

    priority = decide_priority(
        soil_moisture=soil_moisture,
        temperature=temperature,
        net_requirement=net,
        trigger=balance.moisture_trigger,
        growth_stage=growth_stage,
        required=required,
    )

    rate = METHOD_APPLICATION_RATE_MM_H.get(irrigation_method, 32.0)
    duration = int(round((gross / rate) * 60)) if required and gross > 0 else 0

    volume_per_ha = round(gross * 10_000, 0) if required else 0.0  # 1 mm over 1 ha = 10 000 L
    volume_total = round(volume_per_ha * area_hectares, 0)

    status = moisture_status(soil_moisture, balance.moisture_trigger)
    rain_note = _rain_note(rainfall, rain_probability, balance.effective_rain_mm)

    if deferred_for_rain:
        reason = (
            f"A {rain_probability:.0f} % chance of rain is expected to cover the small "
            f"{net:.1f} mm shortfall. Holding irrigation avoids wasting water."
        )
    elif required:
        drivers = []
        if balance.deficit_mm > balance.crop_water_use_mm:
            drivers.append(f"soil moisture is {soil_moisture:.0f} %, below the {balance.moisture_trigger:.0f} % trigger")
        if temperature >= 33:
            drivers.append(f"high temperature ({temperature:.0f} °C) is increasing water loss")
        if humidity < 40:
            drivers.append(f"low humidity ({humidity:.0f} %) is increasing evaporation")
        if wind_speed >= 20:
            drivers.append(f"strong wind ({wind_speed:.0f} km/h) is increasing evaporation")
        if not drivers:
            drivers.append(f"the crop is using about {balance.crop_water_use_mm:.1f} mm per day at this stage")
        reason = "Irrigation is recommended because " + ", and ".join(drivers) + "."
    else:
        reason = (
            f"Soil moisture at {soil_moisture:.0f} % is adequate for the "
            f"{growth_stage.replace('_', ' ')} stage. No irrigation is needed right now."
        )

    return IrrigationDecision(
        irrigation_required=required,
        priority=priority,
        water_requirement_mm=net,
        gross_requirement_mm=gross,
        water_volume_liters=volume_total,
        water_volume_per_hectare=volume_per_ha,
        duration_minutes=duration,
        recommended_window=recommended_window(temperature, wind_speed, weather_condition),
        next_check_hours=next_check_hours(priority, soil_type),
        soil_moisture_status=status,
        reason=reason,
        explanation=_build_explanation(inputs, balance, required, priority),
        water_saving_tips=water_saving_tips(
            irrigation_method=irrigation_method,
            soil_type=soil_type,
            weather_condition=weather_condition,
            priority=priority,
        ),
        rain_forecast_note=rain_note,
        balance=balance,
        feature_contributions=_feature_contributions(inputs, balance),
    )


# --------------------------------------------------------------------------
# Simulated soil moisture
# --------------------------------------------------------------------------


def simulate_soil_moisture(
    *,
    days_since_irrigation: float,
    soil_type: str = "loamy",
    growth_stage: str = "tillering",
    temperature: float = 30.0,
    humidity: float = 60.0,
    wind_speed: float = 6.0,
    weather_condition: str = "clear",
    rainfall_since: float = 0.0,
    starting_moisture: float = 85.0,
) -> dict[str, Any]:
    """Estimate soil moisture when no physical sensor is available.

    The project brief calls for simulated soil-moisture data as a stand-in for
    field sensors. The simulation drains the root zone by one day of crop water
    use per day and adds back effective rainfall.
    """
    et0 = reference_evapotranspiration(temperature, humidity, wind_speed, weather_condition)
    kc = CROP_COEFFICIENT.get(growth_stage, 0.9)
    etc = et0 * kc
    taw = available_water_mm(soil_type, growth_stage)

    drawn_mm = etc * max(0.0, days_since_irrigation)
    added_mm = max(0.0, rainfall_since) * RAINFALL_EFFECTIVENESS

    change_percent = ((added_mm - drawn_mm) / taw) * 100.0
    moisture = min(100.0, max(2.0, starting_moisture + change_percent))

    return {
        "simulated_soil_moisture": round(moisture, 1),
        "starting_moisture": round(starting_moisture, 1),
        "days_since_irrigation": days_since_irrigation,
        "daily_crop_water_use_mm": round(etc, 2),
        "root_zone_available_water_mm": round(taw, 1),
        "water_drawn_mm": round(drawn_mm, 2),
        "rain_added_mm": round(added_mm, 2),
        "method": "simulated",
        "note": (
            "Simulated value derived from a water-balance model, not a physical sensor reading. "
            "Confirm by hand at 15-20 cm depth before acting on it."
        ),
    }
