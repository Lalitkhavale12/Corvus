"""Promote a corvus-ckd version to Production, archiving the outgoing one.

This is the human half of Claim 5: the retraining DAG only recommends a
challenger, the registry stage moves here in one audited step. Archiving
keeps every retired version in the registry, so a rollback is a second
transition rather than a retrain.

Usage::

    .\\venv\\python.exe scripts/promote_production.py 17
    .\\venv\\python.exe scripts/promote_production.py        # config pin
"""

import os
import sys
from pathlib import Path

# Allow `.\venv\python.exe scripts/promote_production.py` from the project
# root: plain-script runs don't put the root on sys.path (unlike `python -m`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mlflow
from mlflow.tracking import MlflowClient

from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

REGISTERED_MODEL_NAME = "corvus-ckd"


def resolve_version(argv: list[str]) -> str:
    """Version from argv, else the pinned serving version.

    Defaulting to the pin means the command is a no-op repeat after a
    completed promotion instead of a second, different transition.
    """
    if len(argv) > 1 and argv[1].strip():
        return argv[1].strip()
    return str(load_config()["api"]["v2_pinned_version"])


def main() -> int:
    try:
        cfg = load_config()
        tracking_uri = os.environ.get(
            "MLFLOW_TRACKING_URI",
            str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]),
        )
        mlflow.set_tracking_uri(tracking_uri)
        version = resolve_version(sys.argv)
        client = MlflowClient()
        client.transition_model_version_stage(
            name=REGISTERED_MODEL_NAME,
            version=version,
            stage="Production",
            archive_existing_versions=True,
        )
    except Exception as exc:
        print(f"PROMOTION ERROR: {exc}")
        return 1
    print(
        f"PROMOTED {REGISTERED_MODEL_NAME} version={version} stage=Production "
        "(previous versions archived, still resolvable for rollback)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
