"""Sugarcane variety recommendation.

Every fact shown about a variety comes from ``data/sugarcane_varieties.json``.
This module only *ranks* the entries against the farmer's conditions - it never
invents an agronomic property that is not in the knowledge base.
"""

from __future__ import annotations

from typing import Any

from app.ml.knowledge import varieties_kb
from app.schemas.common import humanise
from app.schemas.recommendation import VarietyRequest

# Weight assigned to each criterion. They sum to 100 so the score reads as a percent.
WEIGHTS = {
    "soil": 30.0,
    "region": 24.0,
    "water": 20.0,
    "climate": 12.0,
    "season": 9.0,
    "irrigation": 5.0,
}

WATER_FIT = {
    # farmer water availability -> {variety water requirement: fit 0-1}
    "low": {"low": 1.00, "medium": 0.45, "high": 0.10},
    "medium": {"low": 0.85, "medium": 1.00, "high": 0.50},
    "high": {"low": 0.70, "medium": 0.95, "high": 1.00},
}


def _normalise(text: str | None) -> str:
    return (text or "").strip().lower()


def _region_fit(request: VarietyRequest, regions: list[str]) -> tuple[float, str | None]:
    haystack = [_normalise(r) for r in regions]
    for candidate, label in ((request.district, "district"), (request.region, "region")):
        needle = _normalise(candidate)
        if not needle:
            continue
        for region in haystack:
            if needle == region or needle in region or region in needle:
                return 1.0, f"Listed for your {label}: {candidate}"
    if request.region or request.district:
        # A named region that does not match is a genuine mismatch, not neutral.
        return 0.25, None
    return 0.55, None  # No region supplied - neutral, slightly below a true match.


