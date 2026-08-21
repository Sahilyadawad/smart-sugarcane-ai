"""Plant disease analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.ml import disease_model, image_features
from app.models import PlantAnalysis, User
from app.schemas.common import GrowthStage
from app.schemas.plant import (
    PlantAnalysisOut,
    PlantAnalysisResult,
    PlantModelStatus,
    PlantTrend,
)
from app.services import plant_service, storage

router = APIRouter(prefix="/plants", tags=["Plant Analysis"])


@router.post("/analyze", response_model=PlantAnalysisResult)
async def analyze(
    file: UploadFile = File(..., description="Photo of a sugarcane leaf, stem or plant"),
    growth_stage: GrowthStage | None = Form(default=None),
    notes: str | None = Form(default=None),
    save: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlantAnalysisResult:
    data = await storage.read_image_upload(file)
    image = image_features.load_image(data)

    result = plant_service.analyse(
        image,
        growth_stage=growth_stage.value if growth_stage else None,
        notes=notes,
    )

    if save:
        image_path, image_url = storage.save_image(data, "plants", current_user.id, file.filename)
        record = plant_service.save_analysis(db, current_user.id, result, image_path, image_url)
        result["id"] = record.id
        result["image_url"] = image_url
        result["created_at"] = record.created_at

    return PlantAnalysisResult(**result)


@router.get("/history", response_model=list[PlantAnalysisOut])
def history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PlantAnalysisOut]:
    rows = db.scalars(
        select(PlantAnalysis)
        .where(PlantAnalysis.user_id == current_user.id)
        .order_by(PlantAnalysis.created_at.desc())
        .limit(limit)
    ).all()
    return [PlantAnalysisOut.model_validate(row) for row in rows]


@router.get("/trend", response_model=PlantTrend)
def trend(
    limit: int = Query(default=12, ge=2, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlantTrend:
    """Plant Health History: how the crop has changed across uploads."""
    return PlantTrend(**plant_service.plant_trend(db, current_user.id, limit))


@router.get("/model-status", response_model=PlantModelStatus)
def model_status() -> PlantModelStatus:
    return PlantModelStatus(**disease_model.status())


@router.post("/reload-model", response_model=PlantModelStatus)
def reload_model(current_user: User = Depends(get_current_user)) -> PlantModelStatus:
    disease_model.reload_model()
    return PlantModelStatus(**disease_model.status())


@router.get("/{analysis_id}", response_model=PlantAnalysisOut)
def get_one(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlantAnalysisOut:
    row = db.get(PlantAnalysis, analysis_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plant analysis not found.")
    return PlantAnalysisOut.model_validate(row)
