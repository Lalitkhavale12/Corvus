"""Claim 5: drift monitoring, five retrain triggers, champion/challenger.

Schedule: daily at 02:00 UTC.

Shape of the run::

    gather_evidence -> decide_retrain --(retrain)--> retrain_challenger -> compare_with_champion -> report
                                     \\--(skip)----> skip_retraining

``gather_evidence`` collects whatever evidence exists (drift report inputs,
labelled-batch ROC-AUC, production row volume, champion age, operator
request); every missing input is reported as "not fired" with its reason.
``decide_retrain`` branches on the verdict from
``src.monitoring.retrain_triggers``; the retrain task calls the real trainer,
so a fire produces a new registered MLflow version. ``compare_with_champion``
then applies ``src.model_promotion.decide_promotion``.

Promotion stops at a recorded recommendation: the decision is written to
``reports/retrain/`` and tagged on the challenger run, and pinning stays a
one-line ``api.v2_pinned_version`` change. The API mounts ``config/`` read-only
in the container, so an automatic write would fail there anyway, and D-04
keeps the serving pin a reviewed change.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator

# The DAG lives at <repo>/airflow/dags/, so the repo root is two levels up.
# CORVUS_PROJECT_ROOT overrides when Airflow mounts the project elsewhere.
PROJECT_ROOT = Path(os.environ.get("CORVUS_PROJECT_ROOT") or Path(__file__).resolve().parents[2])
for _path in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from src.monitoring.retrain_triggers import (  # noqa: E402
    DEFAULT_MIN_NEW_ROWS,
    DEFAULT_ROC_FLOOR,
    DEFAULT_SCHEDULE_DAYS,
    evaluate_triggers,
)
from src.model_promotion import decide_promotion  # noqa: E402
from src.monitoring.drift import (  # noqa: E402
    check_drift_thresholds,
    detect_data_drift,
    load_config_section,
)
from src.utils.config import load_config  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

log = get_logger()

REPORT_DIR = PROJECT_ROOT / "reports" / "retrain"
DRIFT_REPORT_DIR = PROJECT_ROOT / "reports" / "drift"
LABELLED_BATCH = REPORT_DIR / "labelled_batch.csv"
#: Production row count as of the last retrain, so the volume trigger can
#: measure growth instead of total traffic.
ROW_BASELINE = REPORT_DIR / "row_baseline.json"

default_args = {
    "owner": "corvus-team",
    "depends_on_past": False,
    "email": ["alerts@corvus.io"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": 300,
}

dag = DAG(
    "corvus_drift_retrain",
    default_args=default_args,
    description="Five retrain triggers, real retrain, champion/challenger verdict",
    schedule="0 2 * * *",
    start_date=datetime.now(timezone.utc) - timedelta(days=1),
    catchup=False,
    max_active_runs=1,
    tags=["drift", "retrain", "ml", "production"],
)


# ---------------------------------------------------------------------------
# Evidence gathering (each helper degrades to None, never to a fake pass)
# ---------------------------------------------------------------------------

def _champion_age_days() -> float | None:
    """Age of the pinned serving version, in days."""
    from mlflow.tracking import MlflowClient

    config = load_config()
    version = str(config["api"].get("v2_pinned_version", "") or "").strip()
    if not version:
        return None
    try:
        client = MlflowClient()
        model = client.get_model_version("corvus-ckd", version)
    except Exception as exc:  # registry unreachable
        log.warning(f"champion age unavailable for v{version}: {exc}")
        return None
    created = datetime.fromtimestamp(model.creation_timestamp / 1000, tz=timezone.utc)
    return (datetime.now(timezone.utc) - created).total_seconds() / 86400.0


def _recent_production_rows(limit: int = 5000):
    """Most recent logged v2 requests, or None when the DB is unreachable."""
    import pandas as pd
    from sqlalchemy import create_engine, text

    from api.db import get_database_url
    from src.preprocessing.preprocess_nhanes import get_nhanes_column_lists

    url = os.environ.get("DATABASE_URL") or get_database_url()
    if not url:
        return None
    numeric_cols, categorical_cols = get_nhanes_column_lists()
    columns = [c for c in numeric_cols + categorical_cols]
    try:
        engine = create_engine(url)
        query = text(
            f"SELECT {', '.join(columns)} FROM predictions_v2 "
            f"ORDER BY id DESC LIMIT {int(limit)}"
        )
        with engine.connect() as conn:
            frame = pd.read_sql(query, conn)
    except Exception as exc:
        log.warning(f"production rows unavailable: {exc}")
        return None
    return frame if len(frame) else None


def _reference_frame():
    """Training split the champion was fitted from, or None."""
    import pandas as pd

    processed = Path(load_config()["data"]["processed_dir"])
    for name in ("train_raw.csv", "train.csv"):
        path = processed / name
        if path.exists():
            return pd.read_csv(path)
    return None


def _labelled_roc_auc() -> float | None:
    """Champion ROC-AUC on a labelled batch, if someone scored one.

    The batch must already carry ``y_true`` and ``y_proba`` (an offline
    scoring job produces it); the DAG deliberately does not load the model
    just to score, so a missing batch is reported, not guessed.
    """
    import pandas as pd
    from sklearn.metrics import roc_auc_score

    if not LABELLED_BATCH.exists():
        return None
    try:
        frame = pd.read_csv(LABELLED_BATCH)
        return float(roc_auc_score(frame["y_true"], frame["y_proba"]))
    except Exception as exc:
        log.warning(f"labelled batch unusable: {exc}")
        return None


def _production_row_count() -> int | None:
    from sqlalchemy import create_engine, text

    from api.db import get_database_url

    url = os.environ.get("DATABASE_URL") or get_database_url()
    if not url:
        return None
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            return int(
                conn.execute(text("SELECT COUNT(*) FROM predictions_v2")).scalar() or 0
            )
    except Exception as exc:
        log.warning(f"row count unavailable: {exc}")
        return None


def _new_rows_since_retrain() -> int | None:
    """Production rows added since the last retrain.

    The first run has no baseline to compare against, so it records one and
    reports "unknown" instead of pretending the whole table is new traffic.
    """
    total = _production_row_count()
    if total is None:
        return None
    if not ROW_BASELINE.exists():
        ROW_BASELINE.parent.mkdir(parents=True, exist_ok=True)
        ROW_BASELINE.write_text(json.dumps({"rows": total}), encoding="utf-8")
        log.info(f"recorded row baseline at {total}")
        return None
    try:
        baseline = int(json.loads(ROW_BASELINE.read_text(encoding="utf-8"))["rows"])
    except Exception as exc:
        log.warning(f"row baseline unreadable: {exc}")
        return None
    return max(total - baseline, 0)


def gather_evidence(**context) -> dict:
    """Collect every trigger input and the drift verdict."""
    retrain_cfg = load_config_section("retrain")
    drift_result = None

    reference = _reference_frame()
    current = _recent_production_rows()
    if reference is not None and current is not None:
        numeric_cols = load_config()["data"]["numeric_cols"]
        categorical_cols = load_config()["data"]["categorical_cols"]
        common = [
            c
            for c in numeric_cols + categorical_cols
            if c in reference.columns and c in current.columns
        ]
        if common:
            raw_drift = detect_data_drift(
                reference_data=reference,
                current_data=current,
                column_names=common,
                output_path=DRIFT_REPORT_DIR / "drift_report.html",
            )
            drift_result = {
                "data_drift": raw_drift,
                "drift_check": check_drift_thresholds(
                    raw_drift,
                    drift_threshold=float(retrain_cfg.get("drift_threshold", 0.3)),
                ),
            }
        else:
            log.warning("reference and production rows share no model features")

    manual = bool((context.get("dag_run").conf or {}).get("force_retrain", False))
    verdict = evaluate_triggers(
        days_since_promotion=_champion_age_days(),
        schedule_days=int(retrain_cfg.get("schedule_days", DEFAULT_SCHEDULE_DAYS)),
        drift_result=drift_result,
        labelled_roc_auc=_labelled_roc_auc(),
        roc_floor=float(retrain_cfg.get("roc_floor", DEFAULT_ROC_FLOOR)),
        new_rows_since_retrain=_new_rows_since_retrain(),
        min_new_rows=int(retrain_cfg.get("min_new_rows", DEFAULT_MIN_NEW_ROWS)),
        manual_requested=manual,
    )

    for name, check in verdict["checks"].items():
        log.info(f"trigger[{name}] fired={check['fired']} :: {check['detail']}")
    context["task_instance"].xcom_push(key="trigger_verdict", value=verdict)
    return verdict


def decide_retrain(**context) -> str:
    """Branch: retrain when any trigger fired, otherwise skip."""
    verdict = context["task_instance"].xcom_pull(
        key="trigger_verdict", task_ids="gather_evidence"
    ) or {}
    if verdict.get("retrain"):
        log.info(f"retraining: {', '.join(verdict.get('fired_triggers', []))}")
        return "retrain_challenger"
    log.info("no trigger fired; skipping retraining")
    return "skip_retraining"


def retrain_challenger(**context) -> dict:
    """Fit a challenger exactly the way ``train_nhanes.main`` does, then
    register it and read its metrics back from the run record."""
    from mlflow.tracking import MlflowClient

    from src.training.train_nhanes import (
        REGISTERED_MODEL_NAME,
        load_native_frame,
        run_experiment_native,
        select_by_cv,
        split_native,
        sweep_native,
    )

    X, y, numeric_cols, categorical_cols, cycle = load_native_frame()
    X_dev, _X_hold, y_dev, _y_hold = split_native(X, y, cycle)
    cv_results = sweep_native(X_dev, y_dev, numeric_cols, categorical_cols)
    for name, cv in cv_results.items():
        log.info(f"native-{name} cv_mean_auc={cv['mean_auc']:.4f} cv_std={cv['std_auc']:.4f}")
    winner = select_by_cv(cv_results)
    result = run_experiment_native(winner, cv_stats=cv_results[winner])
    run_id = result["run_id"]

    client = MlflowClient()
    logged = client.get_run(run_id).data.metrics
    versions = client.search_model_versions(f"run_id='{run_id}'")
    version = str(versions[0].version) if versions else None

    payload = {
        "run_id": run_id,
        "model": winner,
        "version": version,
        "metrics": {
            "roc_auc": logged.get("holdout_roc_auc"),
            "pr_auc": logged.get("holdout_pr_auc"),
            "precision": logged.get("precision"),
            "recall": logged.get("recall"),
        },
    }

    # A retrain resets the volume baseline; the next run measures growth
    # from here rather than counting the whole table again.
    total = _production_row_count()
    if total is not None:
        ROW_BASELINE.parent.mkdir(parents=True, exist_ok=True)
        ROW_BASELINE.write_text(json.dumps({"rows": total}), encoding="utf-8")

    context["task_instance"].xcom_push(key="challenger", value=payload)
    log.info(
        f"challenger native-{winner} run {run_id} v{version} "
        f"ROC-AUC {payload['metrics']['roc_auc']}"
    )
    return payload


def compare_with_champion(**context) -> dict:
    """Apply the promotion policy and record the verdict."""
    from mlflow.tracking import MlflowClient

    challenger = context["task_instance"].xcom_pull(
        key="challenger", task_ids="retrain_challenger"
    )
    if not challenger:
        raise ValueError("no challenger run to compare")

    client = MlflowClient()
    config = load_config()
    champion_version = str(config["api"].get("v2_pinned_version", "") or "").strip()
    champion = None
    if champion_version:
        model = client.get_model_version("corvus-ckd", champion_version)
        run_metrics = client.get_run(model.run_id).data.metrics
        champion = {
            "version": champion_version,
            "run_id": model.run_id,
            "roc_auc": run_metrics.get("holdout_roc_auc", run_metrics.get("roc_auc")),
            "pr_auc": run_metrics.get("holdout_pr_auc", run_metrics.get("pr_auc")),
        }

    verdict = decide_promotion(champion, challenger["metrics"])
    verdict.update(
        {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "challenger_run_id": challenger["run_id"],
            "challenger_version": challenger.get("version"),
            "challenger_model": challenger.get("model"),
            "triggers": (
                context["task_instance"].xcom_pull(
                    key="trigger_verdict", task_ids="gather_evidence"
                )
                or {}
            ).get("fired_triggers", []),
        }
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = REPORT_DIR / f"decision-{stamp}.json"
    out.write_text(json.dumps(verdict, indent=2, default=str), encoding="utf-8")

    client.set_tag(challenger["run_id"], "promotion_recommended", str(verdict["promote"]).lower())
    client.set_tag(challenger["run_id"], "promotion_reason", verdict["reason"])

    log.info(f"promotion recommended={verdict['promote']} :: {verdict['reason']}")
    log.info(f"decision written to {out}")
    log.info(
        "pin manually by setting api.v2_pinned_version in config/config.yaml "
        "to the challenger version; the registry keeps the previous version "
        "for rollback"
    )
    context["task_instance"].xcom_push(key="promotion", value=verdict)
    return verdict


def skip_retraining(**context) -> dict:
    verdict = context["task_instance"].xcom_pull(
        key="trigger_verdict", task_ids="gather_evidence"
    ) or {}
    reasons = {
        name: check["detail"] for name, check in (verdict.get("checks") or {}).items()
    }
    log.info(f"retraining skipped: {json.dumps(reasons, default=str)}")
    return {"retrained": False, "reasons": reasons}


gather_evidence_task = PythonOperator(
    task_id="gather_evidence", python_callable=gather_evidence, dag=dag
)
decide_retrain_task = BranchPythonOperator(
    task_id="decide_retrain", python_callable=decide_retrain, dag=dag
)
retrain_task = PythonOperator(
    task_id="retrain_challenger", python_callable=retrain_challenger, dag=dag
)
compare_task = PythonOperator(
    task_id="compare_with_champion", python_callable=compare_with_champion, dag=dag
)
skip_task = PythonOperator(
    task_id="skip_retraining", python_callable=skip_retraining, dag=dag
)

gather_evidence_task >> decide_retrain_task
decide_retrain_task >> retrain_task >> compare_task
decide_retrain_task >> skip_task
