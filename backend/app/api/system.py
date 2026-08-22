"""System status - the single honest answer to "is the AI real or demo?"."""

from __future__ import annotations

import sys

from fastapi import APIRouter

from app.core.config import settings
from app.ml import disease_model, irrigation_model, soil_model
from app.ml.image_features import HAS_CV2
from app.ml.knowledge import knowledge_status

router = APIRouter(prefix="/system", tags=["System"])


def _database_state() -> dict:
    """Live check of the database that is ACTUALLY in use.

    Reports the engine really bound to the app, not the configured URL - those
    differ whenever DATABASE_URL was rejected and the SQLite fallback kicked in,
    and reporting the intended one would be actively misleading.
    """
    from sqlalchemy import text

    from app.database import ENGINE_ERROR, engine

    # Never expose credentials from a Postgres URL in an API response.
    actual_uri = engine.url.render_as_string(hide_password=True)
    kind = engine.dialect.name  # "sqlite", "postgresql", ...
    ephemeral = kind == "sqlite" and settings.is_serverless

    state: dict = {
        "kind": kind,
        "uri": actual_uri,
        "ephemeral": ephemeral,
    }

    if ENGINE_ERROR:
        state["configured_url_rejected"] = ENGINE_ERROR
        state["note"] = (
            "DATABASE_URL could not be used, so a local SQLite fallback is running instead. "
            "Fix the connection string and redeploy."
        )
    if ephemeral:
        state["warning"] = (
            "SQLite on a serverless host is wiped between invocations - accounts and history "
            "will not survive. Set DATABASE_URL to a hosted Postgres connection string."
        )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        state["connected"] = True
    except Exception as exc:  # noqa: BLE001
        state["connected"] = False
        state["error"] = f"{type(exc).__name__}: {exc}"
        state["hint"] = "Set DATABASE_URL to a valid connection string, then redeploy."

    return state


@router.get("/health", response_model=dict)
def health() -> dict:
    """Liveness only - deliberately does not touch the database."""
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
        "serverless": settings.is_serverless,
        "uploads_persisted": settings.persist_uploads,
        "database": _database_state(),
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
