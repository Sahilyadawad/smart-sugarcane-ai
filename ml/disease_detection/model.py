"""Model architecture for sugarcane disease classification.

Transfer learning on a lightweight ImageNet backbone. The preprocessing layer is
built INTO the model, so inference only has to hand it a raw 0-255 RGB array -
that removes the single most common cause of "works in training, wrong in
production" bugs.
"""

from __future__ import annotations

BACKBONES = ("mobilenetv2", "efficientnetb0", "resnet50")
DEFAULT_INPUT_SIZE = (224, 224)


def preprocessing_layer(backbone: str):
    """Return the rescaling layer that matches the backbone's expected input range."""
    import tensorflow as tf

    if backbone == "mobilenetv2":
        # MobileNetV2 expects [-1, 1]
        return tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1.0, name="preprocess")
    if backbone == "resnet50":
        # ResNet50 (caffe-style) expects roughly [0, 255] mean-subtracted; keeping
        # a plain 0-1 rescale is close enough for fine-tuning and much simpler.
        return tf.keras.layers.Rescaling(1.0 / 255.0, name="preprocess")
    # EfficientNet models normalise internally, so pass raw 0-255 through.
    return tf.keras.layers.Rescaling(1.0, name="preprocess")


def build_backbone(backbone: str, input_shape: tuple[int, int, int]):
    import tensorflow as tf

    common = {"include_top": False, "weights": "imagenet", "input_shape": input_shape}
    if backbone == "mobilenetv2":
        return tf.keras.applications.MobileNetV2(**common)
    if backbone == "efficientnetb0":
        return tf.keras.applications.EfficientNetB0(**common)
    if backbone == "resnet50":
        return tf.keras.applications.ResNet50(**common)
    raise ValueError(f"Unknown backbone '{backbone}'. Choose from: {', '.join(BACKBONES)}")


def build_augmentation():
    """Field photos vary wildly in angle and light, so augment accordingly."""
    import tensorflow as tf

    return tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal_and_vertical"),
            tf.keras.layers.RandomRotation(0.15),
            tf.keras.layers.RandomZoom(0.15),
            tf.keras.layers.RandomTranslation(0.08, 0.08),
            tf.keras.layers.RandomContrast(0.15),
            tf.keras.layers.RandomBrightness(0.15, value_range=(0, 255)),
        ],
        name="augmentation",
    )


def build_model(
    num_classes: int,
    input_size: tuple[int, int] = DEFAULT_INPUT_SIZE,
    backbone: str = "mobilenetv2",
    dropout: float = 0.3,
    augment: bool = True,
):
    """Assemble the full classifier with the backbone frozen for phase 1."""
    import tensorflow as tf

    input_shape = (*input_size, 3)
    base = build_backbone(backbone, input_shape)
    base.trainable = False

    inputs = tf.keras.Input(shape=input_shape, name="image")
    x = build_augmentation()(inputs) if augment else inputs
    x = preprocessing_layer(backbone)(x)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D(name="pool")(x)
    x = tf.keras.layers.Dropout(dropout, name="dropout")(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax", name="predictions")(x)

    model = tf.keras.Model(inputs, outputs, name=f"sugarcane_disease_{backbone}")
    return model, base


def compile_model(model, learning_rate: float = 1e-3) -> None:
    import tensorflow as tf

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )


def unfreeze_for_finetuning(base, model, unfreeze_from: float = 0.7, learning_rate: float = 1e-5) -> int:
    """Unfreeze the top fraction of the backbone and recompile at a low LR.

    Fine-tuning the whole backbone at a normal learning rate destroys the
    pretrained features, so only the top layers are unfrozen and the learning
    rate drops by two orders of magnitude.
    """
    base.trainable = True
    cutoff = int(len(base.layers) * unfreeze_from)
    for layer in base.layers[:cutoff]:
        layer.trainable = False
    # BatchNorm statistics must stay frozen during fine-tuning on small datasets.
    for layer in base.layers:
        if layer.__class__.__name__ == "BatchNormalization":
            layer.trainable = False

    compile_model(model, learning_rate)
    return len(base.layers) - cutoff
