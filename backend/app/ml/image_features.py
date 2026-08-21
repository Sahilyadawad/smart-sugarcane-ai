"""Shared image feature extraction for the plant and soil demo analysers.

These are ordinary, inspectable computer-vision measurements - colour ratios,
HSV statistics, sharpness and local texture variance. They are NOT a trained
neural network, and every result that uses them is labelled as a demo estimate.

OpenCV is used when it is installed (faster, better Laplacian) but every
function has a pure NumPy fallback, so the backend runs without it.
"""

from __future__ import annotations

import io
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageOps

try:  # pragma: no cover - optional dependency
    import cv2

    HAS_CV2 = True
except Exception:  # noqa: BLE001
    cv2 = None  # type: ignore[assignment]
    HAS_CV2 = False

ANALYSIS_SIZE = 384


# ---------------------------------------------------------------- loading
def load_image(data: bytes) -> Image.Image:
    """Decode uploaded bytes into an RGB PIL image with EXIF rotation applied."""
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def to_array(image: Image.Image, size: int = ANALYSIS_SIZE) -> np.ndarray:
    """Resize (preserving aspect) and return a float array in the range 0-1."""
    working = image.copy()
    working.thumbnail((size, size), Image.Resampling.LANCZOS)
    return np.asarray(working, dtype=np.float32) / 255.0


