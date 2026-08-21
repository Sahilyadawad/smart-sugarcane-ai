"""System status - the single honest answer to "is the AI real or demo?"."""

from __future__ import annotations

import sys

from fastapi import APIRouter

from app.core.config import settings
from app.ml import disease_model, irrigation_model, soil_model
from app.ml.image_features import HAS_CV2
from app.ml.knowledge import knowledge_status

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health", response_model=dict)
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/status", response_model=dict)
def status() -> dict:
    irrigation = irrigation_model.status()
    disease = disease_model.status()
    soil = soil_model.status()

    def label(entry: dict) -> str:
        if entry["trained_model_available"]:
            return "Trained model"
        return "Rule engine" if entry["model_source"] == "rule_engine" else "Demo heuristic"

    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "python": sys.version.split()[0],
        "model_mode": settings.MODEL_MODE,
        "opencv_available": HAS_CV2,
        "models": {
            "irrigation": {**irrigation, "label": label(irrigation)},
            "disease": {**disease, "label": label(disease)},
            "soil": {**soil, "label": label(soil)},
        },
        "knowledge_base": knowledge_status(),
        "honesty_notice": (
            "Any module reported as 'Demo heuristic' is a transparent colour/texture estimate, not a "
            "trained neural network, and must not be treated as a diagnosis. Any module reported as "
            "'Rule engine' is a documented water-balance calculation. Only 'Trained model' means a "
            "machine-learning model file is loaded and in use."
        ),
    }
