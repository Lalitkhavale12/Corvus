"""Phase 7 - NHANES-native training entry point (tracer: logistic regression).

Native-schema counterpart to ``src/training/train.py``: the quarantine
gate runs before any split, the locked holdout is split once, the native
pipeline is fitted on dev only, and one Claim-2 MLflow run (pipeline +
model artifacts, 5 metrics) lands under the ``corvus-ckd-nhanes``
experiment tagged ``schema=nhanes-native``, registered as ``corvus-ckd``.

Invoked as ``python -m src.training.train_nhanes`` from the project root.
"""

import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.preprocessing.preprocess_nhanes import (
    DERIVED_LABEL_DISCLOSURE,
    QUARANTINE_11,
    assert_quarantine,
    build_native_pipeline,
    get_nhanes_column_lists,
    locked_holdout_split,
)
from src.training.train import compute_metrics
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

REGISTERED_MODEL_NAME = "corvus-ckd"

# Tracer slice: logistic regression only (same seeded shape as the analog).
# Plan 07-02 expands to the full 9-config slate.
NATIVE_ESTIMATORS = {
    # Baseline linear model; random_state keeps the lbfgs shuffling reproducible.
    "logistic-regression": LogisticRegression(random_state=42),
}

NATIVE_PIPELINE_FILENAME = "preprocessing_pipeline_nhanes.joblib"


def build_native_estimator(name: str):
    """Return a fresh native estimator instance for a registered config name."""
    if name not in NATIVE_ESTIMATORS:
        raise KeyError(f"Unknown native estimator config: {name!r}")
    base = NATIVE_ESTIMATORS[name]
    return base.__class__(**base.get_params())


def run_experiment_native(name: str = "logistic-regression") -> dict:
    """Train one native config end-to-end and log the Claim-2 MLflow run."""
    cfg = load_config()
    target_col = cfg["data"]["nhanes_target_column"]
    positive_label = cfg["data"]["nhanes_positive_label"]
    csv_path = PROJECT_ROOT / cfg["data"]["nhanes_csv"]

    df = pd.read_csv(csv_path).copy()

    numeric_cols, categorical_cols = get_nhanes_column_lists()
    numeric_cols = [c for c in numeric_cols if c in df.columns]
    categorical_cols = [c for c in categorical_cols if c in df.columns]
    # The locked CSV carries the quarantined label-source columns by
    # design; they are dropped by the allow-list projection, never inputs.
    dropped_quarantine = sorted(set(df.columns) & QUARANTINE_11)
    if dropped_quarantine:
        log.info(f"Excluded quarantined label-source columns: {dropped_quarantine}")
    unexpected = (
        set(df.columns)
        - set(numeric_cols)
        - set(categorical_cols)
        - {target_col}
        - QUARANTINE_11
    )
    if unexpected:
        log.warning(f"Unexpected columns in {csv_path.name}: {unexpected}")

    y_raw = df[target_col]
    if set(pd.to_numeric(y_raw, errors="coerce").dropna().unique()) <= {0, 1}:
        y = pd.to_numeric(y_raw).astype(int)
    else:
        y = (
            y_raw.astype(str).str.strip().str.lower()
            == str(positive_label).strip().lower()
        ).astype(int)
    X = df[numeric_cols + categorical_cols]
    assert_quarantine(X)  # gate on the training frame, before any split or fit

    X_dev, X_hold, y_dev, y_hold = locked_holdout_split(X, y)

    pipeline = build_native_pipeline(numeric_cols, categorical_cols)
    pipeline.fit(X_dev)  # fit on dev only (leak-safe)
    X_hold_t = pipeline.transform(X_hold)

    estimator = build_native_estimator(name)
    estimator.fit(pipeline.transform(X_dev), y_dev)
    y_pred = estimator.predict(X_hold_t)
    y_proba = estimator.predict_proba(X_hold_t)[:, 1]
    metrics = compute_metrics(y_hold, y_pred, y_proba)

    pipeline_path = Path(cfg["data"]["processed_dir"]) / NATIVE_PIPELINE_FILENAME
    pipeline_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, pipeline_path)

    mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))
    mlflow.set_experiment(cfg["mlflow"]["nhanes_experiment_name"])
    with mlflow.start_run(run_name=f"native-{name}") as run:
        mlflow.set_tag("schema", "nhanes-native")
        mlflow.set_tag("label_disclosure", DERIVED_LABEL_DISCLOSURE)
        mlflow.set_tag("quarantine_attested", "true")
        mlflow.log_params({**estimator.get_params(), "model": type(estimator).__name__})
        mlflow.log_metrics({**metrics, "holdout_roc_auc": metrics["roc_auc"]})
        mlflow.log_artifact(str(pipeline_path), artifact_path="preprocessing")
        mlflow.sklearn.log_model(
            estimator,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME,
            serialization_format="cloudpickle",  # pin: 3.x default is skops
        )
        run_id = run.info.run_id
    log.info(f"Logged native run {name} ({run_id}) with metrics {metrics}")
    log.info(f"Disclosure: {DERIVED_LABEL_DISCLOSURE}")
    return {"run_id": run_id, "metrics": metrics, "features": list(X.columns)}


def main():
    for name in NATIVE_ESTIMATORS:
        result = run_experiment_native(name)
        print(f"TRAINED native-{name} roc_auc={result['metrics']['roc_auc']:.4f}")
        print(f"Disclosure: {DERIVED_LABEL_DISCLOSURE}")


if __name__ == "__main__":
    main()
