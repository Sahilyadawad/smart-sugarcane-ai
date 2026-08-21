"""Sugarcane Assistant chat schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    language: str = Field(default="en", max_length=8)


class ChatSource(BaseModel):
    kind: str
    label: str
    detail: str


class ChatResponse(BaseModel):
    reply: str
    topic: str
    confidence: str  # high | medium | low
    used_context: list[ChatSource]
    suggested_questions: list[str]
    disclaimer: str
    created_at: datetime


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    topic: str | None = None
    created_at: datetime


class AssistantInfo(BaseModel):
    engine: str
    languages_supported: list[str]
    languages_planned: list[str]
    notes: list[str]
