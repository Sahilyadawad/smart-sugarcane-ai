# Irrigation Model

Predicts **how much water sugarcane needs and whether to irrigate now**, from soil
moisture, weather and crop growth stage.

## Current status

| Item | Value |
|---|---|
| Algorithm | `RandomForestRegressor` (water requirement, mm) + `RandomForestClassifier` (irrigate yes/no) |
| Training data | **Synthetic demonstration dataset** unless you supply your own |
| Fallback when no model file exists | Transparent water-balance rule engine — the API still works |
| Model artifact | `models/irrigation_model.joblib` (project root, so the backend can load it) |

> **Honesty note.** The bundled dataset is generated from the project's own
> water-balance model. A model trained on it learns that model very accurately —
> which makes the pipeline demonstrable — but it cannot know anything about your
> field that the water balance does not already encode. The R² you see after
> training measures agreement with the simulation, **not** real-world irrigation
> accuracy.

## Files

```
ml/irrigation/
├── generate_sample_dataset.py   Synthesise a labelled CSV
├── train.py                     Train + evaluate + save the joblib bundle
├── predict.py                   CLI prediction, same code path as the API
├── irrigation_dataset.csv       Created by generate_sample_dataset.py
└── README.md
```

The agronomy itself lives in `backend/app/ml/irrigation_engine.py`. Both training
and serving import it, so the two can never drift apart.

## Quick start

From the project root, with the backend virtual environment active:

```bash
python ml/irrigation/generate_sample_dataset.py --rows 12000
```

```bash
python ml/irrigation/train.py
```

```bash
python ml/irrigation/predict.py --soil-moisture 28 --temperature 36 --humidity 40
```

`train.py` generates the dataset automatically if it is missing, so you can skip
straight to it.

## Features used

| Feature | Unit | Notes |
|---|---|---|
| `soil_moisture` | % | Percent of available water remaining in the root zone |
| `temperature` | °C | Air temperature |
| `humidity` | % | Relative humidity |
| `rainfall` | mm | Last 24 hours |
| `rain_probability` | % | Next 24 hours |
| `wind_speed` | km/h | |
| `weather_condition` | category | clear, partly_cloudy, cloudy, rainy, stormy, humid, dry_wind |
| `soil_type` | category | black, red, sandy, clay, loamy, mixed |
| `growth_stage` | category | germination, tillering, grand_growth, maturation, ratoon_initiation |

Targets: `water_requirement_mm` (regression) and `irrigation_required` (classification).

## Training on your own field data

This is the step that turns the demo into something operationally useful.

1. Log, for each irrigation decision you actually made: the nine feature columns
   above, the water you applied in mm, and whether you irrigated.
2. Save as CSV with exactly those column names.
3. Train:

```bash
python ml/irrigation/train.py --data path/to/your_field_data.csv
```

The bundle records `dataset_type: user_supplied`, and the app stops showing the
synthetic-data warning.

A few hundred well-logged rows from your own field will outperform a hundred
thousand synthetic ones.

## How the app picks the model up

On startup the backend looks for `models/irrigation_model.joblib`. If it is
missing, unreadable, or was trained against a different feature order, the app
logs the reason and falls back to the rule engine — it never silently guesses.

To reload without restarting:

```bash
curl -X POST http://localhost:8000/api/irrigation/reload-model -H "Authorization: Bearer <token>"
```

Check what is in use at any time: `GET /api/irrigation/model-status`.

## Tuning the agronomy

Every coefficient — crop coefficients, moisture triggers, available water per
soil type, application efficiency — is collected at the top of
`backend/app/ml/irrigation_engine.py` and documented. Replace them with values
from your local agricultural university, regenerate the dataset, and retrain.
