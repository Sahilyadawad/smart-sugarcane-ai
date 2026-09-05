"""Re-save a trained soil model without its augmentation layer.

A saved model that contains a custom Keras layer can only be loaded by a process
that imports that class. The FastAPI backend does not import the training code,
so such a file fails to load and the app silently falls back to demo mode.
Augmentation does nothing at inference, so the deployed artifact should not
contain it at all. train.py now does this automatically; this script repairs a
model produced before that change.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = REPO / "models" / "sugarcane_soil_model.keras"
DEFAULT_META = REPO / "models" / "soil_model_meta.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--meta", type=Path, default=DEFAULT_META)
    args = parser.parse_args()

    import tensorflow as tf

    spec = importlib.util.spec_from_file_location("soil_arch", Path(__file__).with_name("model.py"))
    arch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(arch)

    jitter = arch._hue_preserving_jitter_class()
    trained = tf.keras.models.load_model(
        args.model, custom_objects={"HuePreservingColourJitter": jitter}, compile=False
    )
    print(f"Loaded {args.model.name}")

    has_aug = any(layer.name == "soil_augmentation" for layer in trained.layers)
    if not has_aug:
        print("No augmentation layer present - nothing to strip.")
        return

    meta = json.loads(args.meta.read_text(encoding="utf-8")) if args.meta.exists() else {}
    class_names = meta.get("class_names") or []
    size = tuple(meta.get("input_size") or [192, 192])
    backbone = meta.get("backbone", "mobilenetv2")

    export, copied = arch.export_inference_model(
        trained, num_classes=len(class_names) or trained.output_shape[-1],
        input_size=(int(size[0]), int(size[1])), backbone=backbone,
    )
    print(f"Rebuilt without augmentation, copied {copied} weighted layers")

    # The stripped model must agree with the original on real input.
    import numpy as np

    probe = np.random.default_rng(0).uniform(0, 255, size=(4, int(size[0]), int(size[1]), 3)).astype("float32")
    before = trained.predict(probe, verbose=0)
    after = export.predict(probe, verbose=0)
    drift = float(np.abs(before - after).max())
    print(f"Max probability drift vs original: {drift:.2e}")
    if drift > 1e-4:
        raise SystemExit(f"Refusing to save: outputs differ by {drift:.2e}, weight transfer is wrong.")

    export.save(args.model)
    print(f"Saved augmentation-free model to {args.model}")

    reloaded = tf.keras.models.load_model(args.model)  # no custom_objects - must just work
    check = reloaded.predict(probe, verbose=0)
    print(f"Reload without custom_objects: OK (drift {float(np.abs(check - after).max()):.2e})")


if __name__ == "__main__":
    main()
