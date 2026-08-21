"""Fertilizer guidance engine.

Deliberately QUALITATIVE. The engine says which nutrients deserve attention at
the current growth stage, how to time and split applications, and what the soil
type changes about that. It never outputs a kg/ha dose, because a safe dose
depends on a soil test, the variety, the yield target and the state
recommendation - none of which can be inferred from an image or a form.
"""

from __future__ import annotations

from typing import Any

from app.ml.knowledge import fertilizer_kb
from app.schemas.common import humanise
from app.schemas.recommendation import FertilizerRequest

PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2}
PRIORITY_NAMES = ["low", "medium", "high"]

CONDITION_CATEGORY = {
    "healthy": "healthy",
    "red_rot": "diseased_fungal",
    "rust": "diseased_fungal",
    "smut": "diseased_fungal",
    "mosaic": "diseased_viral",
    "yellow_leaf": "diseased_viral",
    "leaf_scald": "diseased_bacterial",
    "unknown": "unknown",
}

FULL_SEASON_STAGES = ["germination", "tillering", "grand_growth", "maturation"]


def _shift_priority(priority: str, steps: int) -> str:
    index = PRIORITY_ORDER.get(priority, 1) + steps
    return PRIORITY_NAMES[max(0, min(len(PRIORITY_NAMES) - 1, index))]


def _rate_lab_value(kb: dict[str, Any], nutrient: str, value: float | None) -> str | None:
    """Classify a laboratory soil-test value as low / medium / high."""
    if value is None:
        return None
    ranges = kb.get("npk_test_rating", {}).get(nutrient)
    if not ranges:
        return None
    thresholds = {
        "nitrogen": (280.0, 560.0),
        "phosphorus": (10.0, 25.0),
        "potassium": (110.0, 280.0),
    }[nutrient]
    if value < thresholds[0]:
        return "low"
    if value <= thresholds[1]:
        return "medium"
    return "high"


def _ph_note(kb: dict[str, Any], ph: float | None) -> str | None:
    if ph is None:
        return None
    bands = kb.get("ph_guidance", [])
    if ph < 5.5:
        band = bands[0]
    elif ph < 6.5:
        band = bands[1]
    elif ph < 7.5:
        band = bands[2]
    elif ph < 8.5:
        band = bands[3]
    else:
        band = bands[4]
    return f"Soil pH {ph:.1f} - {band.get('label')}. {band.get('note')}"


def _split_schedule(kb: dict[str, Any], current_stage: str, soil_type: str) -> list[dict[str, Any]]:
    stages = kb.get("growth_stages", {})
    schedule: list[dict[str, Any]] = []
    for key in FULL_SEASON_STAGES:
        stage = stages.get(key)
        if not stage:
            continue
        schedule.append(
            {
                "stage": key,
                "label": stage.get("label", humanise(key)),
                "window": stage.get("typical_window", ""),
                "focus": stage.get("focus", ""),
                "timing_note": stage.get("timing_note", ""),
                "nutrient_priority": stage.get("nutrient_priority", {}),
                "is_current": key == current_stage,
                "is_past": FULL_SEASON_STAGES.index(key) < FULL_SEASON_STAGES.index(current_stage)
                if current_stage in FULL_SEASON_STAGES
                else False,
            }
        )
    if current_stage == "ratoon_initiation":
        stage = stages.get("ratoon_initiation", {})
        schedule.insert(
            0,
            {
                "stage": "ratoon_initiation",
                "label": stage.get("label", "Ratoon Initiation"),
                "window": stage.get("typical_window", ""),
                "focus": stage.get("focus", ""),
                "timing_note": stage.get("timing_note", ""),
                "nutrient_priority": stage.get("nutrient_priority", {}),
                "is_current": True,
                "is_past": False,
            },
        )
    if soil_type in {"sandy", "red"}:
        for entry in schedule:
            entry["soil_note"] = "Light soil - prefer more, smaller splits to limit leaching."
    elif soil_type in {"black", "clay"}:
        for entry in schedule:
            entry["soil_note"] = "Heavy soil - apply when the soil is workable, never when saturated."
    return schedule


