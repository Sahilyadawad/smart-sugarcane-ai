"""Plant disease analysis schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassProbability(BaseModel):
    key: str
    label: str
    probability: float


class RecoveryPlan(BaseModel):
    """The "How to improve this plant" block."""

    immediate_action: list[str]
    recovery_plan: list[str]
    irrigation_advice: dict
    soil_and_nutrient_advice: list[str]
    prevention_plan: list[str]
    monitoring_schedule: list[str]


class PlantAnalysisResult(BaseModel):
    id: int | None = None
    image_url: str | None = None

    detected_condition: str
    condition_label: str
    pathogen_type: str
    confidence: float
    severity: str
    severity_note: str
    health_score: float

    short_description: str
    symptoms: list[str]
    causes: list[str]
    management: list[str]
    prevention: list[str]

    recovery: RecoveryPlan

    probabilities: list[ClassProbability]
    image_quality: dict

    model_source: str
    model_label: str
    is_demo: bool
    model_notes: list[str]
    disclaimer: str

    growth_stage: str | None = None
    created_at: datetime | None = None


class PlantAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    detected_condition: str
    condition_label: str
    confidence: float
    severity: str
    health_score: float
    growth_stage: str | None
    model_source: str
    is_demo: bool
    result: dict
    created_at: datetime


class PlantTrendPoint(BaseModel):
    id: int
    date: datetime
    condition: str
    condition_label: str
    severity: str
    confidence: float
    health_score: float
    image_url: str


class PlantTrend(BaseModel):
    points: list[PlantTrendPoint]
    direction: str  # improving | stable | deteriorating | insufficient_data
    summary: str
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    comparison_note: str


class PlantModelStatus(BaseModel):
    trained_model_available: bool
    model_path: str | None
    model_source: str
    mode: str
    class_names: list[str]
    notes: list[str]
