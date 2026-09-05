"""Evaluate the soil model on images it has never seen.

This exists because an earlier "16/16 correct" spot check was run on images
drawn from the training set, which proves nothing about generalisation. This
script only ever reads the holdout directory, which train.py never
touches, and optionally any loose real-world photos passed on the command line.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

REPO = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = REPO / "models" / "sugarcane_soil_model.keras"
DEFAULT_META = REPO / "models" / "soil_model_meta.json"
# Resolved relative to the project so this runs on any machine, whether the
# datasets sit inside the project folder or beside it.
def _default_holdout() -> Path:
    for candidate in (
        REPO / "datasets" / "soil" / "holdout",
        REPO.parent / "datasets" / "soil" / "holdout",
    ):
        if candidate.exists():
            return candidate
    return REPO / "datasets" / "soil" / "holdout"


DEFAULT_HOLDOUT = _default_holdout()
SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}


def load_image(path: Path, size: int) -> np.ndarray:
    """Resize exactly the way the backend does, so this measures what ships.

    An earlier version used tf.image.resize with its default aliased bilinear
    filter, matching how image_dataset_from_directory prepared the training
    data. That understated the model by four points - 89.0 % here against
    93.0 % in the application - because the backend resizes with Pillow's
    antialiased BILINEAR, which does not sharpen the grain on a large field
    photograph. An evaluation that does not use the serving path is measuring
    a model nobody runs.
    """
    from PIL import Image  # noqa: PLC0415

    image = Image.open(path).convert("RGB").resize((size, size), Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--meta", type=Path, default=DEFAULT_META)
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("extra", nargs="*", type=Path, help="loose real-world photos to inspect")
    args = parser.parse_args()

    meta = json.loads(args.meta.read_text(encoding="utf-8"))
    class_names = meta["class_names"]
    size = int(meta["input_size"][0])
    model = tf.keras.models.load_model(args.model)

    if args.holdout.exists():
        paths, truths = [], []
        for class_dir in sorted(d for d in args.holdout.iterdir() if d.is_dir()):
            label = class_names.index(class_dir.name)
            for f in sorted(class_dir.iterdir()):
                if f.suffix.lower() in SUFFIXES:
                    paths.append(f)
                    truths.append(label)

        batch = np.stack([load_image(p, size) for p in paths])
        probs = model.predict(batch, verbose=0)
        preds = np.argmax(probs, axis=1)

        n = len(class_names)
        matrix = [[0] * n for _ in range(n)]
        for actual, predicted in zip(truths, preds):
            matrix[actual][predicted] += 1

        correct = sum(matrix[i][i] for i in range(n))
        print(f"HELD-OUT SET ({len(paths)} images the model has never seen)")
        print(f"Overall accuracy: {correct / len(paths) * 100:.1f} %")
        print()
        print(" " * 12 + "".join(f"{c[:8]:>10}" for c in class_names))
        for i, name in enumerate(class_names):
            row = matrix[i]
            recall = row[i] / max(sum(row), 1) * 100
            print(f"  {name:<10}" + "".join(f"{v:>10}" for v in row) + f"    recall {recall:5.1f} %")

        print()
        print("Per-class precision (of everything called X, how much really was X):")
        for i, name in enumerate(class_names):
            called = sum(matrix[r][i] for r in range(n))
            precision = matrix[i][i] / called * 100 if called else 0.0
            print(f"  {name:<10} predicted {called:>3} times, {precision:5.1f} % correct")

        wrong = [
            (paths[k], class_names[truths[k]], class_names[preds[k]], float(probs[k].max()))
            for k in range(len(paths))
            if preds[k] != truths[k]
        ]
        if wrong:
            print()
            print(f"Misclassified ({len(wrong)}):")
            for path, actual, predicted, conf in wrong[:25]:
                print(f"  {path.name:<44} {actual:>8} -> {predicted:<8} @ {conf * 100:.0f} %")
    else:
        print(f"No holdout directory at {args.holdout}")

    photos = [p for p in args.extra if p.is_file()]
    for extra in args.extra:
        if extra.is_dir():
            photos.extend(sorted(f for f in extra.iterdir() if f.suffix.lower() in SUFFIXES))
    if photos:
        print()
        print("REAL-WORLD PHOTOS")
        batch = np.stack([load_image(p, size) for p in photos])
        probs = model.predict(batch, verbose=0)
        for path, row in zip(photos, probs):
            order = np.argsort(row)[::-1]
            spread = "  ".join(f"{class_names[i]} {row[i] * 100:.1f}%" for i in order)
            print(f"  {path.name:<44} {spread}")


if __name__ == "__main__":
    main()
