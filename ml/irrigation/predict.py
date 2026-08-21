"""Command-line irrigation prediction - the same code path the API uses.

Handy for checking the model without starting the web server.

Usage
-----
    python ml/irrigation/predict.py --soil-moisture 28 --temperature 36 --humidity 40
    python ml/irrigation/predict.py --soil-moisture 62 --temperature 27 --humidity 78 \
        --rainfall 12 --rain-probability 80 --growth-stage maturation --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.ml import irrigation_engine as engine  # noqa: E402
from app.ml import irrigation_model  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--soil-moisture", type=float, required=True, help="percent, 0-100")
    parser.add_argument("--temperature", type=float, required=True, help="degrees Celsius")
    parser.add_argument("--humidity", type=float, required=True, help="percent, 0-100")
    parser.add_argument("--rainfall", type=float, default=0.0, help="mm in the last 24 h")
    parser.add_argument("--rain-probability", type=float, default=0.0, help="percent, next 24 h")
    parser.add_argument("--wind-speed", type=float, default=5.0, help="km/h")
    parser.add_argument("--weather-condition", choices=engine.WEATHER_CONDITIONS, default="clear")
    parser.add_argument("--soil-type", choices=engine.SOIL_TYPES, default="loamy")
    parser.add_argument("--growth-stage", choices=engine.GROWTH_STAGES, default="tillering")
    parser.add_argument("--irrigation-method", choices=engine.IRRIGATION_METHODS, default="furrow")
    parser.add_argument("--area-hectares", type=float, default=1.0)
    parser.add_argument("--json", action="store_true", help="print raw JSON instead of a report")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    payload = {
        "soil_moisture": args.soil_moisture,
        "temperature": args.temperature,
        "humidity": args.humidity,
        "rainfall": args.rainfall,
        "rain_probability": args.rain_probability,
        "wind_speed": args.wind_speed,
        "weather_condition": args.weather_condition,
        "soil_type": args.soil_type,
        "growth_stage": args.growth_stage,
        "irrigation_method": args.irrigation_method,
        "area_hectares": args.area_hectares,
    }

    result = irrigation_model.predict(payload)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    status = irrigation_model.status()
    print("=" * 70)
    print("SMART SUGARCANE AI - IRRIGATION RECOMMENDATION")
    print("=" * 70)
    print(f"Prediction source : {result['model_label']}")
    if not status["trained_model_available"]:
        print("                    (no trained model file - run ml/irrigation/train.py)")
    print("-" * 70)
    print(f"Irrigation Required : {'YES' if result['irrigation_required'] else 'NO'}")
    print(f"Priority            : {result['priority'].upper()}")
    if result["irrigation_required"]:
        print(f"Recommended Water   : {result['water_requirement_mm']:.1f} mm net "
              f"({result['gross_requirement_mm']:.1f} mm applied in field)")
        print(f"Recommended Duration: {result['duration_minutes']} minutes")
        print(f"Water Volume        : {result['water_volume_liters']:,.0f} litres "
              f"over {args.area_hectares:g} ha")
        print(f"Best Time           : {result['recommended_window']}")
    print(f"Soil Moisture Status: {result['soil_moisture_status']}")
    print(f"Next Check          : in about {result['next_check_hours']} hours")
    print("-" * 70)
    print(f"Reason        : {result['reason']}")
    print(f"Rain Forecast : {result['rain_forecast_note']}")
    print("-" * 70)
    print("How this was worked out:")
    for line in result["explanation"]:
        print(f"  - {line}")
    print("-" * 70)
    print("Water saving tips:")
    for tip in result["water_saving_tips"]:
        print(f"  - {tip}")
    print("-" * 70)
    for note in result["model_notes"]:
        print(f"NOTE: {note}")
    print("=" * 70)


if __name__ == "__main__":
    main()
