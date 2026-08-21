"""Unified history across plant, soil and irrigation records."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import IrrigationRecord, PlantAnalysis, SoilAnalysis, User
from app.services import storage

PRIORITY_TONE = {"critical": "danger", "high": "warning", "medium": "info", "low": "success"}
SEVERITY_TONE = {"none": "success", "mild": "info", "moderate": "warning", "severe": "danger", "undetermined": "info"}


def _plant_item(row: PlantAnalysis) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": "plant",
        "title": row.condition_label,
        "subtitle": (
            f"{row.confidence * 100:.0f} % confidence"
            + (f" | {row.severity} severity" if row.severity not in {"none", "undetermined"} else "")
            + (" | DEMO mode" if row.is_demo else "")
        ),
        "badge": row.severity.title() if row.severity != "none" else "Healthy",
        "badge_tone": SEVERITY_TONE.get(row.severity, "info"),
        "image_url": row.image_url,
        "created_at": row.created_at,
    }


def _soil_item(row: SoilAnalysis) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": "soil",
        "title": row.soil_label,
        "subtitle": (
            f"{row.confidence * 100:.0f} % visual confidence | {row.moisture_appearance} appearance"
            + (" | DEMO estimate" if row.is_demo else "")
        ),
        "badge": "Visual estimate",
        "badge_tone": "info",
        "image_url": row.image_url,
        "created_at": row.created_at,
    }


def _irrigation_item(row: IrrigationRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": "irrigation",
        "title": "Irrigation recommended" if row.irrigation_required else "No irrigation needed",
        "subtitle": (
            f"Soil moisture {row.soil_moisture:.0f} % | {row.temperature:.0f} °C"
            + (f" | {row.water_requirement_mm:.0f} mm for {row.duration_minutes} min" if row.irrigation_required else "")
        ),
        "badge": row.priority.title(),
        "badge_tone": PRIORITY_TONE.get(row.priority, "info"),
        "image_url": None,
        "created_at": row.created_at,
    }


def counts(db: Session, user: User) -> dict[str, int]:
    def count_of(model) -> int:
        return int(db.scalar(select(func.count()).select_from(model).where(model.user_id == user.id)) or 0)

    plant = count_of(PlantAnalysis)
    soil = count_of(SoilAnalysis)
    irrigation = count_of(IrrigationRecord)
    return {"plant": plant, "soil": soil, "irrigation": irrigation, "total": plant + soil + irrigation}


def list_history(
    db: Session, user: User, kind: str | None = None, page: int = 1, page_size: int = 20
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    if kind in (None, "", "all", "plant"):
        items += [
            _plant_item(row)
            for row in db.scalars(select(PlantAnalysis).where(PlantAnalysis.user_id == user.id))
        ]
    if kind in (None, "", "all", "soil"):
        items += [
            _soil_item(row) for row in db.scalars(select(SoilAnalysis).where(SoilAnalysis.user_id == user.id))
        ]
    if kind in (None, "", "all", "irrigation"):
        items += [
            _irrigation_item(row)
            for row in db.scalars(select(IrrigationRecord).where(IrrigationRecord.user_id == user.id))
        ]

    items.sort(key=lambda item: item["created_at"], reverse=True)
    total = len(items)
    start = max(0, (page - 1) * page_size)
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "counts": counts(db, user),
    }


def _model_for_kind(kind: str):
    return {"plant": PlantAnalysis, "soil": SoilAnalysis, "irrigation": IrrigationRecord}.get(kind)


def get_detail(db: Session, user: User, kind: str, record_id: int) -> dict[str, Any] | None:
    model = _model_for_kind(kind)
    if model is None:
        return None
    row = db.get(model, record_id)
    if row is None or row.user_id != user.id:
        return None

    if kind == "irrigation":
        payload = {
            "inputs": {
                "soil_moisture": row.soil_moisture,
                "temperature": row.temperature,
                "humidity": row.humidity,
                "rainfall": row.rainfall,
                "rain_probability": row.rain_probability,
                "wind_speed": row.wind_speed,
                "weather_condition": row.weather_condition,
                "soil_type": row.soil_type,
                "growth_stage": row.growth_stage,
                "irrigation_method": row.irrigation_method,
                "area_hectares": row.area_hectares,
            },
            "result": row.prediction,
        }
    else:
        payload = {"result": row.result, "image_url": row.image_url}

    return {"id": row.id, "kind": kind, "created_at": row.created_at, "payload": payload}


def delete_record(db: Session, user: User, kind: str, record_id: int) -> bool:
    model = _model_for_kind(kind)
    if model is None:
        return False
    row = db.get(model, record_id)
    if row is None or row.user_id != user.id:
        return False

    if kind in {"plant", "soil"}:
        storage.delete_image(getattr(row, "image_path", None))

    db.delete(row)
    db.commit()
    return True


def clear_all(db: Session, user: User) -> int:
    removed = 0
    for kind, model in (("plant", PlantAnalysis), ("soil", SoilAnalysis), ("irrigation", IrrigationRecord)):
        for row in db.scalars(select(model).where(model.user_id == user.id)):
            if kind in {"plant", "soil"}:
                storage.delete_image(getattr(row, "image_path", None))
            db.delete(row)
            removed += 1
    db.commit()
    return removed
