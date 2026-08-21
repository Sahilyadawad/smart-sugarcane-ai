"""Loaders for the editable JSON knowledge base in ``data/``.

Everything the recommendation engines say about varieties, fertilizer and
diseases comes from these files, so the agronomy content can be corrected
without touching a line of Python.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


def _load(filename: str) -> dict[str, Any]:
    path: Path = settings.data_dir / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Knowledge base file not found: {path}. "
            "It should live in the project-level data/ directory."
        )
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def varieties_kb() -> dict[str, Any]:
    return _load("sugarcane_varieties.json")


@lru_cache(maxsize=1)
def fertilizer_kb() -> dict[str, Any]:
    return _load("fertilizer_rules.json")


@lru_cache(maxsize=1)
def disease_kb() -> dict[str, Any]:
    return _load("disease_recommendations.json")


@lru_cache(maxsize=1)
def soil_kb() -> dict[str, Any]:
    return _load("soil_profiles.json")


def reload_all() -> None:
    """Drop the caches so edited JSON files are picked up without a restart."""
    for loader in (varieties_kb, fertilizer_kb, disease_kb, soil_kb):
        loader.cache_clear()


def knowledge_status() -> dict[str, Any]:
    """Small summary used by /api/system/status."""
    status: dict[str, Any] = {}
    for name, loader in (
        ("sugarcane_varieties.json", varieties_kb),
        ("fertilizer_rules.json", fertilizer_kb),
        ("disease_recommendations.json", disease_kb),
        ("soil_profiles.json", soil_kb),
    ):
        try:
            data = loader()
            status[name] = {
                "loaded": True,
                "schema_version": data.get("schema_version"),
                "last_reviewed": data.get("last_reviewed"),
            }
        except FileNotFoundError as exc:
            status[name] = {"loaded": False, "error": str(exc)}
    return status
