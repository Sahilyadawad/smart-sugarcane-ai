# Sugarcane Disease Detection

Image classification for sugarcane leaf and stalk conditions.

## Current status: DEMO MODE

**No trained model ships with this project.** No labelled sugarcane disease
dataset is bundled, so there is nothing honest to train on out of the box.

Until you train one, the app runs a transparent **colour and texture heuristic**
and labels every result `DEMO`. It measures green / yellow / brown / dark /
bleached coverage, edge density and streak orientation, then scores the classes
with hand-set weights. That is enough to demonstrate the full pipeline end to
end — upload, analyse, severity, recovery plan, history — and it responds to
what is actually in the photograph. It is **not** a validated diagnostic tool,
and neither the code nor the UI ever claims it is.

Check the live status any time:

```bash
curl http://localhost:8000/api/plants/model-status
```

## Classes

| Key | Label | Type |
|---|---|---|
| `healthy` | Healthy Sugarcane | — |
| `red_rot` | Red Rot | fungal |
| `rust` | Rust | fungal |
| `smut` | Smut | fungal |
| `mosaic` | Mosaic Disease | viral |
| `leaf_scald` | Leaf Scald | bacterial |
| `yellow_leaf` | Yellow Leaf Disease | viral |

`unknown` is produced at **runtime** when confidence falls below the floor in
`backend/app/ml/disease_model.py`. It is not a trainable class — do not create a
folder for it.

These keys must match the keys under `conditions` in
`data/disease_recommendations.json`, otherwise the app cannot find the guidance
for a predicted class.

## Training a real model

### 1. Install TensorFlow

```bash
pip install -r ml/disease_detection/requirements.txt
```

On Windows use `tensorflow-cpu` (already pinned in that file). It is a ~250 MB
download.

### 2. Arrange your dataset

```
dataset/
├── healthy/
├── red_rot/
├── rust/
├── smut/
├── mosaic/
├── leaf_scald/
└── yellow_leaf/
```

Folder names become class names. See `docs/DATASET_GUIDE.md` for where to look
for sugarcane imagery and how to collect your own.

Aim for **at least 200 images per class**, ideally 500+. Below ~100 per class
the model memorises rather than learns, and its confidence numbers become
actively misleading.

### 3. Train

```bash
python ml/disease_detection/train.py --data-dir path/to/dataset
```

Useful flags:

```bash
python ml/disease_detection/train.py --data-dir dataset --backbone mobilenetv2 --epochs 15 --fine-tune-epochs 8
```

| Flag | Default | Notes |
|---|---|---|
| `--backbone` | `mobilenetv2` | also `efficientnetb0`, `resnet50` |
| `--image-size` | `224` | |
| `--batch-size` | `32` | drop to 16 if you run out of memory |
| `--epochs` | `15` | phase 1, backbone frozen |
| `--fine-tune-epochs` | `8` | phase 2, top backbone layers unfrozen at a low LR |

Training runs in two phases: the classifier head first with the backbone frozen,
then the top 30 % of the backbone unfrozen at `1e-5`. BatchNorm layers stay
frozen throughout, which matters on small datasets.

**CPU-only laptop?** Expect roughly 2-5 minutes per epoch per 1000 images.
Start with `--epochs 12 --fine-tune-epochs 5` to see whether the data is any
good before committing to a long run.

### 4. Use it

`train.py` writes:

- `models/sugarcane_disease_model.keras` — the model the backend loads
- `models/disease_model_meta.json` — class names, input size, validation accuracy
- `ml/disease_detection/class_names.json` — updated from your folder names

Then restart the backend, or:

```bash
curl -X POST http://localhost:8000/api/plants/reload-model -H "Authorization: Bearer <token>"
```

The app switches from `demo_heuristic` to `trained_model`, and the DEMO banners
disappear from the UI automatically.

## Files

```
ml/disease_detection/
├── model.py            Architecture + augmentation + fine-tuning helper
├── train.py            Two-phase transfer learning, saves model + metadata
├── predict.py          CLI prediction using the exact API code path
├── class_names.json    Class list, rewritten by train.py
├── requirements.txt    TensorFlow, kept out of the backend requirements
└── README.md
```

## A note on reported accuracy

The validation accuracy `train.py` prints is accuracy on a random split of *your*
dataset. It is not field-validated diagnostic accuracy. A model that scores 97 %
on clean, well-lit dataset photos can perform far worse on a phone photo taken in
harsh afternoon sun. This is why the app always shows the confidence score, the
image-quality assessment, and the reminder to confirm with a qualified
agricultural expert.
