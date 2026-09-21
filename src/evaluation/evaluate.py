"""Phase 2 - evaluation + registry lifecycle (tracer slice).

Reads logged test metrics via MlflowClient, ranks runs by strict max
test ROC-AUC (D-03, no tie-break), transitions the winner version to
Staging and every superseded version to Archived. Never touches
Production (D-06: separate explicit step).

Invoked as ``python -m src.evaluation.evaluate`` from the project root.
"""
import os
import sys
from types import SimpleNamespace

import mlflow
from mlflow.tracking import MlflowClient
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

REGISTERED_MODEL_NAME = "corvus-ckd"
METRIC_NAMES = ("accuracy", "precision", "recall", "f1", "roc_auc")


def compute_metrics(y_true, y_pred, y_proba) -> dict:
    """All 5 metrics; ROC-AUC from predict_proba column 1, never labels."""
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        # Pitfall 8: ROC-AUC from probabilities, never from labels.
        "roc_auc": roc_auc_score(y_true, y_proba),
    }


def select_winner(runs: list) -> dict:
    """Strict max by test roc_auc (D-03). No tie-break logic by design."""
    return max(runs, key=lambda r: r["metrics"]["roc_auc"])


def resolve_winner_version(versions: list, winner_run_id: str):
    """Map the winning run to its registered version via run_id linkage.

    The tracer's latest-version heuristic breaks once 9 runs register 9
    versions, so resolve through ``ModelVersion.run_id`` (present in
    installed mlflow 3.16.1). Falls back to the latest version only when
    no version links to the winner run.
    """
    for v in versions:
        if v.run_id == winner_run_id:
            return v.version
    return max(v.version for v in versions)


def apply_registry_stages(client: MlflowClient, model_name: str, winner_version: str,
                          superseded_versions: list) -> None:
    """Winner to Staging, superseded to Archived. Never Production (D-06)."""
    # TECH DEBT (Pitfall 2): model-registry stages are deprecated since
    # MLflow 2.9 and slated for removal in a future major; still functional
    # in installed 3.16.1 which FR-3.1 mandates. Follow-up: migrate to model
    # aliases (set_registered_model_alias) in a later phase.
    client.transition_model_version_stage(
        name=model_name,
        version=winner_version,
        stage="Staging",
        archive_existing_versions=True,
    )
    for version in superseded_versions:
        client.transition_model_version_stage(
            name=model_name, version=version, stage="Archived"
        )


def run_evaluation(model_name: str = REGISTERED_MODEL_NAME):
    """Rank runs in experiment corvus-ckd and apply registry stages."""
    cfg = load_config()
    mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))
    client = MlflowClient()
    try:
        experiment = client.get_experiment_by_name(cfg["mlflow"]["experiment_name"])
        mlflow_runs = client.search_runs(
            [experiment.experiment_id], filter_string="status = 'FINISHED'"
        )
        records = [
            {
                "run_id": r.info.run_id,
                "run_name": r.data.tags.get("mlflow.runName", r.info.run_id),
                "metrics": {m: r.data.metrics[m] for m in METRIC_NAMES},
            }
            for r in mlflow_runs
            if all(m in r.data.metrics for m in METRIC_NAMES)
        ]
        if not records:
            log.warning("No complete runs found for evaluation")
            return SimpleNamespace(success=False, winner=None)
        winner = select_winner(records)

        versions = client.search_model_versions(f"name='{model_name}'")
        if versions:
            winner_version = resolve_winner_version(versions, winner["run_id"])
            superseded = [v.version for v in versions if v.version != winner_version]
            apply_registry_stages(client, model_name, winner_version, superseded)
            stage = client.get_model_version(model_name, winner_version).current_stage
        else:
            winner_version, stage = None, None
        log.info(f"Winner: {winner['run_name']} roc_auc={winner['metrics']['roc_auc']}")
        return SimpleNamespace(success=True, winner=winner,
                               version=winner_version, stage=stage)
    except Exception as exc:
        log.warning(f"Evaluation failed: {type(exc).__name__}: {exc}")
        return SimpleNamespace(success=False, winner=None)


def main() -> int:
    try:
        result = run_evaluation()
    except Exception as exc:
        print(f"EVALUATION ERROR: {exc}")
        return 1
    if result.success:
        print(f"WINNER {result.winner['run_name']} "
              f"roc_auc={result.winner['metrics']['roc_auc']:.4f} "
              f"version={result.version} stage={result.stage}")
        return 0
    print("EVALUATION FAILED — see log for details")
    return 1


if __name__ == "__main__":
    sys.exit(main())
