"""Runtime wrapper around the trained irrigation model.

Loading is lazy and failure-tolerant: if ``models/irrigation_model.joblib`` is
missing, unreadable, or was trained with an incompatible feature order, the
service transparently falls back to the rule engine and says so in the response.
Nothing here ever pretends a model exists when it does not.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.ml import irrigation_engine as engine

logger = logging.getLogger(__name__)

MODEL_FILENAME = "irrigation_model.joblib"

_lock = threading.Lock()
_bundle: dict[str, Any] | None = None
_load_attempted = False
_load_error: str | None = None


def model_path() -> Path:
    return settings.models_dir / MODEL_FILENAME


def _load_bundle() -> dict[str, Any] | None:
    global _bundle, _load_attempted, _load_error

    with _lock:
        if _load_attempted:
            return _bundle
        _load_attempted = True

        path = model_path()
        if not path.exists():
            _load_error = f"No trained model at {path}"
            logger.info("Irrigation model not found at %s - using the rule engine.", path)
            return None

        try:
            import joblib  # imported lazily so the app starts without scikit-learn

            bundle = joblib.load(path)
        except Exception as exc:  # noqa: BLE001 - any failure must degrade gracefully
            _load_error = f"Could not load {path.name}: {exc}"
            logger.warning("Irrigation model failed to load: %s", exc)
            return None

        if not isinstance(bundle, dict) or "regressor" not in bundle:
            _load_error = f"{path.name} is not a Smart Sugarcane irrigation bundle"
            logger.warning(_load_error)
            return None

        stored_order = list(bundle.get("feature_order", []))
        if stored_order != engine.FEATURE_ORDER:
            _load_error = (
                "Feature order in the saved model does not match the current code "
                f"(saved: {stored_order}, expected: {engine.FEATURE_ORDER}). Retrain the model."
            )
            logger.warning(_load_error)
            return None

        _bundle = bundle
        _load_error = None
        logger.info("Loaded trained irrigation model from %s", path)
        return _bundle


def reload_model() -> None:
    """Force the next prediction to re-read the model file from disk."""
    global _bundle, _load_attempted, _load_error
    with _lock:
        _bundle = None
        _load_attempted = False
        _load_error = None


def is_available() -> bool:
    return _load_bundle() is not None


def _to_frame(payload: dict[str, Any]):
    import pandas as pd

    row = {name: payload[name] for name in engine.FEATURE_ORDER}
    return pd.DataFrame([row], columns=engine.FEATURE_ORDER)


def predict(payload: dict[str, Any]) -> dict[str, Any]:
    """Return an irrigation decision plus provenance metadata.

    ``payload`` must contain every key in ``engine.FEATURE_ORDER`` and may also
    contain ``irrigation_method`` and ``area_hectares``.
    """
    inputs = {
        "soil_moisture": float(payload["soil_moisture"]),
        "temperature": float(payload["temperature"]),
        "humidity": float(payload["humidity"]),
        "rainfall": float(payload.get("rainfall", 0.0)),
        "rain_probability": float(payload.get("rain_probability", 0.0)),
        "wind_speed": float(payload.get("wind_speed", 5.0)),
        "weather_condition": str(payload.get("weather_condition", "clear")),
        "soil_type": str(payload.get("soil_type", "loamy")),
        "growth_stage": str(payload.get("growth_stage", "tillering")),
    }
    irrigation_method = str(payload.get("irrigation_method", "furrow"))
    area_hectares = float(payload.get("area_hectares", 1.0))

    bundle = _load_bundle()
    override: float | None = None
    model_source = "rule_engine"
    model_label = "Agronomy rule engine (water-balance model)"
    confidence = 0.75
    notes: list[str] = []

    if bundle is not None:
        try:
            frame = _to_frame(inputs)
            predicted_mm = float(bundle["regressor"].predict(frame)[0])
            override = max(0.0, predicted_mm)
            model_source = "trained_model"
            model_label = f"Trained {bundle.get('regressor_name', 'RandomForest')} regression model"

            classifier = bundle.get("classifier")
            if classifier is not None:
                proba = classifier.predict_proba(frame)[0]
                classes = list(classifier.classes_)
                predicted_class = classifier.predict(frame)[0]
                confidence = float(max(proba))
                model_needs_water = bool(predicted_class)
                if True in classes:
                    needs_water_probability = float(proba[classes.index(True)]) * 100
                    notes.append(
                        f"Classifier probability that irrigation is needed: {needs_water_probability:.0f} %"
                    )
                else:
                    notes.append(f"Classifier confidence: {confidence * 100:.0f} %")
            else:
                model_needs_water = override >= engine.MIN_USEFUL_IRRIGATION_MM

            dataset_type = bundle.get("dataset_type", "unknown")
            if dataset_type == "synthetic_demonstration":
                notes.append(
                    "This model was trained on a SYNTHETIC demonstration dataset generated from the "
                    "water-balance model. Replace it with real field data before relying on it operationally."
                )
            metrics = bundle.get("metrics", {})
            if metrics:
                notes.append(
                    "Held-out test performance - "
                    f"water requirement R2: {metrics.get('regressor_r2', 0):.3f}, "
                    f"MAE: {metrics.get('regressor_mae', 0):.2f} mm, "
                    f"decision accuracy: {metrics.get('classifier_accuracy', 0) * 100:.1f} %."
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Irrigation model prediction failed, falling back to rules: %s", exc)
            override = None
            model_source = "rule_engine"
            model_label = "Agronomy rule engine (water-balance model)"
            notes.append(f"The trained model could not score this input ({exc}). Rule engine used instead.")
            model_needs_water = None
    else:
        model_needs_water = None
        notes.append(
            "No trained irrigation model file found, so the transparent water-balance rule engine "
            "produced this result. Run ml/irrigation/train.py to enable the machine-learning model."
        )
        if _load_error and "No trained model" not in _load_error:
            notes.append(_load_error)

    decision = engine.decide(
        **inputs,
        irrigation_method=irrigation_method,
        area_hectares=area_hectares,
        net_requirement_override=override,
    )

    if model_needs_water is not None and model_needs_water != decision.irrigation_required:
        notes.append(
            "The classifier and the water-balance threshold disagree on this borderline case. "
            "The conservative water-balance answer is shown. Check the soil by hand before deciding."
        )
        confidence = min(confidence, 0.6)

    result = decision.as_dict()
    result.update(
        {
            "model_source": model_source,
            "model_label": model_label,
            "model_confidence": round(confidence, 3),
            "model_notes": notes,
        }
    )
    return result


def status() -> dict[str, Any]:
    bundle = _load_bundle()
    path = model_path()
    if bundle is None:
        return {
            "trained_model_available": False,
            "model_path": str(path),
            "model_source": "rule_engine",
            "trained_at": None,
            "dataset_rows": None,
            "dataset_type": None,
            "metrics": None,
            "notes": [
                _load_error or "No trained model file present.",
                "The API is fully functional using the transparent water-balance rule engine.",
                "To train the demonstration model: python ml/irrigation/train.py",
            ],
        }
    return {
        "trained_model_available": True,
        "model_path": str(path),
        "model_source": "trained_model",
        "trained_at": bundle.get("trained_at"),
        "dataset_rows": bundle.get("dataset_rows"),
        "dataset_type": bundle.get("dataset_type"),
        "metrics": bundle.get("metrics"),
        "notes": [
            f"Model type: {bundle.get('regressor_name', 'RandomForestRegressor')} + "
            f"{bundle.get('classifier_name', 'RandomForestClassifier')}",
            f"scikit-learn version at training time: {bundle.get('sklearn_version', 'unknown')}",
            "Trained on a synthetic demonstration dataset - replace with real field data for production use."
            if bundle.get("dataset_type") == "synthetic_demonstration"
            else "Trained on a user-supplied dataset.",
        ],
    }
