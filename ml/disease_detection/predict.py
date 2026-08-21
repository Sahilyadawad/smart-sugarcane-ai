"""Command-line sugarcane disease prediction.

Uses the same code path as the API, so whatever this prints is exactly what the
website would show - including the DEMO label when no trained model is present.

Usage
-----
    python ml/disease_detection/predict.py path/to/leaf.jpg
    python ml/disease_detection/predict.py path/to/leaf.jpg --json
    python ml/disease_detection/predict.py path/to/leaf.jpg --growth-stage grand_growth
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.ml import disease_model, image_features  # noqa: E402
from app.services import plant_service  # noqa: E402

GROWTH_STAGES = ["germination", "tillering", "grand_growth", "maturation", "ratoon_initiation"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", type=Path, help="path to a sugarcane leaf / stem photo")
    parser.add_argument("--growth-stage", choices=GROWTH_STAGES, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.image.exists():
        raise SystemExit(f"Image not found: {args.image}")

    image = image_features.load_image(args.image.read_bytes())
    result = plant_service.analyse(image, growth_stage=args.growth_stage)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    status = disease_model.status()
    print("=" * 70)
    print("SMART SUGARCANE AI - DISEASE ANALYSIS RESULT")
    print("=" * 70)
    if result["is_demo"]:
        print("*** DEMO MODE - colour and texture heuristic, NOT a trained model. ***")
        print("*** This is illustrative only and must not be used as a diagnosis.  ***")
    else:
        print(f"Model: trained Keras classifier ({status.get('model_path')})")
    print("-" * 70)
    print(f"Detected Condition : {result['condition_label']}")
    print(f"Confidence         : {result['confidence'] * 100:.1f} %")
    print(f"Severity           : {result['severity'].title()}")
    print(f"Health Score       : {result['health_score']:.0f} / 100")
    print(f"Image Quality      : {result['image_quality']['rating']} "
          f"({result['image_quality']['resolution']})")
    for issue in result["image_quality"]["issues"]:
        print(f"    ! {issue}")
    print("-" * 70)
    print(f"{result['short_description']}\n")

    print("Class probabilities:")
    for entry in result["probabilities"][:5]:
        bar = "#" * int(entry["probability"] * 40)
        print(f"  {entry['label']:<22} {entry['probability'] * 100:5.1f} % {bar}")

    print("-" * 70)
    print("SYMPTOMS")
    for item in result["symptoms"]:
        print(f"  - {item}")
    print("\nPOSSIBLE CAUSES")
    for item in result["causes"]:
        print(f"  - {item}")

    recovery = result["recovery"]
    print("\n" + "=" * 70)
    print("HOW TO IMPROVE THIS PLANT")
    print("=" * 70)
    print("IMMEDIATE ACTION")
    for item in recovery["immediate_action"]:
        print(f"  - {item}")
    print("\nRECOVERY PLAN")
    for item in recovery["recovery_plan"]:
        print(f"  - {item}")
    print(f"\nIRRIGATION: {recovery['irrigation_advice'].get('summary', '')}")
    for item in recovery["irrigation_advice"].get("details", []):
        print(f"  - {item}")
    print("\nSOIL AND NUTRIENT ADVICE")
    for item in recovery["soil_and_nutrient_advice"]:
        print(f"  - {item}")
    print("\nPREVENTION")
    for item in recovery["prevention_plan"]:
        print(f"  - {item}")
    print("\nMONITORING SCHEDULE")
    for item in recovery["monitoring_schedule"]:
        print(f"  - {item}")

    print("\n" + "-" * 70)
    for note in result["model_notes"]:
        print(f"NOTE: {note}")
    print("-" * 70)
    print(result["disclaimer"])
    print("=" * 70)


if __name__ == "__main__":
    main()
