"""Soil image analysis service.

Produces a clearly-labelled VISUAL estimate, then chains straight into variety
and fertilizer recommendations so the farmer gets an end-to-end answer from one
photograph.
"""

from __future__ import annotations

from typing import Any

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import soil_model
from app.ml.knowledge import soil_kb
from app.models import SoilAnalysis
from app.schemas.common import GrowthStage, SoilType, humanise
from app.schemas.recommendation import FertilizerRequest, VarietyRequest
from app.schemas.soil import SoilFarmContext
from app.services import fertilizer_service, variety_service

LAB_TEST_NOTICE = (
    "Visual AI estimate - laboratory soil testing provides more accurate nutrient and pH values."
)

DISCLAIMER = (
    "A photograph cannot determine exact NPK values, pH, electrical conductivity or micronutrient "
    "concentrations. Everything below describes how the soil LOOKS in this image."
)


def _profile(soil_type: str) -> dict[str, Any]:
    kb = soil_kb()
    profiles = kb.get("profiles", {})
    return profiles.get(soil_type) or profiles.get("mixed", {})


def analyse(image: Image.Image, context: SoilFarmContext | None = None) -> dict[str, Any]:
    context = context or SoilFarmContext()
    prediction = soil_model.predict(image)
    kb = soil_kb()

    soil_type = prediction["soil_type"]
    confidence = float(prediction["confidence"])
    notes = list(prediction["notes"])

    # A farmer who knows their soil type from a lab test always overrides the image.
    if context.soil_type_override is not None:
        override = context.soil_type_override.value
        if override != soil_type:
            notes.insert(
                0,
                f"You selected {humanise(override)} manually, which overrides the image estimate of "
                f"{humanise(soil_type)}. A known soil type is more reliable than a photograph.",
            )
        soil_type = override
        confidence = max(confidence, 0.95)

    profile = _profile(soil_type)
    moisture_key = prediction["moisture_appearance"]
    moisture_info = kb.get("moisture_appearance", {}).get(moisture_key, {})
    organic_key = prediction["organic_matter_appearance"]
    organic_info = kb.get("organic_matter_appearance", {}).get(organic_key, {})

    probabilities = [
        {"key": key, "label": _profile(key).get("label", humanise(key)), "probability": round(float(value), 4)}
        for key, value in sorted(prediction["probabilities"].items(), key=lambda item: item[1], reverse=True)
    ]

    estimate = {
        "soil_type": soil_type,
        "soil_label": profile.get("label", humanise(soil_type)),
        "confidence": round(confidence, 4),
        "colour_description": prediction["colour_description"],
        "dominant_rgb": prediction["dominant_rgb"],
        "texture_appearance": prediction["texture_appearance"],
        "moisture_appearance": moisture_key,
        "moisture_label": moisture_info.get("label", humanise(moisture_key)),
        "moisture_note": moisture_info.get("note", ""),
        "organic_matter_appearance": organic_key,
        "organic_matter_label": organic_info.get("label", humanise(organic_key)),
        "organic_matter_note": organic_info.get("note", ""),
        "visual_description": profile.get("visual_description", ""),
        "general_properties": profile.get("general_properties", []),
        "sugarcane_suitability": profile.get("sugarcane_suitability", ""),
        "management_notes": profile.get("management_notes", []),
        "irrigation_note": profile.get("irrigation_note", ""),
        "probabilities": probabilities,
        "image_quality": prediction["quality"],
    }

    varieties = variety_service.recommend(
        VarietyRequest(
            soil_type=SoilType(soil_type) if soil_type in SoilType.__members__ else SoilType.mixed,
            region=context.region,
            district=context.district,
            climate=context.climate,
            irrigation_available=context.irrigation_available,
            water_availability=context.water_availability,
            planting_season=context.planting_season,
            limit=4,
        )
    )

    fertilizer = fertilizer_service.recommend(
        FertilizerRequest(
            growth_stage=GrowthStage.tillering,
            soil_type=SoilType(soil_type) if soil_type in SoilType.__members__ else SoilType.mixed,
            water_availability=context.water_availability,
            irrigation_available=context.irrigation_available,
            organic_matter_appearance=organic_key,
        )
    )

    return {
        "estimate": estimate,
        "limitations": kb.get("limitations", []),
        "improve_photo_tips": kb.get("improve_photo_tips", []),
        "varieties": varieties,
        "fertilizer": fertilizer,
        "model_source": prediction["model_source"],
        "model_label": prediction["model_label"],
        "is_demo": prediction["is_demo"],
        "model_notes": notes,
        "disclaimer": DISCLAIMER,
        "lab_test_notice": LAB_TEST_NOTICE,
        "context": {
            "region": context.region,
            "district": context.district,
            "climate": context.climate.value,
            "irrigation_available": context.irrigation_available,
            "water_availability": context.water_availability.value,
            "planting_season": context.planting_season.value,
        },
    }


def save_analysis(
    db: Session,
    user_id: int,
    result: dict[str, Any],
    image_path: str,
    image_url: str,
    context: SoilFarmContext | None = None,
) -> SoilAnalysis:
    context = context or SoilFarmContext()
    estimate = result["estimate"]
    record = SoilAnalysis(
        user_id=user_id,
        image_path=image_path,
        image_url=image_url,
        soil_type=estimate["soil_type"],
        soil_label=estimate["soil_label"],
        confidence=estimate["confidence"],
        moisture_appearance=estimate["moisture_appearance"],
        texture_appearance=estimate["texture_appearance"],
        organic_matter_appearance=estimate["organic_matter_appearance"],
        region=context.region,
        district=context.district,
        water_availability=context.water_availability.value,
        model_source=result["model_source"],
        is_demo=result["is_demo"],
        result=result,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def latest(db: Session, user_id: int) -> SoilAnalysis | None:
    return db.scalars(
        select(SoilAnalysis)
        .where(SoilAnalysis.user_id == user_id)
        .order_by(SoilAnalysis.created_at.desc())
        .limit(1)
    ).first()
