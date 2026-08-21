"""Command-line soil image analysis.

Same code path as the API, so the output matches what the website shows -
including the DEMO label and the limitations notice.

Usage
-----
    python ml/soil_analysis/predict.py path/to/soil.jpg
    python ml/soil_analysis/predict.py path/to/soil.jpg --region Karnataka --water-availability low
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.ml import image_features  # noqa: E402
from app.schemas.common import ClimateType, PlantingSeason, WaterAvailability  # noqa: E402
from app.schemas.soil import SoilFarmContext  # noqa: E402
from app.services import soil_service  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", type=Path)
    parser.add_argument("--region", default=None)
    parser.add_argument("--district", default=None)
    parser.add_argument("--climate", choices=[c.value for c in ClimateType], default="unknown")
    parser.add_argument("--water-availability", choices=[w.value for w in WaterAvailability], default="medium")
    parser.add_argument("--planting-season", choices=[s.value for s in PlantingSeason], default="general")
    parser.add_argument("--no-irrigation", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.image.exists():
        raise SystemExit(f"Image not found: {args.image}")

    context = SoilFarmContext(
        region=args.region,
        district=args.district,
        climate=ClimateType(args.climate),
        irrigation_available=not args.no_irrigation,
        water_availability=WaterAvailability(args.water_availability),
        planting_season=PlantingSeason(args.planting_season),
    )

    image = image_features.load_image(args.image.read_bytes())
    result = soil_service.analyse(image, context)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    estimate = result["estimate"]
    print("=" * 72)
    print("SMART SUGARCANE AI - SOIL PHOTO ANALYSIS")
    print("=" * 72)
    print(f"*** {result['lab_test_notice']} ***")
    if result["is_demo"]:
        print("*** DEMO visual estimate - accuracy depends on lighting and image quality. ***")
    print("-" * 72)
    print(f"Possible Soil Category : {estimate['soil_label']}")
    print(f"Image Confidence       : {estimate['confidence'] * 100:.1f} %")
    print(f"Possible Soil Colour   : {estimate['colour_description']}")
    print(f"Texture Appearance     : {estimate['texture_appearance']}")
    print(f"Moisture Appearance    : {estimate['moisture_label']}")
    print(f"Organic Matter         : {estimate['organic_matter_label']}")
    print(f"Image Quality          : {estimate['image_quality']['rating']} "
          f"({estimate['image_quality']['resolution']})")
    print("-" * 72)
    print(estimate["visual_description"])
    print("\nGENERAL PROPERTIES")
    for item in estimate["general_properties"]:
        print(f"  - {item}")
    print(f"\nSUGARCANE SUITABILITY: {estimate['sugarcane_suitability']}")
    print(f"IRRIGATION: {estimate['irrigation_note']}")

    print("\n" + "=" * 72)
    print("RECOMMENDED SUGARCANE VARIETIES")
    print("=" * 72)
    for match in result["varieties"]["matches"]:
        print(f"\n{match['match_label']} - {match['name']} ({match['match_score']:.0f} %)")
        for reason in match["why_suitable"]:
            print(f"  + {reason}")
        for caution in match["cautions"][:2]:
            print(f"  ! {caution}")
    print(f"\n{result['varieties']['disclaimer']}")

    fert = result["fertilizer"]
    print("\n" + "=" * 72)
    print("FERTILIZER GUIDANCE")
    print("=" * 72)
    print(f"Stage: {fert['growth_stage_label']} ({fert['typical_window']})")
    for focus in fert["nutrient_focus"]:
        print(f"  {focus['nutrient']}: {focus['priority'].upper()} priority")
    print("\nSUGGESTED MANAGEMENT")
    for item in fert["suggested_management"]:
        print(f"  - {item}")
    print(f"\n{fert['disclaimer']}")

    print("\n" + "=" * 72)
    print("LIMITATIONS OF IMAGE-BASED SOIL ANALYSIS")
    print("=" * 72)
    for item in result["limitations"]:
        print(f"  - {item}")
    print("\nTIPS FOR A BETTER PHOTO")
    for item in result["improve_photo_tips"]:
        print(f"  - {item}")
    print("=" * 72)


if __name__ == "__main__":
    main()
