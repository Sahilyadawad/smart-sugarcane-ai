# Dataset Guide

How to get from DEMO mode to real trained models.

---

## The dataset this project was trained on

A labelled sugarcane leaf dataset supplied by the project author, extracted to
`~/datasets/sugarcane`:

| Class folder | Images |
|---|---|
| `healthy` | 522 |
| `mosaic` | 462 |
| `red_rot` | 518 |
| `rust` | 514 |
| `yellow_leaf` | 505 |
| **Total** | **2,521** |

All 2,521 files verified readable, JPEG, mostly around 1040 px on the long edge.
Folder names were renamed from the archive's `Healthy` / `Mosaic` / `RedRot` /
`Rust` / `Yellow` to the lowercase keys the application uses, so that predictions
line up with `data/disease_recommendations.json`.

**Two classes are absent**: `smut` and `leaf_scald`. The app keeps their guidance
in the knowledge base but the trained model will never predict them, because it
was never shown an example. Add folders for them and retrain if you obtain
images.

Retrain from this dataset with:

```bash
python ml/disease_detection/train.py --data-dir ~/datasets/sugarcane
```

> Record where your images came from before submitting. An examiner asking "what
> was this trained on?" deserves a specific answer, and dataset provenance is
> part of the work.

---

## What you need

| Model | Data required | Realistic minimum | Good |
|---|---|---|---|
| Disease detection | Labelled sugarcane photos, one folder per condition | 100 / class | 500+ / class |
| Soil analysis | Labelled bare-soil photos, one folder per soil type | 100 / class | 300+ / class |
| Irrigation | CSV of logged field decisions | 200 rows | 1000+ rows |

Below roughly 100 images per class the model memorises rather than learns, and —
worse — its confidence numbers become actively misleading. A model that is 60 %
accurate but reports 95 % confidence is more dangerous than the honest DEMO
heuristic it replaced.

---

## 1. Disease detection dataset

### Folder layout

```
sugarcane_dataset/
├── healthy/
│   ├── img_0001.jpg
│   └── ...
├── red_rot/
├── rust/
├── smut/
├── mosaic/
├── leaf_scald/
└── yellow_leaf/
```

Folder names become class names. **They must match the keys under `conditions`
in `data/disease_recommendations.json`**, otherwise the app cannot look up the
guidance for a predicted class.

Do **not** create an `unknown/` folder. `unknown` is produced at runtime when
confidence falls below the floor — it is not a trainable class.

You do not need all seven classes. Three well-populated classes beat seven
sparse ones. Delete the folders you cannot fill; `train.py` adapts, and rewrites
`class_names.json` from what it finds.

### Where to look for data

**Public repositories** — search these for "sugarcane disease":

