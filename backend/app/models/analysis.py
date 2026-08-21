"""Analysis history models: plant, soil, irrigation and assistant chat."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime
from app.models.user import utcnow


class PlantAnalysis(Base):
    """One uploaded sugarcane plant image and its analysis result."""

    __tablename__ = "plant_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)

    detected_condition: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_label: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    health_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    growth_stage: Mapped[str | None] = mapped_column(String(48), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    model_source: Mapped[str] = mapped_column(String(48), default="demo_heuristic", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Full analysis payload (symptoms, causes, recovery plan, probabilities...)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    user = relationship("User", back_populates="plant_analyses")


class SoilAnalysis(Base):
    """One uploaded soil image and its visual estimate."""

    __tablename__ = "soil_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)

    soil_type: Mapped[str] = mapped_column(String(48), nullable=False)
    soil_label: Mapped[str] = mapped_column(String(96), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    moisture_appearance: Mapped[str] = mapped_column(String(32), nullable=False)
    texture_appearance: Mapped[str] = mapped_column(String(64), nullable=False)
    organic_matter_appearance: Mapped[str] = mapped_column(String(32), nullable=False)

    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    district: Mapped[str | None] = mapped_column(String(128), nullable=True)
    water_availability: Mapped[str | None] = mapped_column(String(32), nullable=True)

    model_source: Mapped[str] = mapped_column(String(48), default="demo_heuristic", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Full payload including variety + fertilizer recommendations and limitations.
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    user = relationship("User", back_populates="soil_analyses")


class IrrigationRecord(Base):
    """One irrigation prediction with the environmental inputs that produced it."""

    __tablename__ = "irrigation_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Inputs
    soil_moisture: Mapped[float] = mapped_column(Float, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rain_probability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    wind_speed: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    weather_condition: Mapped[str] = mapped_column(String(32), default="clear", nullable=False)
    soil_type: Mapped[str] = mapped_column(String(32), default="loamy", nullable=False)
    growth_stage: Mapped[str] = mapped_column(String(48), default="tillering", nullable=False)
    irrigation_method: Mapped[str] = mapped_column(String(32), default="furrow", nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Outputs
    irrigation_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="low", nullable=False)
    water_requirement_mm: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_source: Mapped[str] = mapped_column(String(48), default="rule_engine", nullable=False)

    prediction: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    user = relationship("User", back_populates="irrigation_records")


class ChatMessage(Base):
    """Sugarcane Assistant conversation history."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    user = relationship("User", back_populates="chat_messages")
