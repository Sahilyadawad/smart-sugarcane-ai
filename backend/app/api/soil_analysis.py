"""Soil image analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.ml import image_features, soil_model
from app.models import SoilAnalysis, User
from app.schemas.common import ClimateType, PlantingSeason, SoilType, WaterAvailability
from app.schemas.soil import SoilAnalysisOut, SoilAnalysisResult, SoilFarmContext, SoilModelStatus
from app.services import soil_service, storage

router = APIRouter(prefix="/soil", tags=["Soil Analysis"])


@router.post("/analyze", response_model=SoilAnalysisResult)
async def analyze(
    file: UploadFile = File(..., description="Photo of bare, freshly turned soil"),
    region: str | None = Form(default=None),
    district: str | None = Form(default=None),
    climate: ClimateType = Form(default=ClimateType.unknown),
    irrigation_available: bool = Form(default=True),
    water_availability: WaterAvailability = Form(default=WaterAvailability.medium),
    planting_season: PlantingSeason = Form(default=PlantingSeason.general),
    soil_type_override: SoilType | None = Form(default=None),
    save: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SoilAnalysisResult:
    data = await storage.read_image_upload(file)
    image = image_features.load_image(data)

    context = SoilFarmContext(
        region=region,
        district=district,
        climate=climate,
        irrigation_available=irrigation_available,
        water_availability=water_availability,
        planting_season=planting_season,
        soil_type_override=soil_type_override,
    )

    result = soil_service.analyse(image, context)

    if save:
        image_path, image_url = storage.save_image(data, "soil", current_user.id, file.filename)
        record = soil_service.save_analysis(db, current_user.id, result, image_path, image_url, context)
        result["id"] = record.id
        result["image_url"] = image_url
        result["created_at"] = record.created_at

    return SoilAnalysisResult(**result)


@router.get("/history", response_model=list[SoilAnalysisOut])
def history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SoilAnalysisOut]:
    rows = db.scalars(
        select(SoilAnalysis)
        .where(SoilAnalysis.user_id == current_user.id)
        .order_by(SoilAnalysis.created_at.desc())
        .limit(limit)
    ).all()
    return [SoilAnalysisOut.model_validate(row) for row in rows]


@router.get("/model-status", response_model=SoilModelStatus)
def model_status() -> SoilModelStatus:
    return SoilModelStatus(**soil_model.status())


@router.post("/reload-model", response_model=SoilModelStatus)
def reload_model(current_user: User = Depends(get_current_user)) -> SoilModelStatus:
    soil_model.reload_model()
    return SoilModelStatus(**soil_model.status())


@router.get("/{analysis_id}", response_model=SoilAnalysisOut)
def get_one(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SoilAnalysisOut:
    row = db.get(SoilAnalysis, analysis_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soil analysis not found.")
    return SoilAnalysisOut.model_validate(row)
