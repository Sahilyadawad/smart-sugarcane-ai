"""Plant disease analysis service.

Combines the image classifier (trained model or demo heuristic) with the
editable guidance in ``data/disease_recommendations.json`` and builds the
"How to improve this plant" recovery plan.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import disease_model
from app.ml.knowledge import disease_kb
from app.models import PlantAnalysis
from app.schemas.common import humanise

DISCLAIMER = (
    "AI-based result: Please verify important disease or chemical treatment decisions with a "
    "qualified agricultural expert."
)


def _condition_entry(condition: str) -> dict[str, Any]:
    kb = disease_kb()
    conditions = kb.get("conditions", {})
    return conditions.get(condition) or conditions.get("unknown", {})


def _build_recovery(entry: dict[str, Any], severity: str, growth_stage: str | None) -> dict[str, Any]:
    immediate = list(entry.get("immediate_actions", []))
    recovery = list(entry.get("management", []))
    prevention = list(entry.get("prevention", []))
    monitoring = list(entry.get("monitoring", []))
    nutrient = list(entry.get("nutrient_advice", []))
    irrigation = dict(entry.get("irrigation_advice", {"summary": "", "details": []}))

    severity_extra = entry.get("severity_guidance", {}).get(severity)
    if severity_extra and severity_extra not in {"Not applicable.", "Not determined."}:
        immediate.insert(0, severity_extra)

    if growth_stage == "germination":
        recovery.append(
            "The crop is still establishing. Gap filling with healthy setts may be more effective "
            "than trying to save badly affected clumps."
        )
    elif growth_stage == "grand_growth":
        recovery.append(
            "This is the peak growth stage, so moisture stress on top of disease pressure will cost "
            "the most yield. Keep irrigation steady while you manage the disease."
        )
    elif growth_stage == "maturation":
        recovery.append(
            "The crop is close to harvest. Discuss early harvesting of the affected block with your "
            "factory cane department rather than starting a new treatment programme."
        )
    elif growth_stage == "ratoon_initiation":
        recovery.append(
            "Do not carry a badly affected crop into another ratoon. Plough out and replant with "
            "certified clean seed instead."
        )

    if severity == "severe":
        monitoring.insert(0, "Inspect the affected block daily until the spread stops.")
    elif severity in {"mild", "moderate"}:
        monitoring.insert(0, "Inspect the affected block every 2 to 3 days.")

    return {
        "immediate_action": immediate,
        "recovery_plan": recovery,
        "irrigation_advice": irrigation,
        "soil_and_nutrient_advice": nutrient,
        "prevention_plan": prevention,
        "monitoring_schedule": monitoring,
    }


def analyse(image: Image.Image, growth_stage: str | None = None, notes: str | None = None) -> dict[str, Any]:
    """Run the classifier and compose the full farmer-facing result."""
    prediction = disease_model.predict(image)
    condition = prediction["condition"]
    confidence = float(prediction["confidence"])
    features = prediction["features"]

    severity, health_score, severity_note = disease_model.estimate_severity(condition, features, confidence)
    entry = _condition_entry(condition)
    kb = disease_kb()

    probabilities = [
        {
            "key": key,
            "label": _condition_entry(key).get("label", humanise(key)),
            "probability": round(float(value), 4),
        }
        for key, value in sorted(prediction["probabilities"].items(), key=lambda item: item[1], reverse=True)
    ]

    return {
        "detected_condition": condition,
        "condition_label": entry.get("label", humanise(condition)),
        "pathogen_type": entry.get("pathogen_type", "undetermined"),
        "confidence": round(confidence, 4),
        "severity": severity,
        "severity_note": severity_note,
        "health_score": health_score,
        "short_description": entry.get("short_description", ""),
        "symptoms": entry.get("symptoms", []),
        "causes": entry.get("causes", []),
        "management": entry.get("management", []),
        "prevention": entry.get("prevention", []),
        "recovery": _build_recovery(entry, severity, growth_stage),
        "probabilities": probabilities,
        "image_quality": prediction["quality"],
        "image_features": features,
        "model_source": prediction["model_source"],
        "model_label": prediction["model_label"],
        "is_demo": prediction["is_demo"],
        "model_notes": prediction["notes"],
        "disclaimer": kb.get("safety_notice", DISCLAIMER),
        "growth_stage": growth_stage,
        "notes": notes,
    }


def save_analysis(
    db: Session,
    user_id: int,
    result: dict[str, Any],
    image_path: str,
    image_url: str,
) -> PlantAnalysis:
    record = PlantAnalysis(
        user_id=user_id,
        image_path=image_path,
        image_url=image_url,
        detected_condition=result["detected_condition"],
        condition_label=result["condition_label"],
        confidence=result["confidence"],
        severity=result["severity"],
        health_score=result["health_score"],
        growth_stage=result.get("growth_stage"),
        notes=result.get("notes"),
        model_source=result["model_source"],
        is_demo=result["is_demo"],
        result=result,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ------------------------------------------------------------------- trend
SEVERITY_RANK = {"none": 0, "mild": 1, "moderate": 2, "severe": 3, "undetermined": 1.5}


def plant_trend(db: Session, user_id: int, limit: int = 12) -> dict[str, Any]:
    """Compare plant analyses over time to show improvement or deterioration."""
    rows = list(
        db.scalars(
            select(PlantAnalysis)
            .where(PlantAnalysis.user_id == user_id)
            .order_by(PlantAnalysis.created_at.desc())
            .limit(limit)
        )
    )
    rows.reverse()  # oldest first for charting

    points = [
        {
            "id": row.id,
            "date": row.created_at,
            "condition": row.detected_condition,
            "condition_label": row.condition_label,
            "severity": row.severity,
            "confidence": row.confidence,
            "health_score": row.health_score,
            "image_url": row.image_url,
        }
        for row in rows
    ]

    if len(points) < 2:
        return {
            "points": points,
            "direction": "insufficient_data",
            "summary": (
                "Upload at least two plant photos to see a health trend. "
                "A follow-up photo after 7 days works well."
                if points
                else "No plant analyses yet. Upload a photo to start tracking plant health."
            ),
            "first_seen": points[0]["date"] if points else None,
            "last_seen": points[-1]["date"] if points else None,
            "comparison_note": "",
        }

    first, last = points[0], points[-1]
    delta = last["health_score"] - first["health_score"]
    severity_delta = SEVERITY_RANK.get(last["severity"], 1.5) - SEVERITY_RANK.get(first["severity"], 1.5)

    if delta >= 8 and severity_delta <= 0:
        direction = "improving"
        summary = f"Plant health score rose by {delta:.0f} points across {len(points)} analyses."
    elif delta <= -8 or severity_delta > 0:
        direction = "deteriorating"
        summary = (
            f"Plant health score fell by {abs(delta):.0f} points. "
            "Inspect the field and consider expert advice."
        )
    else:
        direction = "stable"
        summary = f"Plant health has stayed broadly stable across {len(points)} analyses."

    comparison = (
        f"Previous condition: {first['condition_label']} ({first['severity']}) on "
        f"{first['date']:%d %b %Y}. Current condition: {last['condition_label']} "
        f"({last['severity']}) on {last['date']:%d %b %Y}."
    )

    return {
        "points": points,
        "direction": direction,
        "summary": summary,
        "first_seen": first["date"],
        "last_seen": last["date"],
        "comparison_note": comparison,
    }


def latest(db: Session, user_id: int) -> PlantAnalysis | None:
    return db.scalars(
        select(PlantAnalysis)
        .where(PlantAnalysis.user_id == user_id)
        .order_by(PlantAnalysis.created_at.desc())
        .limit(1)
    ).first()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
