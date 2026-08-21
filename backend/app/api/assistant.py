"""Sugarcane Assistant chat endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.assistant import (
    AssistantInfo,
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
)
from app.schemas.auth import MessageResponse
from app.services import assistant_service

router = APIRouter(prefix="/assistant", tags=["Sugarcane Assistant"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    return ChatResponse(**assistant_service.answer(db, current_user, payload.message, payload.language))


@router.get("/history", response_model=list[ChatMessageOut])
def history(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatMessageOut]:
    rows = assistant_service.history(db, current_user, limit)
    return [
        ChatMessageOut(
            id=row.id, role=row.role, content=row.content, topic=row.topic, created_at=row.created_at
        )
        for row in rows
    ]


@router.delete("/history", response_model=MessageResponse)
def clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    removed = assistant_service.clear_history(db, current_user)
    return MessageResponse(detail=f"Cleared {removed} chat message(s).")


@router.get("/info", response_model=AssistantInfo)
def info() -> AssistantInfo:
    """What the assistant is and, importantly, what it is not."""
    return AssistantInfo(**assistant_service.info())


@router.get("/suggestions", response_model=list[str])
def suggestions() -> list[str]:
    return assistant_service.SUGGESTED_QUESTIONS