def recommend(request: FertilizerRequest) -> dict[str, Any]:
    kb = fertilizer_kb()
    stage_key = request.growth_stage.value
    stage = kb.get("growth_stages", {}).get(stage_key, {})
    soil_key = request.soil_type.value
    soil = kb.get("soil_type_adjustments", {}).get(soil_key, kb.get("soil_type_adjustments", {}).get("mixed", {}))

    base_priority = dict(stage.get("nutrient_priority", {"nitrogen": "medium", "phosphorus": "medium", "potassium": "medium"}))

    lab_used = any(
        value is not None
        for value in (request.nitrogen_kg_ha, request.phosphorus_kg_ha, request.potassium_kg_ha)
    )

    nutrient_focus: list[dict[str, Any]] = []
    for nutrient, lab_value, soil_note_key in (
        ("nitrogen", request.nitrogen_kg_ha, "nitrogen_note"),
        ("phosphorus", request.phosphorus_kg_ha, "phosphorus_note"),
        ("potassium", request.potassium_kg_ha, "potassium_note"),
    ):
        priority = base_priority.get(nutrient, "medium")
        reason_parts = [
            f"{stage.get('label', humanise(stage_key))}: {stage.get('focus', '')}".strip().rstrip(":")
        ]

        rating = _rate_lab_value(kb, nutrient, lab_value)
        if rating == "low":
            priority = _shift_priority(priority, 1)
            reason_parts.append(
                f"Your soil test rates available {nutrient} as LOW ({lab_value:g} kg/ha), which raises its priority."
            )
        elif rating == "high":
            priority = _shift_priority(priority, -1)
            reason_parts.append(
                f"Your soil test rates available {nutrient} as HIGH ({lab_value:g} kg/ha), which lowers its priority."
            )
        elif rating == "medium":
            reason_parts.append(f"Your soil test rates available {nutrient} as MEDIUM ({lab_value:g} kg/ha).")

        soil_note = soil.get(soil_note_key)
        if soil_note:
            reason_parts.append(f"{soil.get('label', humanise(soil_key))}: {soil_note}")

        # Ripening: nitrogen must come down regardless of anything else.
        if stage_key == "maturation" and nutrient == "nitrogen":
            priority = "low"
            reason_parts.append("Nitrogen during ripening keeps the crop vegetative and lowers sugar recovery.")

        nutrient_focus.append(
            {
                "nutrient": nutrient.title(),
                "priority": priority,
                "reason": " ".join(part for part in reason_parts if part),
                "lab_rating": rating,
            }
        )

    condition_key = CONDITION_CATEGORY.get(request.plant_condition or "", "healthy" if not request.plant_condition else "unknown")
    plant_health_note = kb.get("plant_health_adjustments", {}).get(condition_key, "")

    organic_key = (request.organic_matter_appearance or "medium").lower()
    organic_key = {"moderate": "medium"}.get(organic_key, organic_key)
    organic_advice = kb.get("organic_matter_guidance", {}).get(
        organic_key, kb.get("organic_matter_guidance", {}).get("medium", "")
    )
    if request.organic_matter_appearance:
        organic_advice = (
            f"Image estimate suggests {request.organic_matter_appearance} organic matter. {organic_advice} "
            "Note that image-based organic matter is an appearance estimate only - confirm with a laboratory organic carbon test."
        )

    water_note = kb.get("water_availability_adjustments", {}).get(
        request.water_availability.value, ""
    )
    if not request.irrigation_available:
        water_note += (
            " Without assured irrigation, time every application to coincide with expected rainfall - "
            "fertilizer applied to dry soil is largely wasted."
        )

    suggested: list[str] = list(stage.get("practices", []))
    if soil.get("split_note"):
        suggested.append(soil["split_note"])
    if soil.get("drainage_flag"):
        suggested.append(soil["drainage_flag"])
    if not lab_used:
        suggested.append(
            "No laboratory values were supplied. A soil health card test is the single most useful "
            "next step for getting the quantities right."
        )

    return {
        "growth_stage": stage_key,
        "growth_stage_label": stage.get("label", humanise(stage_key)),
        "typical_window": stage.get("typical_window", ""),
        "stage_goal": stage.get("goal", ""),
        "stage_focus": stage.get("focus", ""),
        "nutrient_focus": nutrient_focus,
        "suggested_management": suggested,
        "split_schedule": _split_schedule(kb, stage_key, soil_key),
        "organic_matter_advice": organic_advice,
        "soil_specific_notes": list(soil.get("notes", []))
        + ([soil["organic_matter_note"]] if soil.get("organic_matter_note") else []),
        "ph_note": _ph_note(kb, request.soil_ph),
        "water_note": water_note,
        "plant_health_note": plant_health_note,
        "lab_values_used": lab_used or request.soil_ph is not None,
        "general_practices": kb.get("general_practices", []),
        "disclaimer": kb.get(
            "final_disclaimer",
            "For exact fertilizer quantities and chemical products, use a laboratory soil test and "
            "consult local agricultural extension recommendations.",
        ),
        "data_disclaimer": kb.get("data_disclaimer", ""),
    }
