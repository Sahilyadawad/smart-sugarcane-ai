"""API routers, aggregated onto one router mounted at ``/api``."""

from fastapi import APIRouter

from app.api import (
    assistant,
    auth,
    dashboard,
    history,
    irrigation,
    plant_analysis,
    recommendations,
    soil_analysis,
    system,
    weather,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(irrigation.router)
api_router.include_router(plant_analysis.router)
api_router.include_router(soil_analysis.router)
api_router.include_router(recommendations.router)
api_router.include_router(history.router)
api_router.include_router(assistant.router)
api_router.include_router(weather.router)
api_router.include_router(system.router)

__all__ = ["api_router"]
