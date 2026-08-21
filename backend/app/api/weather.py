"""Weather endpoints (optional live integration)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import weather_service

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/current", response_model=dict)
async def current(city: str | None = Query(default=None, description="City name, e.g. 'Belagavi,IN'")) -> dict:
    """Current conditions, or an honest 'not configured' response."""
    return await weather_service.current_weather(city)


@router.get("/irrigation-prefill", response_model=dict)
async def irrigation_prefill(city: str | None = Query(default=None)) -> dict:
    """Weather mapped straight onto the irrigation form fields."""
    weather = await weather_service.current_weather(city)
    if not weather.get("available"):
        return {"available": False, "notice": weather.get("notice"), "reason": weather.get("reason")}
    return {
        "available": True,
        "city": weather["city"],
        "values": {
            "temperature": weather["temperature"],
            "humidity": weather["humidity"],
            "rainfall": weather["rainfall"],
            "rain_probability": weather["rain_probability"],
            "wind_speed": weather["wind_speed"],
            "weather_condition": weather["weather_condition"],
        },
        "notice": weather["notice"],
        "not_filled": ["soil_moisture", "soil_type", "growth_stage"],
        "not_filled_note": (
            "Soil moisture, soil type and growth stage cannot come from a weather service. "
            "Enter them yourself, or use the soil-moisture simulator."
        ),
    }
