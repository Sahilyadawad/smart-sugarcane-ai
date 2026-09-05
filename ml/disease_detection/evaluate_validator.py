"""Evaluate the sugarcane image validator on images it never saw during training.

Reports maize separately. Maize is the case that matters: if the model has
learned "long green blade leaf = sugarcane" rather than something specific to
sugarcane, maize is where that shows up, and a single overall accuracy figure
would hide it behind the easy negatives.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

REPO = Path(__file__).resolve().parents[2]
EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def load(path: Path, size: int) -> np.ndarray:
    raw = tf.io.read_file(str(path))
    img = tf.io.decode_image(raw, channels=3, expand_animations=False)
    return tf.cast(tf.image.resize(img, (size, size), antialias=True), tf.float32).numpy()


def predict_dir(model, files, size, batch=48):
    out = []
    for i in range(0, len(files), batch):
        chunk = np.stack([load(f, size) for f in files[i : i + batch]])
        out.append(model.predict(chunk, verbose=0))
    return np.concatenate(out) if out else np.zeros((0, 2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", type=Path, default=REPO / "models" / "sugarcane_validator_model.keras")
    ap.add_argument("--meta", type=Path, default=REPO / "models" / "validator_model_meta.json")
    ap.add_argument("--holdout", type=Path, default=Path(r"C:\Users\Hp\datasets\sugarcane_validator\holdout"))
    ap.add_argument("--limit", type=int, default=0, help="cap images per class (0 = all)")
    args = ap.parse_args()

    meta = json.loads(args.meta.read_text(encoding="utf-8"))
    names = meta["class_names"]
    size = int(meta["input_size"][0])
    pos_index = names.index("sugarcane")
    model = tf.keras.models.load_model(args.model)

    print(f"HELD-OUT SET - never seen during training\n")
    totals = {}
    for label in names:
        files = sorted(f for f in (args.holdout / label).iterdir() if f.suffix.lower() in EXT)
        if args.limit:
            files = files[: args.limit]
        probs = predict_dir(model, files, size)
        called_sugarcane = probs[:, pos_index] >= 0.5
        correct = called_sugarcane if label == "sugarcane" else ~called_sugarcane
        totals[label] = (int(correct.sum()), len(files))
        print(f"  {label:<16}{correct.mean() * 100:6.1f} % correct   ({correct.sum()}/{len(files)})")

    got = sum(v[0] for v in totals.values())
    n = sum(v[1] for v in totals.values())
    print(f"\n  overall         {got / n * 100:6.1f} %   ({got}/{n})")

    # The decisive test: maize, held out from the source dataset directly.
    corn = Path(r"C:\Users\Hp\datasets\corn")
    files = [f for f in corn.rglob("*") if f.suffix.lower() in EXT]
    trained_names = {f.name for f in (args.holdout / "not_sugarcane").iterdir()}
    import hashlib

    unseen = []
    for f in files:
        try:
            if f"{hashlib.sha256(f.read_bytes()).hexdigest()[:16]}{f.suffix.lower()}" not in trained_names:
                unseen.append(f)
        except Exception:
            pass
        if len(unseen) >= 400:
            break
    if unseen:
        probs = predict_dir(model, unseen, size)
        wrong = (probs[:, pos_index] >= 0.5)
        print(f"\nMAIZE - the hard case ({len(unseen)} images)")
        print(f"  correctly rejected: {(~wrong).mean() * 100:.1f} %")
        if wrong.any():
            print(f"  called sugarcane:   {wrong.sum()} images")


if __name__ == "__main__":
    main()
