"""Unified history and dashboard schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HistoryItem(BaseModel):
    id: int
    kind: str  # plant | soil | irrigation
    title: str
    subtitle: str
    badge: str
    badge_tone: str  # success | warning | danger | info
    image_url: str | None = None
    created_at: datetime


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    page_size: int
    counts: dict


class HistoryDetail(BaseModel):
    id: int
    kind: str
    created_at: datetime
    payload: dict


class DashboardSummary(BaseModel):
    user_name: str
    greeting: str
    totals: dict
    latest_plant: dict | None
    latest_soil: dict | None
    latest_irrigation: dict | None
    weather: dict | None
    plant_trend: dict
    irrigation_chart: list[dict]
    quick_tips: list[str]
    model_status: dict