- [Kaggle Datasets](https://www.kaggle.com/datasets) — several sugarcane leaf
  disease sets exist; check the licence and how the images were labelled
- [Mendeley Data](https://data.mendeley.com/) — research-grade agricultural
  image sets, usually with a linked paper describing collection method
- [Roboflow Universe](https://universe.roboflow.com/) — community CV datasets,
  exportable as folders
- [PlantVillage](https://plantvillage.psu.edu/) — huge, but sugarcane coverage
  is limited compared to tomato/potato

**Before you use any public dataset, check three things:**

1. **Licence** — can you use it for your project, and does it need attribution?
2. **How it was labelled** — by an agronomist, or by whoever scraped it? Wrong
   labels are worse than no data.
3. **Whether it looks like your field** — a dataset of clean lab photographs
   will not survive contact with a phone photo taken in Belagavi afternoon sun.

**Collecting your own** is slower but produces a far better model, because the
images match your camera, your varieties and your light. This is the single
highest-value thing you can do for this project.

### Collecting good field images

- **Fill the frame** with the affected leaf or stalk. No sky, hands, tools or
  distant rows.
- **Photograph in daylight**, avoiding harsh direct sun and deep shade. No flash.
- **Vary everything except the label**: time of day, angle, distance, phone,
  weather, plant age. If every red-rot photo is taken at 4 pm on one block, the
  model learns "4 pm lighting = red rot".
- **Photograph many different plants**, not one plant many times. Twenty
  locations × 20 photos beats one location × 400 photos.
- **Include the ambiguous cases.** Early-stage symptoms and mixed infections are
  exactly what a farmer will photograph.
- **Get the labels confirmed** by an agricultural officer or your factory cane
  department. For red rot, split the stalk and photograph the internal
  reddening — that is the diagnostic sign, not the leaf.
- **Include plenty of healthy images**, from the same fields and conditions. A
  model that has only seen diseased plants will find disease everywhere.

### Training

```bash
pip install -r ml/disease_detection/requirements.txt
```

```bash
python ml/disease_detection/train.py --data-dir path/to/sugarcane_dataset
```

CPU-only laptop? Start small to check the data is any good before committing:

```bash
python ml/disease_detection/train.py --data-dir path/to/sugarcane_dataset --epochs 12 --fine-tune-epochs 5 --batch-size 16
```

Roughly 2–5 minutes per epoch per 1000 images on CPU.

---

## 2. Soil dataset

```
soil_dataset/
├── black/
├── red/
├── sandy/
├── clay/
└── loamy/
```

Must match the keys under `profiles` in `data/soil_profiles.json`. No `mixed/`
folder — that is a runtime outcome.

### Soil datasets fail in one specific way

**The model learns the lighting, not the soil.** Guard against it deliberately:

- Photograph each soil type in **several different light conditions** — morning,
  midday shade, overcast. If every black-soil photo is a shadowed evening shot,
  the model learns "dark photo = black soil".
- Include **both dry and moist** samples of the same soil. Wet soil looks two
  shades darker; a model trained only on dry samples will misclassify every
  irrigated field.
- Photograph **freshly turned, levelled** soil from 30–40 cm, filling the frame.
- Cover **at least 10 different locations per class**.

This is why the soil augmentation in `ml/soil_analysis/model.py` is
geometry-only — flip, rotate, zoom, but never brightness or contrast jitter,
which would destroy exactly the signal the model needs.

```bash
python ml/soil_analysis/train.py --data-dir path/to/soil_dataset
```

---

## 3. Irrigation dataset

The most valuable dataset here, and the easiest to collect — you just have to
write things down.

For every irrigation decision, log:

| Column | Where it comes from |
|---|---|
| `soil_moisture` | Sensor, or the app's simulator, or a hand check scored 0–100 |
| `temperature`, `humidity`, `wind_speed` | Weather station or phone app |
| `rainfall` | Rain gauge, last 24 h |
| `rain_probability` | Forecast for the next 24 h |
| `weather_condition` | One of the seven enum values |
| `soil_type`, `growth_stage` | You know these |
| `water_requirement_mm` | **What you actually applied**, in mm |
| `irrigation_required` | `True` / `False` |

Converting applied water to mm:

```
mm = litres applied / (area in hectares x 10,000)
```

Or from pump time: `mm = flow rate (L/h) x hours / (area_ha x 10,000)`.

```bash
python ml/irrigation/train.py --data path/to/field_log.csv
```

One season of honest logging from one farm beats any synthetic dataset. The
bundle records `dataset_type: user_supplied` and the synthetic-data warnings
disappear from the app.

---

## 4. After training

Restart the backend, or reload without downtime:

```bash
curl -X POST http://localhost:8000/api/plants/reload-model -H "Authorization: Bearer $TOKEN"
```

Confirm the switch:

```bash
curl http://localhost:8000/api/system/status
```

`model_source` changes from `demo_heuristic` to `trained_model`, and the DEMO
badges disappear from the UI automatically. No code changes are needed.

---

## 5. Judging your model honestly

`train.py` prints validation accuracy on a random split of your dataset. **That
is not field accuracy.** A model scoring 97 % on clean dataset photos can
perform far worse on a phone photo in harsh sun.

Before trusting it:

- **Hold out a whole location or season**, not a random split. Random splits
  leak — near-duplicate photos of the same plant land in both sets and inflate
  the score.
- **Test on photos taken with a different phone**, in different light.
- **Check the confusion matrix**, not just accuracy. A model that never predicts
  `smut` can still score well if smut is rare.
- **Watch for the majority-class shortcut.** With 80 % healthy images, a model
  that always says "healthy" scores 80 %.
- **Show real predictions to an agricultural officer** and ask whether they
  agree.

If the honest answer is "it is not reliable yet", keep collecting data. The app
is fully functional in DEMO mode in the meantime, and a labelled demo is more
useful than an overconfident model.

---

## 6. Editing the knowledge base

Model accuracy is only half the picture — the advice attached to each prediction
comes from `data/`, and you can improve that today without any ML work:

| File | What to correct |
|---|---|
| `sugarcane_varieties.json` | Add varieties released for your district; update disease reactions, which shift over time |
| `disease_recommendations.json` | Align with your state's extension advisory |
| `fertilizer_rules.json` | Adjust stage windows and nutrient priorities to local practice |
| `soil_profiles.json` | Tune the heuristic thresholds and descriptions |

```bash
curl -X POST http://localhost:8000/api/recommendations/reload-knowledge
```

Keep the `data_disclaimer` fields honest as you edit — they are what tells a
farmer how much to trust the entry.
