"""Train the soil image classifier.

Expects one subfolder per soil class:

    soil_dataset/
    ├── black/
    ├── red/
    ├── sandy/
    ├── clay/
    └── loamy/

Folder names become class names and must match the keys under ``profiles`` in
``data/soil_profiles.json``.

Usage
-----
    python ml/soil_analysis/train.py --data-dir path/to/soil_dataset

Requirements
------------
    pip install -r ml/disease_detection/requirements.txt

Important: even a well-trained model here classifies soil APPEARANCE. It cannot
measure NPK, pH, electrical conductivity or micronutrients, and the app will
keep saying so after you train it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

DEFAULT_OUTPUT = PROJECT_ROOT / "models" / "sugarcane_soil_model.keras"
DEFAULT_META = PROJECT_ROOT / "models" / "soil_model_meta.json"
CLASS_NAMES_FILE = SCRIPT_DIR / "class_names.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backbone", default="mobilenetv2", choices=["mobilenetv2", "efficientnetb0", "resnet50"])
    parser.add_argument("--image-size", type=int, default=192)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--fine-tune-epochs", type=int, default=8)
    parser.add_argument("--validation-split", type=float, default=0.2)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--fine-tune-lr", type=float, default=1e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-augment", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit(
            "TensorFlow is not installed.\n  pip install -r ml/disease_detection/requirements.txt"
        ) from exc

    from model import build_model, compile_model, unfreeze_for_finetuning  # noqa: PLC0415

    if not args.data_dir.exists():
        raise SystemExit(
            f"Dataset directory not found: {args.data_dir}\nSee docs/DATASET_GUIDE.md."
        )

    image_size = (args.image_size, args.image_size)
    print(f"TensorFlow {tf.__version__}")

    train_ds = tf.keras.utils.image_dataset_from_directory(
        args.data_dir,
        validation_split=args.validation_split,
        subset="training",
        seed=args.seed,
        image_size=image_size,
        batch_size=args.batch_size,
        label_mode="int",
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        args.data_dir,
        validation_split=args.validation_split,
        subset="validation",
        seed=args.seed,
        image_size=image_size,
        batch_size=args.batch_size,
        label_mode="int",
    )

    class_names = list(train_ds.class_names)
    print(f"\nClasses ({len(class_names)}): {', '.join(class_names)}")
    if len(class_names) < 2:
        raise SystemExit("At least two class subfolders are required.")

    counts = {name: len(list((args.data_dir / name).glob("*"))) for name in class_names}
    for name, count in counts.items():
        print(f"  {name:<10} {count}")
    if min(counts.values()) < 50:
        print(
            "\nWARNING: fewer than 50 images in the smallest class. Soil colour varies enormously "
            "with lighting and moisture, so small soil datasets overfit very quickly."
        )

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000, seed=args.seed).prefetch(autotune)
    val_ds = val_ds.cache().prefetch(autotune)

    model, base = build_model(
        num_classes=len(class_names),
        input_size=image_size,
        backbone=args.backbone,
        augment=not args.no_augment,
    )
    compile_model(model, args.learning_rate)
    model.summary()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(str(args.output), monitor="val_accuracy", save_best_only=True, verbose=1),
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=6, restore_best_weights=True, verbose=1),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, verbose=1),
    ]

    print("\nPHASE 1 - classifier head (backbone frozen)")
    history = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks)

    if args.fine_tune_epochs > 0:
        unfrozen = unfreeze_for_finetuning(base, model, learning_rate=args.fine_tune_lr)
        print(f"\nPHASE 2 - fine-tuning the top {unfrozen} backbone layers")
        fine_history = model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=args.epochs + args.fine_tune_epochs,
            initial_epoch=len(history.history["loss"]),
            callbacks=callbacks,
        )
        for key, values in fine_history.history.items():
            history.history.setdefault(key, []).extend(values)

    loss, accuracy = model.evaluate(val_ds, verbose=0)
    print(f"\nFinal validation accuracy: {accuracy * 100:.2f} %   (loss {loss:.4f})")

    model.save(args.output)

    meta = {
        "class_names": class_names,
        "input_size": list(image_size),
        "backbone": args.backbone,
        "preprocessing": "rescale_in_model",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "val_accuracy": round(float(accuracy), 4),
        "val_loss": round(float(loss), 4),
        "epochs_run": len(history.history["loss"]),
        "images_per_class": counts,
        "dataset_path": str(args.data_dir),
        "tensorflow_version": tf.__version__,
        "honesty_note": (
            "This model classifies soil APPEARANCE from a photograph. It cannot determine NPK, pH, "
            "electrical conductivity or micronutrient concentrations. Laboratory soil testing "
            "provides accurate nutrient and pH values."
        ),
    }
    DEFAULT_META.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    CLASS_NAMES_FILE.write_text(
        json.dumps({"class_names": class_names, "updated_at": meta["trained_at"]}, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved model    : {args.output}")
    print(f"Saved metadata : {DEFAULT_META}")
    print("\nRestart the backend (or POST /api/soil/reload-model) to use it.")


if __name__ == "__main__":
    main()
