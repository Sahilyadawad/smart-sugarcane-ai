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
    "export_inference_model",
    "compile_model",
    "preprocessing_layer",
    "unfreeze_for_finetuning",
]


def _hue_preserving_jitter_class():
    """Defined lazily so importing this module never requires TensorFlow."""
    import keras
    import tensorflow as tf

    @keras.saving.register_keras_serializable(package="sugarcane_soil")
    class HuePreservingColourJitter(tf.keras.layers.Layer):
        """Scales value and saturation in HSV, leaving the hue channel alone."""

        def __init__(self, brightness=0.22, saturation=0.45, **kwargs):
            super().__init__(**kwargs)
            self.brightness = brightness
            self.saturation = saturation

        def call(self, inputs, training=None):
            if not training:
                return inputs
            import tensorflow as tf  # noqa: PLC0415

            x = tf.clip_by_value(inputs / 255.0, 0.0, 1.0)
            hsv = tf.image.rgb_to_hsv(x)
            shape = (tf.shape(hsv)[0], 1, 1)
            v_scale = tf.random.uniform(shape, 1.0 - self.brightness, 1.0 + self.brightness)
            s_scale = tf.random.uniform(shape, 1.0 - self.saturation, 1.0 + self.saturation)
            hue = hsv[..., 0]
            sat = tf.clip_by_value(hsv[..., 1] * s_scale, 0.0, 1.0)
            val = tf.clip_by_value(hsv[..., 2] * v_scale, 0.0, 1.0)
            return tf.image.hsv_to_rgb(tf.stack([hue, sat, val], axis=-1)) * 255.0

        def compute_output_shape(self, input_shape):
            return input_shape

        def get_config(self):
            config = super().get_config()
            config.update({"brightness": self.brightness, "saturation": self.saturation})
            return config

    return HuePreservingColourJitter


def build_soil_augmentation():
    """Geometry, plus exposure and saturation jitter that leaves HUE untouched.

    An earlier version was geometry-only, on the reasoning that "colour is the
    label". That was too blunt. In this taxonomy the label is carried by HUE:
    red soil sits near 4-23 deg, alluvial near 27-50 deg. Saturation and
    brightness are not label - they are the weather, the camera and the time of
    day. Trained on vivid red soil only, the model learned "red = saturated"
    instead of "red = low hue", and a bright, washed-out red field photo
    (hue 1 deg, saturation 0.42) was confidently classified as alluvial.

    So we jitter exposure and saturation to make those two dimensions
    uninformative, while hue - the one channel that actually carries the class -
    is never touched.
    """
    import tensorflow as tf

    return tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal_and_vertical"),
            tf.keras.layers.RandomRotation(0.25),
            tf.keras.layers.RandomZoom(0.15),
            _hue_preserving_jitter_class()(name="hue_preserving_jitter"),
        ],
        name="soil_augmentation",
    )


def export_inference_model(trained, num_classes, input_size, backbone):
    """Rebuild the trained model WITHOUT the augmentation layer.

    Augmentation is a no-op at inference, but leaving a custom layer in the
    saved file means every process that loads it - the FastAPI backend, the
    serverless function - must import that class or the load fails outright.
    Stripping it keeps the deployed artifact a plain graph with no custom
    objects, which is one less thing that can break in production.
    """
    export, _ = build_model(
        num_classes=num_classes, input_size=input_size, backbone=backbone, augment=False
    )
    by_name = {layer.name: layer for layer in trained.layers}
    copied = 0
    for layer in export.layers:
        source = by_name.get(layer.name)
        if source is not None and source.weights:
            layer.set_weights(source.get_weights())
            copied += 1
    return export, copied


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
