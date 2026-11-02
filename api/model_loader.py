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

import json
import os

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

from pathlib import Path

import joblib
import mlflow
import pandas as pd
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from src.preprocessing.preprocess import get_column_lists
from src.preprocessing.preprocess_nhanes import get_nhanes_column_lists
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

REGISTERED_MODEL_NAME = "corvus-ckd"
PIPELINE_ARTIFACT_PATH = "preprocessing/preprocessing_pipeline.joblib"
# Native pipeline filename is distinct from v1 by 07-01 design; this must
# track src.training.train_nhanes.NATIVE_PIPELINE_FILENAME (pinned by test).
V2_PIPELINE_ARTIFACT_PATH = "preprocessing/preprocessing_pipeline_nhanes.joblib"
# Must track src.training.train_nhanes.THRESHOLD_ARTIFACT_PATH/FILENAME.
V2_THRESHOLD_ARTIFACT_PATH = "evaluation/nhanes_decision_threshold.json"
# Cut-off used when a run predates threshold selection.
DEFAULT_DECISION_THRESHOLD = 0.5

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


# Native-schema probe literals (verified against the locked derived CSV;
# handle_unknown="ignore" means the assert checks width, never vocabulary).
_V2_PROBE_CATEGORICALS = {
    "RIAGENDR": 1,
    "RIDRETH1": 1,
    "DMDEDUC2": 1,
    "DIQ010": 1,
    "MCQ035": 1,
}


def resolve_v2_version() -> str:
    """v2 serving version: MODEL_VERSION_V2 env wins, else api.v2_pinned_version.

    Empty string when no challenger pin is configured — the /v2 routes
    fail closed on that (503) instead of serving anything unapproved.
    """
    override = os.environ.get("MODEL_VERSION_V2")
    if override:
        return str(override)
    cfg = load_config()
    return str(cfg["api"].get("v2_pinned_version", ""))


