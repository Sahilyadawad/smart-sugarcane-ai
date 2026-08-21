# ML Models

What is actually running, how accurate it really is, and how to replace it.

---

## Current status

| Module | Out of the box | Type | Where the artifact lives |
|---|---|---|---|
| Irrigation | Rule engine → **trained model** after one command | `RandomForestRegressor` + `RandomForestClassifier` | `models/irrigation_model.joblib` |
| Disease detection | **DEMO heuristic** | Colour + texture scoring | `models/sugarcane_disease_model.keras` (absent) |
| Soil analysis | **DEMO heuristic** | HSV + graininess scoring | `models/sugarcane_soil_model.keras` (absent) |
| Assistant | **Rule-based** | Keyword intent matching | n/a |

```bash
curl http://localhost:8000/api/system/status
```

---

## 1. Irrigation model

### How the decision is made

The agronomy lives in `backend/app/ml/irrigation_engine.py` — a simplified,
transparent FAO-56 style water balance:

```
net requirement = soil moisture deficit
                + one day of crop water use (ET0 x Kc)
                - effective rainfall
```

Every coefficient is a **documented assumption**, collected at the top of that
file so you can replace them with local values:

| Constant | What it encodes |
|---|---|
| `CROP_COEFFICIENT` | Kc per growth stage (0.50 germination → 1.25 grand growth) |
| `STAGE_TRIGGER` | Soil moisture % at which irrigation triggers, per stage |
| `SOIL_TRIGGER_ADJUST` | Trigger shift per soil type (sandy +8, black −5) |
| `TOTAL_AVAILABLE_WATER_MM` | mm of available water in a full root zone, per soil |
| `ROOT_ZONE_FRACTION` | Root development fraction per stage |
| `WEATHER_ET_FACTOR` | Sky-condition multiplier on ET0 |
| `METHOD_EFFICIENCY` | Application efficiency (flood 0.55 → drip 0.90) |
| `METHOD_APPLICATION_RATE_MM_H` | mm delivered per hour, used for duration |
| `RAINFALL_EFFECTIVENESS` | 0.75 — fraction of measured rain reaching the root zone |

Reference ET is a readable temperature/humidity/wind formulation, not full
Penman-Monteith:

```python
ET0 = 0.35 * (T - 5)^0.9 * (1 - RH/100 * 0.60) * (1 + 0.02 * wind) * sky_factor
```

It behaves sensibly across the Indian range (roughly 2–8 mm/day). Swap in
Penman-Monteith once you have solar radiation data.

### What the ML model adds

`train.py` fits two models on the same nine features:

- **`RandomForestRegressor`** → net water requirement in mm
- **`RandomForestClassifier`** → whether irrigation is needed at all

At prediction time the regressor supplies the water requirement, and the rule
engine derives priority, duration, volume and the human explanation around it —
so the numbers stay internally consistent. The classifier's probability is
reported as `model_confidence`, and **if the classifier disagrees with the
water-balance threshold on a borderline case, the response says so** and lowers
the confidence rather than hiding the disagreement.

### About those metrics

```
R2   : 0.9624
MAE  : 1.354 mm
Accuracy : 96.42 %
```

**Read this carefully.** The model was trained on a synthetic dataset generated
*from the water-balance model itself*. So these numbers measure how faithfully
the forest reproduces that simulation — **not** how accurately it predicts real
irrigation outcomes in your field. An R² of 0.96 against a simulation is not
evidence of real-world accuracy, and the training script prints a warning
saying exactly that.

This is genuinely useful for demonstrating the pipeline end to end, and it gives
sensible answers because the underlying water balance is sound. It is not a
substitute for field data.

### Training on real data

```bash
python ml/irrigation/train.py --data path/to/your_field_data.csv
```

Required columns:

```
soil_moisture, temperature, humidity, rainfall, rain_probability, wind_speed,
weather_condition, soil_type, growth_stage,
water_requirement_mm, irrigation_required
```

A few hundred well-logged rows from your own field will outperform a hundred
thousand synthetic ones. The saved bundle records `dataset_type: user_supplied`
and the synthetic-data warning disappears from the UI.

### Safety: feature-order checking

The bundle stores the feature order it was trained with. If you change
`FEATURE_ORDER` in the engine and forget to retrain, the loader **refuses the
stale model**, logs why, and falls back to the rule engine. It never silently
scores against mismatched columns.

---

## 2. Disease detection

### Why it ships in DEMO mode

No labelled sugarcane disease dataset is bundled with this project. Shipping a
model trained on nothing, or on a handful of scraped images, and calling it a
disease detector would be dishonest. So the app runs a transparent heuristic and
labels every result `DEMO`.

### What the heuristic actually measures

`backend/app/ml/image_features.py` extracts real computer-vision measurements:

