"""Weather integration.

Live weather is optional. With an OpenWeatherMap key in ``.env`` the irrigation
form can be pre-filled from real observations; without one the endpoint says so
plainly instead of inventing numbers.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
TIMEOUT = httpx.Timeout(8.0)

#: OpenWeatherMap condition codes mapped onto the enum the irrigation model uses.
def _map_condition(owm_main: str, description: str, humidity: float, wind_kmh: float) -> str:
    main = (owm_main or "").lower()
    if main in {"thunderstorm", "squall", "tornado"}:
        return "stormy"
    if main in {"rain", "drizzle"}:
        return "rainy"
    if main in {"snow"}:
        return "rainy"
    if main in {"clouds"}:
        return "cloudy" if "overcast" in (description or "").lower() else "partly_cloudy"
    if main in {"mist", "fog", "haze"}:
        return "humid"
    # Clear sky - split by how dry and windy it is.
    if wind_kmh >= 20 and humidity < 45:
        return "dry_wind"
    if humidity >= 75:
        return "humid"
    return "clear"


def is_configured() -> bool:
    return bool(settings.OPENWEATHER_API_KEY.strip())


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "city": settings.DEFAULT_WEATHER_CITY,
        "notice": (
            "Live weather is not configured. Enter the weather values manually on the irrigation "
            "page - the prediction works exactly the same either way."
        ),
        "setup_hint": (
            "Add a free OpenWeatherMap API key as OPENWEATHER_API_KEY in backend/.env to enable "
            "automatic weather fill."
        ),
    }


async def current_weather(city: str | None = None) -> dict[str, Any]:
    if not is_configured():
        return _unavailable("No OPENWEATHER_API_KEY configured.")

    location = (city or settings.DEFAULT_WEATHER_CITY).strip()
    params = {"q": location, "appid": settings.OPENWEATHER_API_KEY, "units": "metric"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(CURRENT_URL, params=params)
            if response.status_code == 401:
                return _unavailable("OpenWeatherMap rejected the API key (401).")
            if response.status_code == 404:
                return _unavailable(f"OpenWeatherMap does not recognise the location '{location}'.")
            response.raise_for_status()
            data = response.json()

            rain_probability = 0.0
            try:
                forecast = await client.get(FORECAST_URL, params={**params, "cnt": 8})
                if forecast.status_code == 200:
                    entries = forecast.json().get("list", [])
                    pops = [float(item.get("pop", 0.0)) for item in entries[:8]]
                    if pops:
                        rain_probability = round(max(pops) * 100, 0)
            except httpx.HTTPError:
                logger.info("Forecast lookup failed; continuing without rain probability.")
    except httpx.HTTPError as exc:
        logger.warning("Weather lookup failed: %s", exc)
        return _unavailable(f"Could not reach OpenWeatherMap: {exc}")

    main = data.get("main", {})
    wind = data.get("wind", {})
    weather_list = data.get("weather", [{}])
    weather_main = weather_list[0].get("main", "")
    description = weather_list[0].get("description", "")

    humidity = float(main.get("humidity", 60))
    wind_kmh = round(float(wind.get("speed", 0.0)) * 3.6, 1)
    rainfall = float(data.get("rain", {}).get("3h", data.get("rain", {}).get("1h", 0.0)))

    return {
        "available": True,
        "city": data.get("name", location),
        "country": data.get("sys", {}).get("country", ""),
        "temperature": round(float(main.get("temp", 0.0)), 1),
        "feels_like": round(float(main.get("feels_like", 0.0)), 1),
        "humidity": humidity,
        "pressure": main.get("pressure"),
        "wind_speed": wind_kmh,
        "rainfall": round(rainfall, 2),
        "rain_probability": rain_probability,
        "weather_condition": _map_condition(weather_main, description, humidity, wind_kmh),
        "description": description.title(),
        "icon": weather_list[0].get("icon", ""),
        "source": "OpenWeatherMap",
        "notice": (
            "Live observation from OpenWeatherMap for the named city, which may be some distance "
            "from your field. Adjust the values if your local conditions differ."
        ),
    }


def summary_for_dashboard(weather: dict[str, Any]) -> dict[str, Any]:
    if not weather.get("available"):
        return {
            "available": False,
            "headline": "Weather not configured",
            "detail": weather.get("notice", ""),
        }
    return {
        "available": True,
        "headline": f"{weather['temperature']:.0f} °C, {weather.get('description', '')}",
        "detail": (
            f"Humidity {weather['humidity']:.0f} % | Wind {weather['wind_speed']:.0f} km/h | "
            f"Rain chance {weather['rain_probability']:.0f} %"
        ),
        "city": weather.get("city"),
        "temperature": weather.get("temperature"),
        "humidity": weather.get("humidity"),
        "wind_speed": weather.get("wind_speed"),
        "rain_probability": weather.get("rain_probability"),
        "weather_condition": weather.get("weather_condition"),
        "icon": weather.get("icon"),
    }
