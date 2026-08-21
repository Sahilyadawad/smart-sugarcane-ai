"""Generate a SYNTHETIC demonstration dataset for the irrigation model.

Why synthetic
-------------
No public, labelled sugarcane irrigation dataset ships with this project, and
the project brief calls for simulated soil-moisture data. Rather than pretend
otherwise, this script generates rows from the documented water-balance model in
``backend/app/ml/irrigation_engine.py``, adds measurement-style noise, and marks
the output clearly as synthetic.

What that means for accuracy
----------------------------
A model trained on this data learns the water-balance relationship - which is
genuinely useful for demonstrating the pipeline and gives sensible answers - but
it CANNOT capture anything the water-balance model does not already know about
your field. Replace this with real logged field data (soil moisture readings,
weather records and the irrigation actually applied) before using the model
operationally. The CSV column layout is the contract: match it and train.py
will work unchanged.

Usage
-----
    python ml/irrigation/generate_sample_dataset.py
    python ml/irrigation/generate_sample_dataset.py --rows 20000 --seed 7
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Make the backend package importable so training and serving share one engine.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.ml import irrigation_engine as engine  # noqa: E402

DEFAULT_ROWS = 12_000
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "irrigation_dataset.csv"

COLUMNS = [
    *engine.FEATURE_ORDER,
    "irrigation_method",
    "reference_et_mm",
    "crop_water_use_mm",
    "deficit_mm",
    "effective_rain_mm",
    "water_requirement_mm",
    "irrigation_required",
    "priority",
]


def _sample_weather(rng: np.random.Generator, n: int) -> dict[str, np.ndarray]:
    """Draw a weather profile that resembles an Indian sugarcane belt year."""
    # Season index drives a coherent temperature / humidity / rain relationship
    # instead of sampling every variable independently, which would produce
    # physically impossible rows such as 45 C with 95 % humidity and heavy rain.
    season = rng.integers(0, 3, size=n)  # 0 = dry hot, 1 = monsoon, 2 = mild

    temperature = np.where(
        season == 0,
        rng.normal(36.0, 4.0, n),
        np.where(season == 1, rng.normal(28.0, 3.0, n), rng.normal(30.0, 4.5, n)),
    )
    humidity = np.where(
        season == 0,
        rng.normal(35.0, 12.0, n),
        np.where(season == 1, rng.normal(82.0, 8.0, n), rng.normal(58.0, 14.0, n)),
    )
    rainfall = np.where(
        season == 1,
        rng.gamma(shape=1.6, scale=9.0, size=n),
        np.where(rng.random(n) < 0.12, rng.gamma(shape=1.1, scale=4.0, size=n), 0.0),
    )
    rain_probability = np.clip(
        np.where(season == 1, rng.normal(70, 20, n), rng.normal(18, 18, n)) + rainfall * 1.2,
        0,
        100,
    )
    wind_speed = np.clip(rng.gamma(shape=2.2, scale=4.0, size=n), 0, 45)

    condition = np.empty(n, dtype=object)
    for i in range(n):
        if rainfall[i] > 12:
            condition[i] = "stormy" if wind_speed[i] > 25 else "rainy"
        elif rainfall[i] > 0.5:
            condition[i] = "rainy"
        elif humidity[i] > 78:
            condition[i] = "humid"
        elif humidity[i] < 40 and wind_speed[i] > 18:
            condition[i] = "dry_wind"
        elif season[i] == 1:
            condition[i] = "cloudy"
        else:
            condition[i] = rng.choice(["clear", "partly_cloudy"], p=[0.65, 0.35])

    return {
        "temperature": np.clip(temperature, 12, 48),
        "humidity": np.clip(humidity, 12, 99),
        "rainfall": np.round(np.clip(rainfall, 0, 180), 2),
        "rain_probability": np.round(rain_probability, 0),
        "wind_speed": np.round(wind_speed, 1),
        "weather_condition": condition,
    }


def generate(rows: int = DEFAULT_ROWS, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    weather = _sample_weather(rng, rows)
    soil_moisture = np.clip(rng.beta(2.4, 2.0, rows) * 100, 3, 99)
    soil_type = rng.choice(list(engine.SOIL_TYPES), size=rows)
    growth_stage = rng.choice(
        list(engine.GROWTH_STAGES),
        size=rows,
        p=[0.15, 0.28, 0.32, 0.15, 0.10],  # grand growth and tillering dominate a real season
    )
    irrigation_method = rng.choice(list(engine.IRRIGATION_METHODS), size=rows, p=[0.30, 0.42, 0.13, 0.15])

    records = []
    for i in range(rows):
        inputs = {
            "soil_moisture": float(soil_moisture[i]),
            "temperature": float(weather["temperature"][i]),
            "humidity": float(weather["humidity"][i]),
            "rainfall": float(weather["rainfall"][i]),
            "rain_probability": float(weather["rain_probability"][i]),
            "wind_speed": float(weather["wind_speed"][i]),
            "weather_condition": str(weather["weather_condition"][i]),
            "soil_type": str(soil_type[i]),
            "growth_stage": str(growth_stage[i]),
        }
        decision = engine.decide(**inputs, irrigation_method=str(irrigation_method[i]))
        balance = decision.balance

        # Measurement-style noise so the model does not simply memorise a formula.
        noisy_requirement = float(
            max(0.0, decision.water_requirement_mm + rng.normal(0.0, 1.4))
        )

        records.append(
            {
                **inputs,
                "irrigation_method": str(irrigation_method[i]),
                "reference_et_mm": balance.reference_et_mm,
                "crop_water_use_mm": balance.crop_water_use_mm,
                "deficit_mm": balance.deficit_mm,
                "effective_rain_mm": balance.effective_rain_mm,
                "water_requirement_mm": round(noisy_requirement, 3),
                "irrigation_required": bool(decision.irrigation_required),
                "priority": decision.priority,
            }
        )

    return pd.DataFrame.from_records(records, columns=COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help=f"rows to generate (default {DEFAULT_ROWS})")
    parser.add_argument("--seed", type=int, default=42, help="random seed for reproducibility")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output CSV path")
    args = parser.parse_args()

    print(f"Generating {args.rows:,} synthetic rows (seed={args.seed})...")
    frame = generate(args.rows, args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)

    required = int(frame["irrigation_required"].sum())
    print(f"\nSaved: {args.output}")
    print(f"Rows: {len(frame):,}")
    print(f"Irrigation required: {required:,} ({required / len(frame) * 100:.1f} %)")
    print("\nWater requirement (mm) summary:")
    print(frame["water_requirement_mm"].describe().round(2).to_string())
    print("\nPriority distribution:")
    print(frame["priority"].value_counts().to_string())
    print("\nNOTE: this dataset is SYNTHETIC. It demonstrates the pipeline; it does not")
    print("      represent measured field outcomes. Replace it with logged field data")
    print("      before using the trained model for real irrigation decisions.")


if __name__ == "__main__":
    main()
