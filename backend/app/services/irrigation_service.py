"""Irrigation prediction service - thin layer over the ML model and rule engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import irrigation_model
from app.models import IrrigationRecord
from app.schemas.irrigation import IrrigationInput

DISCLAIMER = (
    "This is a decision-support estimate built from a simplified water-balance model. "
    "Confirm soil moisture by hand at 15-20 cm depth before starting the pump, and follow "
    "your local agricultural extension guidance for your field."
)


def predict(payload: IrrigationInput) -> dict[str, Any]:
    raw = irrigation_model.predict(
        {
            "soil_moisture": payload.soil_moisture,
            "temperature": payload.temperature,
            "humidity": payload.humidity,
            "rainfall": payload.rainfall,
            "rain_probability": payload.rain_probability,
            "wind_speed": payload.wind_speed,
            "weather_condition": payload.weather_condition.value,
            "soil_type": payload.soil_type.value,
            "growth_stage": payload.growth_stage.value,
            "irrigation_method": payload.irrigation_method.value,
            "area_hectares": payload.area_hectares,
        }
    )

    balance = raw.get("balance") or {}
    return {
        "irrigation_required": raw["irrigation_required"],
        "priority": raw["priority"],
        "water_requirement_mm": raw["water_requirement_mm"],
        "water_volume_liters": raw["water_volume_liters"],
        "water_volume_per_hectare": raw["water_volume_per_hectare"],
        "duration_minutes": raw["duration_minutes"],
        "recommended_window": raw["recommended_window"],
        "next_check_hours": raw["next_check_hours"],
        "soil_moisture_status": raw["soil_moisture_status"],
        "deficit_mm": balance.get("deficit_mm", 0.0),
        "crop_water_use_mm": balance.get("crop_water_use_mm", 0.0),
        "effective_rain_mm": balance.get("effective_rain_mm", 0.0),
        "reference_et_mm": balance.get("reference_et_mm", 0.0),
        "crop_coefficient": balance.get("crop_coefficient", 0.0),
        "reason": raw["reason"],
        "explanation": raw["explanation"],
        "water_saving_tips": raw["water_saving_tips"],
        "rain_forecast_note": raw["rain_forecast_note"],
        "model_source": raw["model_source"],
        "model_label": raw["model_label"],
        "model_confidence": raw["model_confidence"],
        "model_notes": raw["model_notes"],
        "feature_contributions": raw["feature_contributions"],
        "disclaimer": DISCLAIMER,
    }


def save_record(db: Session, user_id: int, payload: IrrigationInput, result: dict[str, Any]) -> IrrigationRecord:
    record = IrrigationRecord(
        user_id=user_id,
        soil_moisture=payload.soil_moisture,
        temperature=payload.temperature,
        humidity=payload.humidity,
        rainfall=payload.rainfall,
        rain_probability=payload.rain_probability,
        wind_speed=payload.wind_speed,
        weather_condition=payload.weather_condition.value,
        soil_type=payload.soil_type.value,
        growth_stage=payload.growth_stage.value,
        irrigation_method=payload.irrigation_method.value,
        area_hectares=payload.area_hectares,
        irrigation_required=result["irrigation_required"],
        priority=result["priority"],
        water_requirement_mm=result["water_requirement_mm"],
        duration_minutes=result["duration_minutes"],
        model_source=result["model_source"],
        prediction=result,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def latest(db: Session, user_id: int) -> IrrigationRecord | None:
    return db.scalars(
        select(IrrigationRecord)
        .where(IrrigationRecord.user_id == user_id)
        .order_by(IrrigationRecord.created_at.desc())
        .limit(1)
    ).first()


def recent_chart(db: Session, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Series used by the dashboard chart: moisture vs recommended water."""
    rows = list(
        db.scalars(
            select(IrrigationRecord)
            .where(IrrigationRecord.user_id == user_id)
            .order_by(IrrigationRecord.created_at.desc())
            .limit(limit)
        )
    )
    rows.reverse()
    return [
        {
            "date": row.created_at.strftime("%d %b"),
            "timestamp": row.created_at.isoformat(),
            "soil_moisture": round(row.soil_moisture, 1),
            "temperature": round(row.temperature, 1),
            "water_mm": round(row.water_requirement_mm, 1),
            "priority": row.priority,
            "required": row.irrigation_required,
        }
        for row in rows
    ]
