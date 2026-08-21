"""Irrigation prediction endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_optional_user
from app.database import get_db
from app.ml import irrigation_engine, irrigation_model
from app.models import IrrigationRecord, User
from app.schemas.common import GrowthStage, SoilType, WeatherCondition
from app.schemas.irrigation import (
    IrrigationInput,
    IrrigationModelStatus,
    IrrigationRecordOut,
    IrrigationResult,
)
from app.services import irrigation_service

router = APIRouter(prefix="/irrigation", tags=["Irrigation"])


@router.post("/predict", response_model=IrrigationResult)
def predict(
    payload: IrrigationInput,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> IrrigationResult:
    """Predict irrigation requirement from environmental inputs.

    Works without signing in so the feature can be demonstrated, but the result
    is only saved to history for an authenticated user.
    """
    result = irrigation_service.predict(payload)

    if current_user is not None and payload.save:
        record = irrigation_service.save_record(db, current_user.id, payload, result)
        result["record_id"] = record.id
        result["created_at"] = record.created_at

    return IrrigationResult(**result)


@router.get("/history", response_model=list[IrrigationRecordOut])
def history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IrrigationRecordOut]:
    rows = db.scalars(
        select(IrrigationRecord)
        .where(IrrigationRecord.user_id == current_user.id)
        .order_by(IrrigationRecord.created_at.desc())
        .limit(limit)
    ).all()
    return [IrrigationRecordOut.model_validate(row) for row in rows]


@router.get("/chart", response_model=list[dict])
def chart(
    limit: int = Query(default=10, ge=2, le=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return irrigation_service.recent_chart(db, current_user.id, limit)


@router.get("/model-status", response_model=IrrigationModelStatus)
def model_status() -> IrrigationModelStatus:
    """Is a trained model in use, or the rule engine? Never guesses."""
    return IrrigationModelStatus(**irrigation_model.status())


@router.post("/reload-model", response_model=IrrigationModelStatus)
def reload_model(current_user: User = Depends(get_current_user)) -> IrrigationModelStatus:
    """Pick up a freshly trained model file without restarting the server."""
    irrigation_model.reload_model()
    return IrrigationModelStatus(**irrigation_model.status())


class SoilMoistureSimulationRequest(BaseModel):
    """Inputs for the simulated soil-moisture model.

    The project brief calls for simulated soil-moisture data where physical
    sensors are unavailable or too expensive.
    """

    days_since_irrigation: float = Field(default=3.0, ge=0, le=60)
    starting_moisture: float = Field(default=85.0, ge=0, le=100)
    soil_type: SoilType = SoilType.loamy
    growth_stage: GrowthStage = GrowthStage.tillering
    temperature: float = Field(default=30.0, ge=-10, le=60)
    humidity: float = Field(default=60.0, ge=0, le=100)
    wind_speed: float = Field(default=6.0, ge=0, le=150)
    weather_condition: WeatherCondition = WeatherCondition.clear
    rainfall_since: float = Field(default=0.0, ge=0, le=500)


@router.post("/simulate-soil-moisture", response_model=dict)
def simulate_soil_moisture(payload: SoilMoistureSimulationRequest) -> dict:
    return irrigation_engine.simulate_soil_moisture(
        days_since_irrigation=payload.days_since_irrigation,
        starting_moisture=payload.starting_moisture,
        soil_type=payload.soil_type.value,
        growth_stage=payload.growth_stage.value,
        temperature=payload.temperature,
        humidity=payload.humidity,
        wind_speed=payload.wind_speed,
        weather_condition=payload.weather_condition.value,
        rainfall_since=payload.rainfall_since,
    )


@router.get("/options", response_model=dict)
def options() -> dict:
    """Enum values plus the agronomy assumptions, so the UI never hard-codes them."""
    return {
        "soil_types": [s.value for s in SoilType],
        "growth_stages": [g.value for g in GrowthStage],
        "weather_conditions": [w.value for w in WeatherCondition],
        "irrigation_methods": list(irrigation_engine.IRRIGATION_METHODS),
        "assumptions": {
            "crop_coefficient": irrigation_engine.CROP_COEFFICIENT,
            "moisture_trigger_by_stage": irrigation_engine.STAGE_TRIGGER,
            "soil_trigger_adjustment": irrigation_engine.SOIL_TRIGGER_ADJUST,
            "total_available_water_mm": irrigation_engine.TOTAL_AVAILABLE_WATER_MM,
            "application_efficiency": irrigation_engine.METHOD_EFFICIENCY,
            "application_rate_mm_per_hour": irrigation_engine.METHOD_APPLICATION_RATE_MM_H,
            "rainfall_effectiveness": irrigation_engine.RAINFALL_EFFECTIVENESS,
            "minimum_useful_irrigation_mm": irrigation_engine.MIN_USEFUL_IRRIGATION_MM,
        },
        "assumption_note": (
            "These are documented starting assumptions, not measured constants for your field. "
            "Replace them with values from your local agricultural university in "
            "backend/app/ml/irrigation_engine.py."
        ),
    }
