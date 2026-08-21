# Soil Image Analysis

Estimates a soil category, moisture appearance, texture appearance and apparent
organic matter from a photograph — then chains into variety and fertilizer
recommendations.

## What a photograph can and cannot tell you

**Can (as an appearance estimate):** colour, apparent texture, whether the
surface looks dry or wet, whether the soil looks high or low in organic matter,
and a likely soil category.

**Cannot, ever:**

- exact NPK values
- pH
- electrical conductivity / salinity
- micronutrient concentrations

The app labels every image-based soil result **"Visual AI estimate — laboratory
soil testing provides more accurate nutrient and pH values."** That stays true
after you train a real model, and the code keeps saying it.

## Current status: DEMO MODE

No trained soil model ships with this project. Until you train one, the app runs
a transparent HSV colour + graininess heuristic scored against the tunable
thresholds in `data/soil_profiles.json`, and labels the result
`DEMO visual estimate`.

Check live status:

```bash
curl http://localhost:8000/api/soil/model-status
```

## Classes

| Key | Label |
|---|---|
| `black` | Black Soil (Vertisol / Regur) |
| `red` | Red Soil |
| `sandy` | Sandy Soil |
| `clay` | Clay Soil |
| `loamy` | Loamy Soil |

`mixed` is produced at **runtime** when confidence is too low, or when the photo
looks like vegetation rather than bare soil. It is not a trainable class — do not
create a folder for it.

## Training a real model

```bash
pip install -r ml/disease_detection/requirements.txt
```

Arrange your dataset:

```
soil_dataset/
├── black/
├── red/
├── sandy/
├── clay/
└── loamy/
```

Then:

```bash
python ml/soil_analysis/train.py --data-dir path/to/soil_dataset
```

### Collecting soil images that actually work

Soil datasets fail in a specific, predictable way: the model learns the
*lighting* instead of the *soil*. Guard against it.

- Photograph each soil type in **several different light conditions** — morning,
  midday shade, overcast. If every black-soil photo is a shadowed evening shot,
  the model learns "dark photo = black soil".
- Include both **dry and moist** samples of the same soil. Wet soil looks two
  shades darker, and a model that has only seen dry samples will misclassify
  every irrigated field.
- Fill the frame with soil. No hands, tools, grass or sky.
- Photograph freshly turned soil, levelled flat, from about 30-40 cm.
- Aim for **200+ images per class** across at least 10 different locations per
  class. Ten locations photographed 20 times each beats one location
  photographed 200 times.

The augmentation in `model.py` is geometry-only for exactly this reason — see the
comment in `build_soil_augmentation()`.

## Files

```
ml/soil_analysis/
├── model.py          Architecture (shares helpers with disease_detection/model.py)
├── train.py          Two-phase transfer learning, saves model + metadata
├── predict.py        CLI analysis using the exact API code path
├── class_names.json  Class list, rewritten by train.py
└── README.md
```

## Outputs

`train.py` writes:

- `models/sugarcane_soil_model.keras`
- `models/soil_model_meta.json`
- `ml/soil_analysis/class_names.json`

Restart the backend or `POST /api/soil/reload-model` to pick it up.

## Tuning the demo heuristic

The HSV bands and graininess thresholds per soil class live under
`profiles.<class>.heuristic` in `data/soil_profiles.json`, and the scoring
functions are in `backend/app/ml/soil_model.py`. Both are editable without
touching the API.
