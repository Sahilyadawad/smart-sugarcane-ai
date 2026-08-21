"""Irrigation prediction request / response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import (
    GrowthStage,
    IrrigationMethod,
    Priority,
    SoilType,
    WeatherCondition,
)


class IrrigationInput(BaseModel):
    """Environmental inputs for an irrigation decision.

    These are exactly the parameters described in the project block diagram:
    soil data (moisture, type), weather data (temperature, humidity, rainfall,
    wind) and crop data (growth stage).
    """

    soil_moisture: float = Field(ge=0, le=100, description="Volumetric soil moisture, percent")
    temperature: float = Field(ge=-10, le=60, description="Air temperature, degrees Celsius")
    humidity: float = Field(ge=0, le=100, description="Relative humidity, percent")
    rainfall: float = Field(default=0.0, ge=0, le=500, description="Rainfall in the last 24 h, mm")
    rain_probability: float = Field(
        default=0.0, ge=0, le=100, description="Probability of rain in the next 24 h, percent"
    )
    wind_speed: float = Field(default=5.0, ge=0, le=150, description="Wind speed, km/h")
    weather_condition: WeatherCondition = WeatherCondition.clear
    soil_type: SoilType = SoilType.loamy
    growth_stage: GrowthStage = GrowthStage.tillering
    irrigation_method: IrrigationMethod = IrrigationMethod.furrow
    area_hectares: float = Field(default=1.0, gt=0, le=1000)
    save: bool = Field(default=True, description="Store this prediction in history")


class FeatureContribution(BaseModel):
    feature: str
    label: str
    value: float
    impact: float = Field(description="Signed effect on the water requirement, mm")
    note: str


class IrrigationResult(BaseModel):
    irrigation_required: bool
    priority: Priority
    water_requirement_mm: float
    water_volume_liters: float
    water_volume_per_hectare: float
    duration_minutes: int
    recommended_window: str
    next_check_hours: int

    soil_moisture_status: str
    deficit_mm: float
    crop_water_use_mm: float
    effective_rain_mm: float
    reference_et_mm: float
    crop_coefficient: float

    reason: str
    explanation: list[str]
    water_saving_tips: list[str]
    rain_forecast_note: str

    model_source: str
    model_label: str
    model_confidence: float
    model_notes: list[str]
    feature_contributions: list[FeatureContribution]
    disclaimer: str

    record_id: int | None = None
    created_at: datetime | None = None


class IrrigationRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    soil_moisture: float
    temperature: float
    humidity: float
    rainfall: float
    rain_probability: float
    wind_speed: float
    weather_condition: str
    soil_type: str
    growth_stage: str
    irrigation_method: str
    area_hectares: float
    irrigation_required: bool
    priority: str
    water_requirement_mm: float
    duration_minutes: int
    model_source: str
    prediction: dict
    created_at: datetime


class IrrigationModelStatus(BaseModel):
    trained_model_available: bool
    model_path: str | None
    model_source: str
    trained_at: str | None = None
    dataset_rows: int | None = None
    dataset_type: str | None = None
    metrics: dict | None = None
    notes: list[str]
