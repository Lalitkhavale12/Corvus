"""Phase 7 - promote a staged NHANES challenger to Production (human gate only).

Mirrors ``scripts/promote_production.py`` exactly, except the version
comes from a required ``--version`` argument instead of a hardcoded
constant, and it must NEVER run without explicit human approval at the
07-02 promotion gate (D-04: no auto-promote, ever). On approval the gate
records the version here; rejection leaves the registry untouched with
the challenger in Staging.

Invoked as ``.\\venv\\python.exe scripts/promote_challenger.py --version 11``
from the project root, only after the gate approves.
"""

import argparse
import os
import sys
from pathlib import Path

# Allow `.\venv\python.exe scripts/promote_challenger.py` from the project
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote a staged corvus-ckd challenger to Production."
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Challenger version the human gate approved (e.g. 11)",
    )
    args = parser.parse_args(argv)
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
            version=str(args.version),
            stage="Production",
            archive_existing_versions=True,
        )
    except Exception as exc:
        print(f"PROMOTION ERROR: {exc}")
        return 1
    print(
        f"PROMOTED {REGISTERED_MODEL_NAME} version={args.version} stage=Production"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
