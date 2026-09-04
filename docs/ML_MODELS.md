# ML Models

What is actually running, how accurate it really is, and how to replace it.

---

## Current status

| Module | Out of the box | Type | Where the artifact lives |
|---|---|---|---|
| Irrigation | Rule engine → **trained model** after one command | `RandomForestRegressor` + `RandomForestClassifier` | `models/irrigation_model.joblib` |
| Disease detection | ✅ **Trained model** | MobileNetV2 transfer learning, 86.3 % val accuracy | `models/sugarcane_disease_model.keras` |
| Soil analysis | ✅ **Trained model** | MobileNetV2, 89.6 % val accuracy | `models/sugarcane_soil_model.keras` |
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

### Current status: TRAINED

A MobileNetV2 classifier is trained and in use, on a 2,521-image labelled
sugarcane dataset (see [DATASET_GUIDE.md](DATASET_GUIDE.md)):

| | |
|---|---|
| Validation accuracy | **86.31 %** (loss 0.374) |
| Classes | healthy, mosaic, red_rot, rust, yellow_leaf |
| Epochs | 23 (15 frozen + 8 fine-tune) |
| Progression | 64 % → 82 % (phase 1) → 86 % (fine-tuning) |

Random guessing across five classes is 20 %, so the model has learned real
structure. Read the accuracy as accuracy **on a random split of this dataset** -
not field-validated diagnostic accuracy. A phone photo in harsh sun is a harder
problem than a curated dataset image, which is why the UI still shows the
confidence score, the image-quality assessment, and the reminder to confirm with
a qualified agricultural expert.

`smut` and `leaf_scald` had no images in the dataset, so the model cannot predict
them. Their guidance stays in the knowledge base for when images are available.

### The DEMO fallback (still present)

If the model file is missing, the app falls back to a transparent colour and
texture heuristic and labels every result `DEMO`, rather than failing.

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

### Current status: TRAINED — with an important caveat about the data

A MobileNetV2 classifier is trained and in use: **89.55 % validation accuracy**
over 4 classes (`alluvial`, `black`, `clay`, `red`).

**Read that number sceptically.** The source archive contained 1,563 files but
only **672 unique images** — 57 % were byte-identical duplicates. Worse, its
supplied train/test split was useless: **every single one of the 341 "test"
images also appeared in the training folder**, so evaluating on it would have
reported a meaningless near-perfect score. One image was filed under two
different labels and was dropped.

The model was therefore trained on the deduplicated set with a fresh split:

| Class | Unique images |
|---|---|
| alluvial | 281 |
| black | 122 |
| clay | 114 |
| red | 155 |

Two consequences worth stating plainly:

* **Small and imbalanced.** 114 images for clay is at the bottom of the usable
  range, and alluvial has 2.5x more examples than clay.
* **Web-sourced, not field-collected.** These are largely internet images, so
  the model may be keying partly on photographic style rather than on soil. It
  has not been tested against phone photos of a real field.

`sandy` and `loamy` had no images, so the model cannot predict them. They remain
selectable manually and in the knowledge base.

### The permanent limitation

None of this changes what the module can honestly tell a farmer. Even a perfect
model classifies soil **appearance**. It cannot measure NPK, pH, electrical
conductivity or micronutrients - that is physics, not a modelling gap - so the
app still shows "laboratory soil testing provides accurate nutrient and pH
values" on every result.

### The DEMO fallback (still present)

If the model file is missing, the app falls back to a weighted HSV + graininess
heuristic, labelled `DEMO visual estimate`.

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
