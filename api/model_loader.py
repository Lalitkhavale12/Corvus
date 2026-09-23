"""Startup-pinned registry loader for the Corvus prediction API.

Resolves the serving version once from config/env (``api.pinned_version``,
``MODEL_VERSION`` env override), loads ``models:/corvus-ckd/<version>`` via
``mlflow.sklearn.load_model`` plus the co-logged preprocessing pipeline
from the version's ``run_id``, then asserts the pipeline output width
equals the estimator's ``n_features_in_`` before serving.

FR-4.4 deviation (locked D-02): pinning happens at startup, not per
request — model swaps need restarts.
"""
from __future__ import annotations

import os

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

from pathlib import Path

import joblib
import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

from src.preprocessing.preprocess import get_column_lists
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

REGISTERED_MODEL_NAME = "corvus-ckd"
PIPELINE_ARTIFACT_PATH = "preprocessing/preprocessing_pipeline.joblib"

# Literal-valid probe values (handle_unknown="ignore" in the pipeline, so
# the assertion only checks width, never vocabulary membership).
_PROBE_CATEGORICALS = {
    "rbc": "normal",
    "pc": "normal",
    "pcc": "notpresent",
    "ba": "notpresent",
    "htn": "no",
    "dm": "no",
    "cad": "no",
    "appet": "good",
    "pe": "no",
    "ane": "no",
}


def resolve_pinned_version() -> str:
    """Serving version: MODEL_VERSION env wins, else config api.pinned_version."""
    override = os.environ.get("MODEL_VERSION")
    if override:
        return str(override)
    cfg = load_config()
    return str(cfg["api"]["pinned_version"])


def resolve_tracking_uri(cfg: dict | None = None) -> str:
    """Tracking URI: MLFLOW_TRACKING_URI env, else api.tracking_uri, else mlflow.

    Relative paths anchor at PROJECT_ROOT so container and host layouts agree.
    """
    cfg = cfg if cfg is not None else load_config()
    uri = (
        os.environ.get("MLFLOW_TRACKING_URI")
        or cfg.get("api", {}).get("tracking_uri")
        or cfg["mlflow"]["tracking_uri"]
    )
    if "://" in uri or Path(uri).is_absolute():
        return uri
    return str(PROJECT_ROOT / uri)


def load_serving_artifacts(version: str):
    """Load estimator + fitted pipeline for a pinned registry version.

    Returns ``(model, pipeline, run_id, version)``; raises loudly on a
    pipeline/estimator width mismatch so a skewed artifact never serves.
    """
    cfg = load_config()
    mlflow.set_tracking_uri(resolve_tracking_uri(cfg))
    client = MlflowClient()
    details = client.get_model_version(REGISTERED_MODEL_NAME, version)
    run_id = details.run_id
    model = mlflow.sklearn.load_model(f"models:/{REGISTERED_MODEL_NAME}/{version}")
    pipe_path = mlflow.artifacts.download_artifacts(
        run_id=run_id, artifact_path=PIPELINE_ARTIFACT_PATH
    )
    pipeline = joblib.load(pipe_path)
    numeric_cols, categorical_cols = get_column_lists()
    probe = pd.DataFrame(
        [
            {
                **{col: 1.0 for col in numeric_cols},
                **{col: _PROBE_CATEGORICALS[col] for col in categorical_cols},
            }
        ]
    )
    width = pipeline.transform(probe).shape[1]
    expected = int(model.n_features_in_)
    if width != expected:
        raise RuntimeError(
            f"Pipeline/estimator width mismatch for {REGISTERED_MODEL_NAME} "
            f"version {version}: pipeline yields {width} features, "
            f"estimator expects {expected}"
        )
    log.info(
        f"Serving {REGISTERED_MODEL_NAME} version={version} run_id={run_id} "
        f"features={expected}"
    )
    return model, pipeline, run_id, str(version)
