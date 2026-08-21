"""Soil image analysis schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ClimateType, PlantingSeason, SoilType, WaterAvailability


class SoilClassProbability(BaseModel):
    key: str
    label: str
    probability: float


class SoilVisualEstimate(BaseModel):
    soil_type: str
    soil_label: str
    confidence: float

    colour_description: str
    dominant_rgb: list[int]
    texture_appearance: str
    moisture_appearance: str
    moisture_label: str
    moisture_note: str
    organic_matter_appearance: str
    organic_matter_label: str
    organic_matter_note: str

    visual_description: str
    general_properties: list[str]
    sugarcane_suitability: str
    management_notes: list[str]
    irrigation_note: str

    probabilities: list[SoilClassProbability]
    image_quality: dict


class SoilFarmContext(BaseModel):
    """Optional extra information the farmer can supply to sharpen recommendations."""

    region: str | None = Field(default=None, max_length=128, description="State or region")
    district: str | None = Field(default=None, max_length=128)
    climate: ClimateType = ClimateType.unknown
    irrigation_available: bool = True
    water_availability: WaterAvailability = WaterAvailability.medium
    planting_season: PlantingSeason = PlantingSeason.general
    soil_type_override: SoilType | None = Field(
        default=None, description="Set this if you already know your soil type from a lab test"
    )


class SoilAnalysisResult(BaseModel):
    id: int | None = None
    image_url: str | None = None

    estimate: SoilVisualEstimate
    limitations: list[str]
    improve_photo_tips: list[str]

    varieties: dict | None = None
    fertilizer: dict | None = None

    model_source: str
    model_label: str
    is_demo: bool
    model_notes: list[str]
    disclaimer: str
    lab_test_notice: str

    created_at: datetime | None = None


class SoilAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    soil_type: str
    soil_label: str
    confidence: float
    moisture_appearance: str
    texture_appearance: str
    organic_matter_appearance: str
    region: str | None
    water_availability: str | None
    model_source: str
    is_demo: bool
    result: dict
    created_at: datetime


class SoilModelStatus(BaseModel):
    trained_model_available: bool
    model_path: str | None
    model_source: str
    mode: str
    class_names: list[str]
    notes: list[str]
