"""Unified history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.auth import MessageResponse
from app.schemas.history import HistoryDetail, HistoryPage
from app.services import history_service

router = APIRouter(prefix="/history", tags=["History"])

VALID_KINDS = {"plant", "soil", "irrigation"}


@router.get("", response_model=HistoryPage)
def list_history(
    kind: str | None = Query(default=None, description="plant | soil | irrigation | all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HistoryPage:
    return HistoryPage(**history_service.list_history(db, current_user, kind, page, page_size))


@router.get("/{kind}/{record_id}", response_model=HistoryDetail)
def get_detail(
    kind: str,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HistoryDetail:
    if kind not in VALID_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown history kind '{kind}'. Use one of: {', '.join(sorted(VALID_KINDS))}.",
        )
    detail = history_service.get_detail(db, current_user, kind, record_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History record not found.")
    return HistoryDetail(**detail)


@router.delete("/{kind}/{record_id}", response_model=MessageResponse)
def delete_record(
    kind: str,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    if kind not in VALID_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown history kind '{kind}'. Use one of: {', '.join(sorted(VALID_KINDS))}.",
        )
    if not history_service.delete_record(db, current_user, kind, record_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History record not found.")
    return MessageResponse(detail="Record deleted.")


@router.delete("", response_model=MessageResponse)
def clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Data / privacy control: delete every stored analysis for this account."""
    removed = history_service.clear_all(db, current_user)
    return MessageResponse(detail=f"Deleted {removed} record(s) and their uploaded images.")