def load_v2_artifacts(version: str):
    """Load estimator + co-logged NATIVE pipeline for a v2 registry version.

    Mirrors ``load_serving_artifacts`` on the native 16+5 schema: probes a
    native-schema frame and raises RuntimeError when the pipeline output
    width differs from the estimator's ``n_features_in_``.
    Returns ``(model, pipeline, run_id, version)``.
    """
    cfg = load_config()
    mlflow.set_tracking_uri(resolve_tracking_uri(cfg))
    client = MlflowClient()
    details = client.get_model_version(REGISTERED_MODEL_NAME, version)
    run_id = details.run_id
    model = mlflow.sklearn.load_model(f"models:/{REGISTERED_MODEL_NAME}/{version}")
    pipe_path = mlflow.artifacts.download_artifacts(
        run_id=run_id, artifact_path=V2_PIPELINE_ARTIFACT_PATH
    )
    pipeline = joblib.load(pipe_path)
    numeric_cols, categorical_cols = get_nhanes_column_lists()
    probe = pd.DataFrame(
        [
            {
                **{col: 1.0 for col in numeric_cols},
                **{col: _V2_PROBE_CATEGORICALS[col] for col in categorical_cols},
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
        f"Serving v2 {REGISTERED_MODEL_NAME} version={version} run_id={run_id} "
        f"features={expected}"
    )
    return model, pipeline, run_id, str(version)


def load_v2_threshold(version: str) -> float:
    """Decision cut-off for v2, taken from the same run as the pipeline.

    A cut-off only means anything against the estimator that produced the
    probabilities, so it is resolved per version rather than configured
    globally. Runs logged before threshold selection existed carry no
    artifact; those fall back to 0.5.
    """
    if not version:
        return DEFAULT_DECISION_THRESHOLD
    cfg = load_config()
    mlflow.set_tracking_uri(resolve_tracking_uri(cfg))
    client = MlflowClient()
    run_id = client.get_model_version(REGISTERED_MODEL_NAME, str(version)).run_id
    try:
        path = mlflow.artifacts.download_artifacts(
            run_id=run_id, artifact_path=V2_THRESHOLD_ARTIFACT_PATH
        )
    except MlflowException:
        log.warning(
            f"No decision threshold artifact for version {version}; "
            f"falling back to {DEFAULT_DECISION_THRESHOLD}"
        )
        return DEFAULT_DECISION_THRESHOLD
    with open(path, encoding="utf-8") as handle:
        return float(json.load(handle)["threshold"])


# ---------------------------------------------------------------------------
# Model Management (Phase 4 - Enhanced API)
# ---------------------------------------------------------------------------

def list_all_model_versions() -> list[dict]:
    """List all registered model versions in MLflow registry."""
    client = MlflowClient()
    try:
        versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
    except Exception as e:
        log.warning(f"Failed to search model versions: {e}")
        return []

    results = []
    for mv in versions:
        try:
            details = client.get_model_version(REGISTERED_MODEL_NAME, mv.version)
            results.append({
                "name": mv.name,
                "version": mv.version,
                "stage": mv.current_stage,
                "run_id": mv.run_id,
                "creation_timestamp": mv.creation_timestamp,
                "last_updated_timestamp": mv.last_updated_timestamp,
                "metrics": dict(mv.metadata.metrics) if mv.metadata and mv.metadata.metrics else {},
                "tags": dict(mv.tags) if mv.tags else {},
            })
        except Exception:
            continue
    return results


def get_model_version_details(version: str) -> dict | None:
    """Get detailed information about a specific model version."""
    client = MlflowClient()
    try:
        details = client.get_model_version(REGISTERED_MODEL_NAME, version)
        return {
            "name": details.name,
            "version": details.version,
            "stage": details.current_stage,
            "run_id": details.run_id,
            "creation_timestamp": details.creation_timestamp,
            "last_updated_timestamp": details.last_updated_timestamp,
            "status": details.status,
            "status_message": details.status_message,
            "metrics": dict(details.metadata.metrics) if details.metadata and details.metadata.metrics else {},
            "tags": dict(details.tags) if details.tags else {},
            "source": details.source,
            "run_link": f"{client.tracking_uri}/#/experiments/{details.run_id}/runs/{details.run_id}",
        }
    except Exception as e:
        log.warning(f"Failed to get model version details for {version}: {e}")
        return None


def compare_model_versions(champion_version: str, challenger_version: str) -> dict:
    """Compare two model versions side by side."""
    client = MlflowClient()

    champion_details = get_model_version_details(champion_version)
    challenger_details = get_model_version_details(challenger_version)

    if not champion_details:
        return {
            "error": f"Champion version {champion_version} not found",
            "promoted": False,
        }

    if not challenger_details:
        return {
            "error": f"Challenger version {challenger_version} not found",
            "promoted": False,
        }

    # Compare metrics
    champion_metrics = champion_details.get("metrics", {})
    challenger_metrics = challenger_details.get("metrics", {})

    all_metric_names = set(champion_metrics.keys()) | set(challenger_metrics.keys())

    comparison = []
    improvements = 0
    degradations = 0

    for metric_name in sorted(all_metric_names):
        champ_val = champion_metrics.get(metric_name)
        chall_val = challenger_metrics.get(metric_name)

        if champ_val is not None and chall_val is not None:
            try:
                champ_f = float(champ_val)
                chall_f = float(chall_val)
                if champ_f > 0:
                    improvement_pct = ((chall_f - champ_f) / champ_f) * 100
                    if chall_f > champ_f:
                        improvements += 1
                    elif chall_f < champ_f:
                        degradations += 1
                comparison.append({
                    "metric": metric_name,
                    "champion": champ_val,
                    "challenger": chall_val,
                    "improvement_pct": round(improvement_pct, 2),
                    "improved": chall_f > champ_f,
                })
            except (ValueError, TypeError):
                comparison.append({
                    "metric": metric_name,
                    "champion": champ_val,
                    "challenger": chall_val,
                    "improvement_pct": None,
                    "improved": None,
                })
        else:
            comparison.append({
                "metric": metric_name,
                "champion": champ_val,
                "challenger": chall_val,
                "improvement_pct": None,
                "improved": None,
            })

    is_better = improvements > degradations

    return {
        "champion_version": champion_version,
        "challenger_version": challenger_version,
        "champion_metrics": champion_metrics,
        "challenger_metrics": challenger_metrics,
        "comparison": comparison,
        "improvements": improvements,
        "degradations": degradations,
        "is_better": is_better,
        "recommend_promote": is_better and improvements > 0,
    }
