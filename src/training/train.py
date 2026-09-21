"""Phase 2 - training entry point (tracer slice: logistic regression).

Uniform per-run shape that plan 02-02 reuses for all 9 configs (D-01):
load ``*_raw.csv`` splits through a fresh pipeline re-fit on train-raw
only, fit one estimator, log params + 5 test metrics + pipeline artifact
+ model in a single MLflow run (Claim 2 contract).

Invoked as ``python -m src.training.train`` from the project root.
"""
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import os
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.preprocessing.preprocess import (
    LINEAGE_ID_COL,
    LINEAGE_ROW_COL,
    build_pipeline,
    get_column_lists,
)
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

REGISTERED_MODEL_NAME = "corvus-ckd"

# D-02: library defaults with fixed seeds + one rationale each. No grid
# search — at n=279 train rows, grids mostly fit noise. LR uses the
# liblinear-friendly default solver; random_state keeps runs reproducible.
ESTIMATORS = {
    "logistic-regression": LogisticRegression(random_state=42),
}


def build_estimator(name: str):
    """Return a fresh estimator instance for a registered config name."""
    if name not in ESTIMATORS:
        raise KeyError(f"Unknown estimator config: {name!r}")
    base = ESTIMATORS[name]
    return base.__class__(**base.get_params())


def load_raw_splits():
    """Load cleaned-but-untransformed raw splits; return (X_*, y_*) tuples.

    Drops lineage metadata (``__source_row``/``__source_id``) and the
    configured target from X, binary-encodes the target via
    ``data.positive_label``. Never reads transformed train/val/test.csv.
    """
    cfg = load_config()
    target_col = cfg["data"]["target_column"]
    positive_label = cfg["data"]["positive_label"].strip().lower()
    processed_dir = Path(cfg["data"]["processed_dir"])

    frames = {}
    for split in ("train", "val", "test"):
        path = processed_dir / f"{split}_raw.csv"
        df = pd.read_csv(path).copy()
        unexpected = set(df.columns) - set(
            get_column_lists()[0] + get_column_lists()[1]
        ) - {target_col, LINEAGE_ROW_COL, LINEAGE_ID_COL}
        if unexpected:
            log.warning(f"Unexpected columns in {path.name}: {unexpected}")
        y_raw = df[target_col]
        if set(pd.to_numeric(y_raw, errors="coerce").dropna().unique()) <= {0, 1}:
            # Phase 1 clean_raw already binary-encoded the target.
            y = pd.to_numeric(y_raw).astype(int)
        else:
            y = (y_raw.astype(str).str.strip().str.lower() == positive_label).astype(int)
        drop_cols = [c for c in (target_col, LINEAGE_ROW_COL, LINEAGE_ID_COL) if c in df.columns]
        X = df.drop(columns=drop_cols)
        frames[split] = (X, y)
    return frames["train"], frames["val"], frames["test"]


def compute_metrics(y_true, y_pred, y_proba) -> dict:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        # Pitfall 8: ROC-AUC from probabilities, never from labels.
        "roc_auc": roc_auc_score(y_true, y_proba),
    }


def run_experiment(name: str = "logistic-regression") -> dict:
    """Train one config end-to-end and log the Claim 2 MLflow run."""
    cfg = load_config()
    mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))
    mlflow.set_experiment(cfg["mlflow"]["experiment_name"])

    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_raw_splits()
    numeric_cols, categorical_cols = get_column_lists()
    numeric_cols = [c for c in numeric_cols if c in X_train.columns]
    categorical_cols = [c for c in categorical_cols if c in X_train.columns]

    pipeline = build_pipeline(numeric_cols, categorical_cols)
    pipeline.fit(X_train)  # fit on train-raw only (leak-safe)
    X_test_t = pipeline.transform(X_test)

    estimator = build_estimator(name)
    estimator.fit(pipeline.transform(X_train), y_train)
    y_pred = estimator.predict(X_test_t)
    y_proba = estimator.predict_proba(X_test_t)[:, 1]
    metrics = compute_metrics(y_test, y_pred, y_proba)

    pipeline_path = Path(cfg["data"]["processed_dir"]) / "preprocessing_pipeline.joblib"
    joblib.dump(pipeline, pipeline_path)

    with mlflow.start_run(run_name=name) as run:
        mlflow.log_params({**estimator.get_params(), "model": type(estimator).__name__})
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(pipeline_path), artifact_path="preprocessing")
        mlflow.sklearn.log_model(
            estimator,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME,
            serialization_format="cloudpickle",  # pin: 3.x default is skops (Pitfall 3)
        )
        run_id = run.info.run_id
    log.info(f"Logged run {name} ({run_id}) with metrics {metrics}")
    return {"run_id": run_id, "metrics": metrics, "features": list(X_train.columns)}


def main():
    result = run_experiment("logistic-regression")
    print(f"TRAINED logistic-regression roc_auc={result['metrics']['roc_auc']:.4f}")


if __name__ == "__main__":
    main()