def _score_variety(request: VarietyRequest, variety: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    warnings: list[str] = []
    total = 0.0

    # --- soil ---
    soils = [str(s).lower() for s in variety.get("soil_suitability", [])]
    soil_key = request.soil_type.value
    if soil_key == "mixed":
        soil_fit = 0.55
        warnings.append("Soil type was not identified, so the soil match is treated as neutral.")
    elif soil_key in soils:
        soil_fit = 1.0
        reasons.append(f"Suited to {humanise(soil_key)}, which matches your field.")
    else:
        soil_fit = 0.2
        warnings.append(
            f"Not listed for {humanise(soil_key)} - the knowledge base lists it for "
            f"{', '.join(humanise(s) for s in soils) or 'no specific soil'}."
        )
    total += WEIGHTS["soil"] * soil_fit

    # --- region ---
    region_fit, region_reason = _region_fit(request, variety.get("regions", []))
    if region_reason:
        reasons.append(region_reason)
    elif region_fit <= 0.3:
        warnings.append(
            "Your region is not in the recommended list for this variety. "
            f"It is listed for: {', '.join(variety.get('regions', [])[:4])}."
        )
    total += WEIGHTS["region"] * region_fit

    # --- water ---
    requirement = str(variety.get("water_requirement", "medium")).lower()
    water_fit = WATER_FIT.get(request.water_availability.value, WATER_FIT["medium"]).get(requirement, 0.5)
    if water_fit >= 0.85:
        reasons.append(
            f"Its {requirement} water requirement fits your {request.water_availability.value} water availability."
        )
    elif water_fit <= 0.35:
        warnings.append(
            f"Its {requirement} water requirement is a poor fit for {request.water_availability.value} water availability."
        )
    total += WEIGHTS["water"] * water_fit

    # --- climate ---
    climates = [str(c).lower() for c in variety.get("climate", [])]
    climate_key = request.climate.value
    if climate_key == "unknown":
        climate_fit = 0.6
    elif climate_key in climates:
        climate_fit = 1.0
        reasons.append(f"Grown in {climate_key.replace('_', '-')} conditions like yours.")
    else:
        climate_fit = 0.3
    total += WEIGHTS["climate"] * climate_fit

    # --- season ---
    seasons = [str(s).lower() for s in variety.get("planting_seasons", [])]
    season_key = request.planting_season.value
    if season_key == "general":
        season_fit = 0.6
    elif season_key in seasons:
        season_fit = 1.0
        reasons.append(f"Suitable for {season_key.replace('_', ' ')} planting.")
    else:
        season_fit = 0.3
        warnings.append(f"Not listed for {season_key.replace('_', ' ')} planting in this knowledge base.")
    total += WEIGHTS["season"] * season_fit

    # --- irrigation availability ---
    if request.irrigation_available:
        irrigation_fit = 1.0
    else:
        irrigation_fit = {"low": 1.0, "medium": 0.5, "high": 0.1}.get(requirement, 0.5)
        if irrigation_fit <= 0.5:
            warnings.append("Without assured irrigation this variety's water requirement is a real risk.")
    total += WEIGHTS["irrigation"] * irrigation_fit

    if variety.get("ratooning", "").lower().startswith("reported good"):
        reasons.append(variety["ratooning"] + ".")

    return round(total, 1), reasons, warnings


def _match_label(rank: int, score: float) -> str:
    if score < 45:
        return "Weak Match"
    if rank == 0:
        return "Best Match"
    if rank == 1 or score >= 70:
        return "Good Match"
    return "Alternative"


def recommend(request: VarietyRequest) -> dict[str, Any]:
    kb = varieties_kb()
    entries = kb.get("varieties", [])

    scored: list[tuple[float, dict[str, Any], list[str], list[str]]] = []
    for variety in entries:
        score, reasons, warnings = _score_variety(request, variety)
        scored.append((score, variety, reasons, warnings))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[: request.limit]

    matches = []
    for rank, (score, variety, reasons, warnings) in enumerate(top):
        if not reasons:
            reasons = ["Included as a general option - no strong match on your stated criteria."]
        matches.append(
            {
                "id": variety.get("id", ""),
                "name": variety.get("name", "Unknown"),
                "aliases": variety.get("aliases", []),
                "released_by": variety.get("released_by", "Not recorded"),
                "match_score": score,
                "match_label": _match_label(rank, score),
                "why_suitable": reasons,
                "soil_suitability": [humanise(s) for s in variety.get("soil_suitability", [])],
                "water_requirement": str(variety.get("water_requirement", "medium")).title(),
                "climate_suitability": [str(c).replace("_", "-").title() for c in variety.get("climate", [])],
                "maturity": "Early (about 10-12 months)"
                if variety.get("maturity") == "early"
                else "Mid-late (about 12-16 months)",
                "duration_months": variety.get("duration_months", "Not recorded"),
                "planting_seasons": [str(s).replace("_", " ").title() for s in variety.get("planting_seasons", [])],
                "ratooning": variety.get("ratooning", "Not recorded"),
                "disease_notes": variety.get("disease_notes", "Not recorded in this knowledge base."),
                "strengths": variety.get("strengths", []),
                "cautions": list(variety.get("cautions", [])) + warnings,
                "source_note": variety.get("source_note", "Verify locally."),
            }
        )

    criteria: list[str] = [f"Soil type: {humanise(request.soil_type.value)}"]
    if request.region:
        criteria.append(f"Region: {request.region}")
    if request.district:
        criteria.append(f"District: {request.district}")
    if request.climate.value != "unknown":
        criteria.append(f"Climate: {request.climate.value.replace('_', '-')}")
    criteria.append(f"Water availability: {request.water_availability.value}")
    criteria.append(f"Irrigation available: {'yes' if request.irrigation_available else 'no'}")
    if request.planting_season.value != "general":
        criteria.append(f"Planting season: {request.planting_season.value.replace('_', ' ')}")

    return {
        "matches": matches,
        "considered": len(entries),
        "criteria_used": criteria,
        "score_explanation": (
            "The match score is a weighted fit against the criteria you supplied "
            f"(soil {WEIGHTS['soil']:.0f} %, region {WEIGHTS['region']:.0f} %, water {WEIGHTS['water']:.0f} %, "
            f"climate {WEIGHTS['climate']:.0f} %, season {WEIGHTS['season']:.0f} %, "
            f"irrigation {WEIGHTS['irrigation']:.0f} %). It is a recommendation score, "
            "not a predicted yield or a guaranteed agricultural outcome."
        ),
        "disclaimer": (
            "Recommendation scores rank knowledge-base entries against your stated conditions. "
            "They are not guaranteed agricultural outcomes. Confirm variety choice and seed "
            "availability with your local Sugarcane Research Station or sugar factory cane department."
        ),
        "data_disclaimer": kb.get("data_disclaimer", ""),
        "last_reviewed": kb.get("last_reviewed", "unknown"),
    }
