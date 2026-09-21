"""Phase 2 - MLP training entry point (3 activation runs, D-01/D-04/D-05).

Thin variant of ``src.training.train``: reuses the identical
``load_raw_splits`` and Claim 2 ``run_experiment`` shape (raw-CSV inputs,
train-only pipeline re-fit, one run holding params + 5 metrics + pipeline
artifact + model). The ONLY difference is the estimator factory below:
three ``MLPClassifier`` runs differing solely in activation, with
``hidden_layer_sizes=(50,)``, a fixed ``max_iter`` budget, seeded runs,
and no early stopping (the 40-row val split is too noisy a stop signal).

Invoked as ``python -m src.training.train_mlp`` from the project root.
"""

import os
import warnings
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPClassifier

from src.preprocessing.preprocess import build_pipeline, get_column_lists
from src.training.train import (
    REGISTERED_MODEL_NAME,
    compute_metrics,
    load_raw_splits,
)
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

# D-04: display name -> sklearn activation value. "sigmoid" is the textbook
# name but NOT a valid sklearn value (valid: identity/logistic/tanh/relu),
# so the map translates it; never pass the literal "sigmoid" to sklearn.
ACTIVATIONS = {"sigmoid": "logistic", "tanh": "tanh", "relu": "relu"}

# D-05: fixed iteration budget with seeded runs; no early stopping.
MAX_ITER = 500


def build_estimator(activation_name: str) -> MLPClassifier:
    """Return a fresh MLPClassifier for a display activation name."""
    if activation_name not in ACTIVATIONS:
        raise KeyError(f"Unknown MLP activation: {activation_name!r}")
    # D-02/D-04: library defaults apart from the locked small hidden layer,
    # mapped activation, fixed budget, and seed. One rationale: a single
    # 50-unit layer is right-sized for 279 train rows so runs stay comparable.
    return MLPClassifier(
        hidden_layer_sizes=(50,),
        activation=ACTIVATIONS[activation_name],
        max_iter=MAX_ITER,
        random_state=42,
    )


def run_experiment(activation_name: str = "sigmoid") -> dict:
    """Train one MLP activation end-to-end and log the Claim 2 MLflow run."""
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

    estimator = build_estimator(activation_name)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        estimator.fit(pipeline.transform(X_train), y_train)
    for warning in caught:
        # Warning-not-crash per project conventions: fixed-budget runs are
        # expected to raise ConvergenceWarning; log it, never silently ignore.
        log.warning(f"MLP ({activation_name}) training notice: {warning.message}")
    y_pred = estimator.predict(X_test_t)
    y_proba = estimator.predict_proba(X_test_t)[:, 1]
    metrics = compute_metrics(y_test, y_pred, y_proba)

    pipeline_path = Path(cfg["data"]["processed_dir"]) / "preprocessing_pipeline.joblib"
    joblib.dump(pipeline, pipeline_path)

    run_name = f"mlp-{activation_name}"
    with mlflow.start_run(run_name=run_name) as run:
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
    log.info(f"Logged run {run_name} ({run_id}) with metrics {metrics}")
    return {"run_id": run_id, "metrics": metrics, "features": list(X_train.columns)}


def main():
    for activation_name in ACTIVATIONS:
        result = run_experiment(activation_name)
        print(f"TRAINED mlp-{activation_name} roc_auc={result['metrics']['roc_auc']:.4f}")


if __name__ == "__main__":
    main()
