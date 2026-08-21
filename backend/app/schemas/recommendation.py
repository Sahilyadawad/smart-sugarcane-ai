"""Variety and fertilizer recommendation schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import (
    ClimateType,
    GrowthStage,
    PlantingSeason,
    SoilType,
    WaterAvailability,
)


# --------------------------------------------------------------------- variety
class VarietyRequest(BaseModel):
    soil_type: SoilType = SoilType.mixed
    region: str | None = Field(default=None, max_length=128)
    district: str | None = Field(default=None, max_length=128)
    climate: ClimateType = ClimateType.unknown
    irrigation_available: bool = True
    water_availability: WaterAvailability = WaterAvailability.medium
    planting_season: PlantingSeason = PlantingSeason.general
    limit: int = Field(default=4, ge=1, le=12)


class VarietyMatch(BaseModel):
    id: str
    name: str
    aliases: list[str]
    released_by: str
    match_score: float
    match_label: str  # Best Match / Good Match / Alternative
    why_suitable: list[str]
    soil_suitability: list[str]
    water_requirement: str
    climate_suitability: list[str]
    maturity: str
    duration_months: str
    planting_seasons: list[str]
    ratooning: str
    disease_notes: str
    strengths: list[str]
    cautions: list[str]
    source_note: str


class VarietyRecommendation(BaseModel):
    matches: list[VarietyMatch]
    considered: int
    criteria_used: list[str]
    score_explanation: str
    disclaimer: str
    data_disclaimer: str
    last_reviewed: str


# ------------------------------------------------------------------ fertilizer
class FertilizerRequest(BaseModel):
    growth_stage: GrowthStage = GrowthStage.tillering
    soil_type: SoilType = SoilType.mixed
    water_availability: WaterAvailability = WaterAvailability.medium
    irrigation_available: bool = True
    plant_condition: str | None = Field(
        default=None, description="Disease key from a plant analysis, e.g. 'red_rot' or 'healthy'"
    )
    organic_matter_appearance: str | None = Field(
        default=None, description="low | moderate | high, from the soil image estimate"
    )
    # Optional laboratory values - only used when supplied.
    nitrogen_kg_ha: float | None = Field(default=None, ge=0, le=2000)
    phosphorus_kg_ha: float | None = Field(default=None, ge=0, le=2000)
    potassium_kg_ha: float | None = Field(default=None, ge=0, le=2000)
    soil_ph: float | None = Field(default=None, ge=0, le=14)


class NutrientFocus(BaseModel):
    nutrient: str
    priority: str
    reason: str
    lab_rating: str | None = None


class FertilizerRecommendation(BaseModel):
    growth_stage: str
    growth_stage_label: str
    typical_window: str
    stage_goal: str
    stage_focus: str

    nutrient_focus: list[NutrientFocus]
    suggested_management: list[str]
    split_schedule: list[dict]
    organic_matter_advice: str
    soil_specific_notes: list[str]
    ph_note: str | None = None
    water_note: str
    plant_health_note: str
    lab_values_used: bool

    general_practices: list[str]
    disclaimer: str
    data_disclaimer: str