| Feature | Meaning |
|---|---|
| `green_ratio`, `yellow_ratio`, `brown_ratio`, `dark_ratio`, `bleached_ratio` | HSV colour-mask coverage |
| `tissue_ratio` | Fraction of the frame that is plant tissue |
| `brown_fragmentation` | Boundary-to-area ratio of the brown mask |
| `edge_density` | Fraction of pixels above a fixed gradient threshold |
| `green_hue_std` | Hue spread inside green tissue |
| `vertical_streak_score` | Whether marks form lengthwise streaks |
| `sharpness`, `brightness`, `contrast`, `graininess` | Image quality and texture |

`disease_model.py` scores each class from these. Two design points matter:

**Coverage is measured relative to visible tissue, not the whole frame.**
Otherwise background, sky and shadow dominate the ratios and every leaf
photographed against dark soil scores identically.

**Fragmentation separates rust from red rot.** Both produce reddish-brown
discoloration and similar coverage. What differs is structure: rust is many
small pustules (boundary/area ≈ 0.36), red rot is a few large lesions
(≈ 0.03). No colour feature can tell them apart; this one can.

Symptom coverage is amplified through a saturating function before scoring,
because 3 % of a leaf covered in rust is a real infection and must be able to
compete with a healthy leaf's ~100 % green.

### Honesty mechanisms

- Confidence is capped at **0.88** — the heuristic is never allowed to sound
  certain.
- Below a **0.42** confidence floor the answer becomes `unknown`, not a guess.
- Evidence spread is normalised against a minimum, so genuinely ambiguous images
  produce a flat distribution and therefore an honest `unknown`.
- If the image contains little plant tissue, it says so and returns `unknown`.
- Image quality is assessed and reported, and reduces confidence when poor.
- The measured colour percentages are returned in `model_notes`, so you can see
  exactly what drove the answer.

### Calibration

```bash
cd backend && venv\Scripts\python calibration_check.py
```

Renders synthetic images carrying each condition's textbook visual signature and
asserts the heuristic picks the right class (currently 12/12, disease and soil).

This is a **regression guard**, not a validation study. It catches the failure
where a change to the feature extractor makes everything classify as one class.
It says nothing about accuracy on real photographs.

### Training a real model

See [DATASET_GUIDE.md](DATASET_GUIDE.md) for data, then:

```bash
pip install -r ml/disease_detection/requirements.txt
```

```bash
python ml/disease_detection/train.py --data-dir path/to/dataset
```

Architecture (`ml/disease_detection/model.py`):

- MobileNetV2 / EfficientNetB0 / ResNet50 backbone, ImageNet weights
- Preprocessing built **into** the model, so inference feeds raw 0–255 RGB —
  this removes the most common "works in training, wrong in production" bug
- Augmentation: flip, rotate, zoom, translate, contrast, brightness
- **Phase 1**: classifier head only, backbone frozen, lr 1e-3
- **Phase 2**: top 30 % of the backbone unfrozen, lr 1e-5, BatchNorm kept frozen

Outputs `models/sugarcane_disease_model.keras` and
`models/disease_model_meta.json`. Restart the backend or call
`POST /api/plants/reload-model`; the DEMO badges disappear automatically.

---

## 3. Soil analysis

Same two-mode design. The demo scores five classes with a **weighted mean of
membership functions** over hue, saturation, brightness and graininess.

A weighted *mean* rather than a sum of bonuses matters: with a sum, a near-black
soil was scored as clay because "smooth" and "low saturation" both paid out
while the brightness criterion merely contributed nothing. A mean lets a failed
criterion drag the whole score down.

Thresholds live in `_CRITERIA` in `backend/app/ml/soil_model.py`, and the
descriptive text in `data/soil_profiles.json`. Both are editable.

### The permanent limitation

Even a perfectly trained soil model classifies **appearance**. It cannot measure
NPK, pH, electrical conductivity or micronutrients — and the app keeps saying so
after you train one, because that limitation is physical, not a software gap.

Note also that the same soil looks two shades darker when wet, which is why the
soil augmentation is **geometry-only** — no brightness or contrast jitter, since
that would teach the model that lighting is the label.

---

## 4. Assistant

Keyword intent matching over the user's saved analyses plus the JSON knowledge
base. Deliberately not an LLM: no API key, no cost, no hallucination, and it
cites which of your records it used.

Adding a language: extend `INTENTS` with local-language keywords, translate the
handlers in `HANDLERS`, and add the code to `SUPPORTED_LANGUAGES` in
`backend/app/services/assistant_service.py`. Until a language is listed there,
the assistant answers in English and says so rather than pretending.

---

## 5. Model mode

`MODEL_MODE` in `backend/.env`:

| Value | Behaviour |
|---|---|
| `auto` (default) | Use trained models if present, otherwise fall back |
| `demo` | Force the heuristics even if model files exist — useful for comparison |
| `production` | Load trained models only |

Loading is lazy and failure-tolerant throughout. A missing, corrupt or
incompatible model file logs the reason and degrades to the documented fallback.
The app never pretends a model is loaded when it is not.
