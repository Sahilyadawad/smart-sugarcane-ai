"""Variety and fertilizer recommendation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_optional_user
from app.ml.knowledge import fertilizer_kb, reload_all, varieties_kb
from app.models import User
from app.schemas.recommendation import (
    FertilizerRecommendation,
    FertilizerRequest,
    VarietyRecommendation,
    VarietyRequest,
)
from app.services import fertilizer_service, variety_service

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("/variety", response_model=VarietyRecommendation)
def recommend_variety(payload: VarietyRequest) -> VarietyRecommendation:
    return VarietyRecommendation(**variety_service.recommend(payload))


@router.post("/fertilizer", response_model=FertilizerRecommendation)
def recommend_fertilizer(payload: FertilizerRequest) -> FertilizerRecommendation:
    return FertilizerRecommendation(**fertilizer_service.recommend(payload))


@router.get("/varieties", response_model=dict)
def list_varieties() -> dict:
    """The full variety knowledge base, exactly as stored in data/."""
    kb = varieties_kb()
    return {
        "count": len(kb.get("varieties", [])),
        "last_reviewed": kb.get("last_reviewed"),
        "data_disclaimer": kb.get("data_disclaimer"),
        "field_notes": kb.get("field_notes", {}),
        "varieties": kb.get("varieties", []),
    }


@router.get("/fertilizer-rules", response_model=dict)
def list_fertilizer_rules() -> dict:
    kb = fertilizer_kb()
    return {
        "last_reviewed": kb.get("last_reviewed"),
        "data_disclaimer": kb.get("data_disclaimer"),
        "growth_stages": kb.get("growth_stages", {}),
        "soil_type_adjustments": kb.get("soil_type_adjustments", {}),
        "npk_test_rating": kb.get("npk_test_rating", {}),
        "ph_guidance": kb.get("ph_guidance", []),
        "general_practices": kb.get("general_practices", []),
        "final_disclaimer": kb.get("final_disclaimer"),
    }


@router.post("/reload-knowledge", response_model=dict)
def reload_knowledge(current_user: User | None = Depends(get_optional_user)) -> dict:
    """Re-read the JSON knowledge base after editing it, without a server restart."""
    reload_all()
    return {
        "detail": "Knowledge base reloaded from data/.",
        "varieties": len(varieties_kb().get("varieties", [])),
    }
