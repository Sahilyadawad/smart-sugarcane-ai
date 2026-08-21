"""Model architecture for soil image classification.

Soil classification is the same shape of problem as disease classification - a
small-image, few-class transfer-learning task - so the architecture helpers are
shared with ``ml/disease_detection/model.py`` rather than duplicated. Only the
defaults differ: soil uses a smaller input size and gentler augmentation,
because soil colour IS the signal and aggressive brightness or contrast jitter
destroys exactly the information the model needs.

The shared module is loaded by explicit file path under a distinct module name.
Both files are called ``model.py``, so a plain ``from model import ...`` would
resolve back to this file and fail half-initialised.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SHARED_PATH = Path(__file__).resolve().parents[1] / "disease_detection" / "model.py"


def _load_shared():
    if "sugarcane_shared_arch" in sys.modules:
        return sys.modules["sugarcane_shared_arch"]
    spec = importlib.util.spec_from_file_location("sugarcane_shared_arch", _SHARED_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Could not load shared architecture helpers from {_SHARED_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["sugarcane_shared_arch"] = module
    spec.loader.exec_module(module)
    return module


_shared = _load_shared()

BACKBONES = _shared.BACKBONES
build_backbone = _shared.build_backbone
compile_model = _shared.compile_model
preprocessing_layer = _shared.preprocessing_layer
unfreeze_for_finetuning = _shared.unfreeze_for_finetuning

DEFAULT_INPUT_SIZE = (192, 192)

__all__ = [
    "BACKBONES",
    "DEFAULT_INPUT_SIZE",
    "build_backbone",
    "build_model",
    "build_soil_augmentation",
    "compile_model",
    "preprocessing_layer",
    "unfreeze_for_finetuning",
]


def build_soil_augmentation():
    """Geometry-only augmentation.

    No brightness, contrast or hue jitter: a random brightness shift can turn a
    photo of loamy soil into something the model should call black soil, which
    teaches it precisely the wrong thing.
    """
    import tensorflow as tf

    return tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal_and_vertical"),
            tf.keras.layers.RandomRotation(0.25),
            tf.keras.layers.RandomZoom(0.15),
        ],
        name="soil_augmentation",
    )


def build_model(
    num_classes: int,
    input_size: tuple[int, int] = DEFAULT_INPUT_SIZE,
    backbone: str = "mobilenetv2",
    dropout: float = 0.25,
    augment: bool = True,
):
    import tensorflow as tf

    input_shape = (*input_size, 3)
    base = build_backbone(backbone, input_shape)
    base.trainable = False

    inputs = tf.keras.Input(shape=input_shape, name="image")
    x = build_soil_augmentation()(inputs) if augment else inputs
    x = preprocessing_layer(backbone)(x)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D(name="pool")(x)
    x = tf.keras.layers.Dropout(dropout, name="dropout")(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax", name="predictions")(x)

    return tf.keras.Model(inputs, outputs, name=f"sugarcane_soil_{backbone}"), base
