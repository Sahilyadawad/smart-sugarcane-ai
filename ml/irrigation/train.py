"""Train the irrigation model.

Trains two scikit-learn models on the same features:

* ``RandomForestRegressor``  -> net water requirement in mm
* ``RandomForestClassifier`` -> whether irrigation is needed at all

Both are wrapped in a pipeline with one-hot encoding for the categorical
columns, then saved together in a single joblib bundle that also records the
feature order, the metrics, and whether the training data was synthetic. The
backend refuses to load a bundle whose feature order does not match the current
code, so a stale model can never silently produce nonsense.

Usage
-----
    python ml/irrigation/train.py                      # generates data if needed, then trains
    python ml/irrigation/train.py --data my_field.csv  # train on your own logged data
    python ml/irrigation/train.py --rows 25000         # bigger synthetic set
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.ml import irrigation_engine as engine  # noqa: E402

DEFAULT_DATA = Path(__file__).resolve().parent / "irrigation_dataset.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "models" / "irrigation_model.joblib"
TARGET_REGRESSION = "water_requirement_mm"
TARGET_CLASSIFICATION = "irrigation_required"


def load_or_create_dataset(path: Path, rows: int, seed: int) -> tuple[pd.DataFrame, str]:
    """Return (dataframe, dataset_type)."""
    if path.exists():
        frame = pd.read_csv(path)
        dataset_type = (
            "synthetic_demonstration" if path.resolve() == DEFAULT_DATA.resolve() else "user_supplied"
        )
        print(f"Loaded {len(frame):,} rows from {path}")
        return frame, dataset_type

    if path.resolve() != DEFAULT_DATA.resolve():
        raise SystemExit(
            f"Dataset not found: {path}\n"
            "Provide a CSV with these columns:\n  " + ", ".join(engine.FEATURE_ORDER)
            + f", {TARGET_REGRESSION}, {TARGET_CLASSIFICATION}"
        )

    print(f"No dataset at {path} - generating a synthetic demonstration dataset first.")
    from generate_sample_dataset import generate  # noqa: PLC0415

    frame = generate(rows, seed)
    frame.to_csv(path, index=False)
    print(f"Wrote {len(frame):,} synthetic rows to {path}")
    return frame, "synthetic_demonstration"


def validate_columns(frame: pd.DataFrame) -> None:
    required = set(engine.FEATURE_ORDER) | {TARGET_REGRESSION, TARGET_CLASSIFICATION}
    missing = required - set(frame.columns)
    if missing:
        raise SystemExit(
            "The dataset is missing required columns: " + ", ".join(sorted(missing))
            + "\nExpected columns: " + ", ".join(sorted(required))
        )


def build_pipeline(estimator):
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                engine.CATEGORICAL_FEATURES,
            ),
        ],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    return Pipeline([("preprocess", preprocessor), ("model", estimator)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="training CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="where to save the joblib bundle")
    parser.add_argument("--rows", type=int, default=12_000, help="rows to generate if no dataset exists")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--n-estimators", type=int, default=120)
    # Unbounded trees on 10k rows produce a ~110 MB artifact. Depth 12 brings that
    # down to ~17 MB and costs only about 0.4 percentage points of accuracy, which
    # is well inside the noise of a synthetic dataset.
    parser.add_argument("--max-depth", type=int, default=12)
    args = parser.parse_args()

    try:
        import joblib
        import sklearn
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.metrics import (
            accuracy_score,
            classification_report,
            f1_score,
            mean_absolute_error,
            r2_score,
        )
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise SystemExit(
            f"Missing dependency: {exc.name}\n"
            "Install the backend requirements first:\n"
            "  pip install -r backend/requirements.txt"
        ) from exc

    frame, dataset_type = load_or_create_dataset(args.data, args.rows, args.seed)
    validate_columns(frame)

    features = frame[engine.FEATURE_ORDER].copy()
    y_reg = frame[TARGET_REGRESSION].astype(float)
    y_clf = frame[TARGET_CLASSIFICATION].astype(bool)

    x_train, x_test, yr_train, yr_test, yc_train, yc_test = train_test_split(
        features, y_reg, y_clf, test_size=args.test_size, random_state=args.seed, stratify=y_clf
    )
    print(f"\nTraining rows: {len(x_train):,}   Test rows: {len(x_test):,}")

    print("\nTraining RandomForestRegressor (water requirement, mm)...")
    regressor = build_pipeline(
        RandomForestRegressor(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            min_samples_leaf=4,
            random_state=args.seed,
            n_jobs=-1,
        )
    )
    regressor.fit(x_train, yr_train)
    reg_pred = regressor.predict(x_test)
    reg_r2 = float(r2_score(yr_test, reg_pred))
    reg_mae = float(mean_absolute_error(yr_test, reg_pred))
    reg_rmse = float(np.sqrt(np.mean((yr_test - reg_pred) ** 2)))
    print(f"  R2   : {reg_r2:.4f}")
    print(f"  MAE  : {reg_mae:.3f} mm")
    print(f"  RMSE : {reg_rmse:.3f} mm")

    print("\nTraining RandomForestClassifier (irrigation required)...")
    classifier = build_pipeline(
        RandomForestClassifier(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            min_samples_leaf=4,
            class_weight="balanced",
            random_state=args.seed,
            n_jobs=-1,
        )
    )
    classifier.fit(x_train, yc_train)
    clf_pred = classifier.predict(x_test)
    clf_accuracy = float(accuracy_score(yc_test, clf_pred))
    clf_f1 = float(f1_score(yc_test, clf_pred))
    print(f"  Accuracy : {clf_accuracy * 100:.2f} %")
    print(f"  F1       : {clf_f1:.4f}")
    print("\n" + classification_report(yc_test, clf_pred, target_names=["no irrigation", "irrigate"]))

    bundle = {
        "version": 1,
        "feature_order": engine.FEATURE_ORDER,
        "numeric_features": engine.NUMERIC_FEATURES,
        "categorical_features": engine.CATEGORICAL_FEATURES,
        "regressor": regressor,
        "classifier": classifier,
        "regressor_name": "RandomForestRegressor",
        "classifier_name": "RandomForestClassifier",
        "metrics": {
            "regressor_r2": round(reg_r2, 4),
            "regressor_mae": round(reg_mae, 4),
            "regressor_rmse": round(reg_rmse, 4),
            "classifier_accuracy": round(clf_accuracy, 4),
            "classifier_f1": round(clf_f1, 4),
            "test_rows": int(len(x_test)),
        },
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_rows": int(len(frame)),
        "dataset_path": str(args.data),
        "dataset_type": dataset_type,
        "sklearn_version": sklearn.__version__,
        "honesty_note": (
            "Trained on a synthetic dataset generated from the project's water-balance model. "
            "Metrics show how well the model reproduces that model, NOT how well it predicts real "
            "field irrigation outcomes."
            if dataset_type == "synthetic_demonstration"
            else "Trained on a user-supplied dataset."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, args.output)

    metrics_path = args.output.with_suffix(".metrics.json")
    metrics_path.write_text(
        json.dumps(
            {k: v for k, v in bundle.items() if k not in {"regressor", "classifier"}},
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nSaved model bundle : {args.output}")
    print(f"Saved metrics      : {metrics_path}")
    if dataset_type == "synthetic_demonstration":
        print("\n" + "!" * 72)
        print("SYNTHETIC DATA WARNING")
        print("The metrics above measure how well the forest reproduces the water-balance")
        print("model it was trained on - not how accurately it predicts real irrigation")
        print("outcomes. Retrain on logged field data before operational use.")
        print("!" * 72)
    print("\nThe backend picks this up automatically on restart, or immediately via")
    print("POST /api/irrigation/reload-model")


if __name__ == "__main__":
    main()
