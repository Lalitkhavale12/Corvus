"""The five retraining triggers of Claim 5, as pure functions.

The Airflow DAG only gathers evidence and wires branches; every decision
lives here so it can be tested without an Airflow scheduler, a database or
a model registry.

Trigger types:

``schedule``     champion is older than ``retrain.schedule_days``
``drift``        Evidently found more feature drift than the configured share
``performance``  champion ROC-AUC on a freshly labelled batch fell below the floor
``data_volume``  enough new production rows have accumulated since the last retrain
``manual``       an operator asked for it (DAG conf or a flag file)

Every trigger reports why it did or did not fire, so a skipped retrain is
explained in the DAG log instead of being silent.
"""

from __future__ import annotations

from typing import Any

TRIGGER_TYPES: tuple[str, ...] = (
    "schedule",
    "drift",
    "performance",
    "data_volume",
    "manual",
)

#: Champion older than this many days retrains on the schedule trigger.
DEFAULT_SCHEDULE_DAYS = 30
#: New prediction rows since the last retrain that justify one.
DEFAULT_MIN_NEW_ROWS = 500
#: Champion ROC-AUC on a labelled batch below which retraining is forced.
DEFAULT_ROC_FLOOR = 0.80


def _check(
    fired: bool, detail: str, evidence: Any = None
) -> dict[str, Any]:
    return {"fired": bool(fired), "detail": detail, "evidence": evidence}


def evaluate_triggers(
    *,
    days_since_promotion: float | None = None,
    schedule_days: int = DEFAULT_SCHEDULE_DAYS,
    drift_result: dict | None = None,
    labelled_roc_auc: float | None = None,
    roc_floor: float = DEFAULT_ROC_FLOOR,
    new_rows_since_retrain: int | None = None,
    min_new_rows: int = DEFAULT_MIN_NEW_ROWS,
    manual_requested: bool = False,
) -> dict[str, Any]:
    """Evaluate all five triggers and say whether any of them fires.

    ``None`` for an input means "no evidence available", which is reported as
    not fired with the reason, never as a pass.
    """
    checks: dict[str, dict[str, Any]] = {}

    if days_since_promotion is None:
        checks["schedule"] = _check(False, "champion age unknown")
    else:
        due = days_since_promotion >= schedule_days
        checks["schedule"] = _check(
            due,
            f"champion is {days_since_promotion:.1f}d old "
            f"(due at {schedule_days}d)",
            days_since_promotion,
        )

    if drift_result is None:
        checks["drift"] = _check(False, "no drift report available")
    else:
        drift_check = drift_result.get("drift_check", drift_result)
        drifted = bool(drift_check.get("drift_detected", False))
        share = drift_check.get("share_drifted_features")
        detail = "drift threshold not exceeded"
        if drifted:
            detail = (
                f"drifted share {share:.2%}" if isinstance(share, (int, float))
                else "drift threshold exceeded"
            )
        checks["drift"] = _check(drifted, detail, share)

    if labelled_roc_auc is None:
        checks["performance"] = _check(False, "no labelled batch scored")
    else:
        degraded = labelled_roc_auc < roc_floor
        checks["performance"] = _check(
            degraded,
            f"champion ROC-AUC {labelled_roc_auc:.4f} on labelled batch "
            f"(floor {roc_floor:.2f})",
            labelled_roc_auc,
        )

    if new_rows_since_retrain is None:
        checks["data_volume"] = _check(False, "production row count unknown")
    else:
        enough = new_rows_since_retrain >= min_new_rows
        checks["data_volume"] = _check(
            enough,
            f"{new_rows_since_retrain} new rows since last retrain "
            f"(needs {min_new_rows})",
            new_rows_since_retrain,
        )

    checks["manual"] = _check(
        manual_requested,
        "operator requested a retrain" if manual_requested else "not requested",
    )

    fired = [name for name, result in checks.items() if result["fired"]]
    return {
        "retrain": bool(fired),
        "fired_triggers": fired,
        "checks": checks,
    }
