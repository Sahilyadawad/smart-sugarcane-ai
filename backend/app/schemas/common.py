"""Shared enums and small response helpers used across the API."""

from __future__ import annotations

from enum import Enum


class SoilType(str, Enum):
    alluvial = "alluvial"
    black = "black"
    red = "red"
    sandy = "sandy"
    clay = "clay"
    loamy = "loamy"
    mixed = "mixed"


class GrowthStage(str, Enum):
    germination = "germination"
    tillering = "tillering"
    grand_growth = "grand_growth"
    maturation = "maturation"
    ratoon_initiation = "ratoon_initiation"


class WeatherCondition(str, Enum):
    clear = "clear"
    partly_cloudy = "partly_cloudy"
    cloudy = "cloudy"
    rainy = "rainy"
    stormy = "stormy"
    humid = "humid"
    dry_wind = "dry_wind"


class IrrigationMethod(str, Enum):
    flood = "flood"
    furrow = "furrow"
    sprinkler = "sprinkler"
    drip = "drip"


class WaterAvailability(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Severity(str, Enum):
    none = "none"
    mild = "mild"
    moderate = "moderate"
    severe = "severe"
    undetermined = "undetermined"


class ClimateType(str, Enum):
    tropical = "tropical"
    subtropical = "subtropical"
    semi_arid = "semi_arid"
    unknown = "unknown"


class PlantingSeason(str, Enum):
    adsali = "adsali"
    pre_seasonal = "pre_seasonal"
    suru = "suru"
    spring = "spring"
    autumn = "autumn"
    general = "general"


class ModelMode(str, Enum):
    """How a prediction was produced - surfaced in every AI response."""

    trained_model = "trained_model"
    rule_engine = "rule_engine"
    demo_heuristic = "demo_heuristic"


HUMAN_LABELS: dict[str, str] = {
    # soil
    "alluvial": "Alluvial Soil",
    "black": "Black Soil",
    "red": "Red Soil",
    "sandy": "Sandy Soil",
    "clay": "Clay Soil",
    "loamy": "Loamy Soil",
    "mixed": "Mixed / Unknown",
    # growth stages
    "germination": "Germination / Establishment",
    "tillering": "Tillering",
    "grand_growth": "Grand Growth / Elongation",
    "maturation": "Maturation / Ripening",
    "ratoon_initiation": "Ratoon Initiation",
    # weather
    "clear": "Clear",
    "partly_cloudy": "Partly Cloudy",
    "cloudy": "Cloudy",
    "rainy": "Rainy",
    "stormy": "Stormy",
    "humid": "Humid",
    "dry_wind": "Dry Wind",
    # irrigation methods
    "flood": "Flood Irrigation",
    "furrow": "Furrow Irrigation",
    "sprinkler": "Sprinkler",
    "drip": "Drip Irrigation",
}


def humanise(value: str | None) -> str:
    if not value:
        return "Unknown"
    return HUMAN_LABELS.get(value, value.replace("_", " ").title())