# ------------------------------------------------------------ colour space
def rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """Vectorised RGB -> HSV. Hue in degrees 0-360, S and V in 0-1."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = np.max(rgb, axis=-1)
    minc = np.min(rgb, axis=-1)
    delta = maxc - minc

    hue = np.zeros_like(maxc)
    mask = delta > 1e-6

    r_is_max = mask & (maxc == r)
    g_is_max = mask & (maxc == g) & ~r_is_max
    b_is_max = mask & (maxc == b) & ~r_is_max & ~g_is_max

    safe_delta = np.where(mask, delta, 1.0)
    hue[r_is_max] = (((g - b) / safe_delta) % 6.0)[r_is_max]
    hue[g_is_max] = (((b - r) / safe_delta) + 2.0)[g_is_max]
    hue[b_is_max] = (((r - g) / safe_delta) + 4.0)[b_is_max]
    hue = hue * 60.0

    saturation = np.where(maxc > 1e-6, delta / np.where(maxc > 1e-6, maxc, 1.0), 0.0)
    return np.stack([hue, saturation, maxc], axis=-1)


# ------------------------------------------------------------- statistics
def laplacian_variance(rgb: np.ndarray) -> float:
    """Blur metric. Low values mean a soft or out-of-focus photograph."""
    grey = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)
    if HAS_CV2:
        return float(cv2.Laplacian(grey, cv2.CV_32F).var()) * 10000.0
    # 4-neighbour Laplacian kernel applied with slicing.
    lap = (
        -4.0 * grey[1:-1, 1:-1]
        + grey[:-2, 1:-1]
        + grey[2:, 1:-1]
        + grey[1:-1, :-2]
        + grey[1:-1, 2:]
    )
    return float(lap.var()) * 10000.0


def local_variance(rgb: np.ndarray, window: int = 7) -> float:
    """Graininess metric - high for sandy soil, low for smooth clay."""
    grey = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)
    if HAS_CV2:
        mean = cv2.blur(grey, (window, window))
        mean_sq = cv2.blur(grey * grey, (window, window))
        return float(np.mean(np.maximum(mean_sq - mean * mean, 0.0))) * 1000.0
    h, w = grey.shape
    trim_h, trim_w = h - h % window, w - w % window
    blocks = grey[:trim_h, :trim_w].reshape(trim_h // window, window, trim_w // window, window)
    return float(blocks.var(axis=(1, 3)).mean()) * 1000.0


#: Absolute gradient magnitude that counts as an edge. A fixed threshold is
#: essential here: an earlier percentile-based version returned ~0.10 for every
#: image by construction, which made the feature useless for telling a speckled
#: leaf from a smooth one.
EDGE_THRESHOLD = 0.055


def edge_density(rgb: np.ndarray) -> float:
    """Fraction of pixels sitting on a strong edge - proxy for speckling."""
    grey = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)
    gy, gx = np.gradient(grey)
    magnitude = np.hypot(gx, gy)
    return float((magnitude > EDGE_THRESHOLD).mean())


def mask_fragmentation(mask: np.ndarray) -> float:
    """Boundary-to-area ratio of a mask - how broken-up the marked region is.

    Many small rust pustules give a high ratio; a few large red-rot lesions give
    a low one. This is the main thing separating those two classes visually, and
    neither colour nor total coverage captures it.
    """
    area = int(mask.sum())
    if area < 30:
        return 0.0
    boundary = np.zeros_like(mask, dtype=bool)
    boundary[:-1, :] |= mask[:-1, :] != mask[1:, :]
    boundary[:, :-1] |= mask[:, :-1] != mask[:, 1:]
    return float((boundary & mask).sum()) / float(area)


def dominant_rgb(rgb: np.ndarray, bins: int = 6) -> list[int]:
    """Most common colour, found by coarse histogram quantisation."""
    quantised = np.clip((rgb * (bins - 1)).round().astype(np.int32), 0, bins - 1)
    flat = quantised.reshape(-1, 3)
    codes = flat[:, 0] * bins * bins + flat[:, 1] * bins + flat[:, 2]
    winner = int(np.bincount(codes).argmax())
    r = winner // (bins * bins)
    g = (winner // bins) % bins
    b = winner % bins
    scale = 255.0 / (bins - 1)
    return [int(r * scale), int(g * scale), int(b * scale)]


# ------------------------------------------------------------------ colour masks
def colour_masks(hsv: np.ndarray) -> dict[str, np.ndarray]:
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    return {
        "green": (hue >= 65) & (hue <= 175) & (sat > 0.18) & (val > 0.12),
        "yellow": (hue >= 35) & (hue < 65) & (sat > 0.25) & (val > 0.25),
        "orange_brown": (((hue < 35) | (hue > 340)) & (sat > 0.20) & (val > 0.12)),
        "dark": val < 0.22,
        "bleached": (sat < 0.14) & (val > 0.68),
        "grey": (sat < 0.16) & (val >= 0.25) & (val <= 0.68),
    }


@dataclass
class ImageFeatures:
    width: int
    height: int
    mean_rgb: list[float]
    dominant_rgb: list[int]
    mean_hue: float
    mean_saturation: float
    mean_value: float
    brightness: float
    contrast: float
    sharpness: float
    graininess: float
    edge_density: float
    green_ratio: float
    yellow_ratio: float
    brown_ratio: float
    dark_ratio: float
    bleached_ratio: float
    grey_ratio: float
    green_hue_std: float
    green_value_std: float
    vertical_streak_score: float
    brown_fragmentation: float
    tissue_ratio: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _vertical_streak_score(mask: np.ndarray) -> float:
    """How strongly a mask forms long vertical/lengthwise streaks.

    Leaf streak symptoms (leaf scald, yellow leaf midrib) run along the leaf,
    so column-wise concentration separates them from scattered speckling.
    """
    if mask.size == 0 or not mask.any():
        return 0.0
    column_share = mask.mean(axis=0)
    row_share = mask.mean(axis=1)
    column_spread = float(column_share.std())
    row_spread = float(row_share.std())
    if column_spread + row_spread <= 1e-6:
        return 0.0
    return float(column_spread / (column_spread + row_spread))


def extract_features(image: Image.Image) -> ImageFeatures:
    original_size = image.size
    rgb = to_array(image)
    hsv = rgb_to_hsv(rgb)
    masks = colour_masks(hsv)

    grey = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    green_mask = masks["green"]
    green_pixels_exist = bool(green_mask.any())

    combined_streak = masks["yellow"] | masks["bleached"]

    return ImageFeatures(
        width=original_size[0],
        height=original_size[1],
        mean_rgb=[round(float(rgb[..., i].mean()), 4) for i in range(3)],
        dominant_rgb=dominant_rgb(rgb),
        mean_hue=round(float(np.mean(hsv[..., 0][hsv[..., 1] > 0.1])) if (hsv[..., 1] > 0.1).any() else 0.0, 2),
        mean_saturation=round(float(hsv[..., 1].mean()), 4),
        mean_value=round(float(hsv[..., 2].mean()), 4),
        brightness=round(float(grey.mean()), 4),
        contrast=round(float(grey.std()), 4),
        sharpness=round(laplacian_variance(rgb), 3),
        graininess=round(local_variance(rgb), 4),
        edge_density=round(edge_density(rgb), 4),
        green_ratio=round(float(green_mask.mean()), 4),
        yellow_ratio=round(float(masks["yellow"].mean()), 4),
        brown_ratio=round(float(masks["orange_brown"].mean()), 4),
        dark_ratio=round(float(masks["dark"].mean()), 4),
        bleached_ratio=round(float(masks["bleached"].mean()), 4),
        grey_ratio=round(float(masks["grey"].mean()), 4),
        green_hue_std=round(float(hsv[..., 0][green_mask].std()) if green_pixels_exist else 0.0, 3),
        green_value_std=round(float(hsv[..., 2][green_mask].std()) if green_pixels_exist else 0.0, 4),
        vertical_streak_score=round(_vertical_streak_score(combined_streak), 4),
        brown_fragmentation=round(mask_fragmentation(masks["orange_brown"]), 4),
        tissue_ratio=round(
            float((green_mask | masks["yellow"] | masks["orange_brown"] | masks["bleached"]).mean()), 4
        ),
    )


# ------------------------------------------------------------ image quality
def assess_quality(features: ImageFeatures) -> dict[str, Any]:
    """Honest reporting of whether the photo is good enough to analyse."""
    issues: list[str] = []
    score = 1.0

    if min(features.width, features.height) < 200:
        issues.append("The image is quite small. A larger photo gives a more reliable analysis.")
        score -= 0.30
    if features.sharpness < 8:
        issues.append("The image looks blurred or out of focus. Hold the camera steady and retake it.")
        score -= 0.30
    elif features.sharpness < 20:
        issues.append("The image is a little soft. A sharper photo would improve confidence.")
        score -= 0.12
    if features.brightness < 0.16:
        issues.append("The image is very dark. Photograph in daylight, avoiding deep shade.")
        score -= 0.25
    elif features.brightness > 0.88:
        issues.append("The image is over-exposed. Avoid direct flash and harsh midday glare.")
        score -= 0.20
    if features.contrast < 0.06:
        issues.append("The image has very little contrast, so features are hard to separate.")
        score -= 0.15

    score = max(0.05, min(1.0, score))
    if score >= 0.85:
        rating = "good"
    elif score >= 0.6:
        rating = "acceptable"
    elif score >= 0.35:
        rating = "poor"
    else:
        rating = "very poor"

    return {
        "rating": rating,
        "score": round(score, 2),
        "issues": issues,
        "resolution": f"{features.width} x {features.height}",
        "sharpness": features.sharpness,
        "brightness": round(features.brightness, 3),
    }


def looks_like_plant(features: ImageFeatures) -> bool:
    """Rough sanity check that the photo contains vegetation."""
    return features.green_ratio >= 0.06 or (features.yellow_ratio + features.brown_ratio) >= 0.25


def looks_like_soil(features: ImageFeatures) -> bool:
    """Rough sanity check that the photo is mostly bare soil, not a green canopy."""
    return features.green_ratio < 0.35
