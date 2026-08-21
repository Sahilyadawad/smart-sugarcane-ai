"""Farmer dashboard summary."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.ml import disease_model, irrigation_model, soil_model
from app.models import User
from app.schemas.history import DashboardSummary
from app.services import (
    history_service,
    irrigation_service,
    plant_service,
    soil_service,
    weather_service,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _greeting(name: str) -> str:
    hour = datetime.now(timezone.utc).astimezone().hour
    if hour < 12:
        part = "Good morning"
    elif hour < 17:
        part = "Good afternoon"
    else:
        part = "Good evening"
    first = name.split()[0] if name else "farmer"
    return f"{part}, {first}"


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummary:
    plant = plant_service.latest(db, current_user.id)
    soil = soil_service.latest(db, current_user.id)
    irrigation = irrigation_service.latest(db, current_user.id)

    city = current_user.farm_location or None
    weather_raw = await weather_service.current_weather(city)

    latest_plant = (
        {
            "id": plant.id,
            "condition": plant.detected_condition,
            "condition_label": plant.condition_label,
            "confidence": plant.confidence,
            "severity": plant.severity,
            "health_score": plant.health_score,
            "image_url": plant.image_url,
            "is_demo": plant.is_demo,
            "created_at": plant.created_at.isoformat(),
        }
        if plant
        else None
    )

    latest_soil = (
        {
            "id": soil.id,
            "soil_type": soil.soil_type,
            "soil_label": soil.soil_label,
            "confidence": soil.confidence,
            "moisture_appearance": soil.moisture_appearance,
            "image_url": soil.image_url,
            "is_demo": soil.is_demo,
            "created_at": soil.created_at.isoformat(),
        }
        if soil
        else None
    )

    latest_irrigation = (
        {
            "id": irrigation.id,
            "irrigation_required": irrigation.irrigation_required,
            "priority": irrigation.priority,
            "water_requirement_mm": irrigation.water_requirement_mm,
            "duration_minutes": irrigation.duration_minutes,
            "soil_moisture": irrigation.soil_moisture,
            "temperature": irrigation.temperature,
            "reason": (irrigation.prediction or {}).get("reason", ""),
            "model_source": irrigation.model_source,
            "created_at": irrigation.created_at.isoformat(),
        }
        if irrigation
        else None
    )

    quick_tips = [
        "Check soil moisture by hand at 15-20 cm before every irrigation - it takes 30 seconds and "
        "catches sensor drift.",
        "Photograph the same block every week so the health trend has something to compare.",
        "A laboratory soil test once a season is worth more than any number of soil photographs.",
    ]
    if latest_irrigation and latest_irrigation["irrigation_required"]:
        quick_tips.insert(
            0,
            f"Irrigation is currently flagged {latest_irrigation['priority'].upper()} priority - "
            f"about {latest_irrigation['water_requirement_mm']:.0f} mm.",
        )
    if latest_plant and latest_plant["condition"] not in {"healthy", "unknown"}:
        quick_tips.insert(
            0,
            f"Your last plant analysis flagged {latest_plant['condition_label']}. "
            "Follow the recovery plan and re-photograph in 5 to 7 days.",
        )

    return DashboardSummary(
        user_name=current_user.name,
        greeting=_greeting(current_user.name),
        totals=history_service.counts(db, current_user),
        latest_plant=latest_plant,
        latest_soil=latest_soil,
        latest_irrigation=latest_irrigation,
        weather=weather_service.summary_for_dashboard(weather_raw),
        plant_trend=plant_service.plant_trend(db, current_user.id, limit=10),
        irrigation_chart=irrigation_service.recent_chart(db, current_user.id, limit=10),
        quick_tips=quick_tips[:4],
        model_status={
            "irrigation": irrigation_model.status()["model_source"],
            "irrigation_trained": irrigation_model.status()["trained_model_available"],
            "disease": disease_model.status()["model_source"],
            "disease_trained": disease_model.status()["trained_model_available"],
            "soil": soil_model.status()["model_source"],
            "soil_trained": soil_model.status()["trained_model_available"],
        },
    )
