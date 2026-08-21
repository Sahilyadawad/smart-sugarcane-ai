"""User account model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, UTCDateTime


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    farm_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Settings page
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    theme: Mapped[str] = mapped_column(String(16), default="light", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    plant_analyses = relationship(
        "PlantAnalysis", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    soil_analyses = relationship(
        "SoilAnalysis", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    irrigation_records = relationship(
        "IrrigationRecord", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User id={self.id} email={self.email!r}>"
