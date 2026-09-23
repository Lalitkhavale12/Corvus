"""Phase 3 - promote corvus-ckd v9 Staging to Production (D-01 first act).

One-shot script: transitions version 9 to Production, archiving nothing new
since Production is empty. Stage mutation is audited by the MLflow registry
and reversible only via an explicit second transition.

Invoked as ``.\\venv\\python.exe scripts/promote_production.py`` from the
project root.
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
PROMOTE_VERSION = "9"


def main() -> int:
    try:
        cfg = load_config()
        tracking_uri = os.environ.get(
            "MLFLOW_TRACKING_URI",
            str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]),
        )
        mlflow.set_tracking_uri(tracking_uri)
        client = MlflowClient()
        client.transition_model_version_stage(
            name=REGISTERED_MODEL_NAME,
            version=PROMOTE_VERSION,
            stage="Production",
            archive_existing_versions=True,
        )
    except Exception as exc:
        print(f"PROMOTION ERROR: {exc}")
        return 1
    print(f"PROMOTED {REGISTERED_MODEL_NAME} version={PROMOTE_VERSION} stage=Production")
    return 0


if __name__ == "__main__":
    sys.exit(main())
