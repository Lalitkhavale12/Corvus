"""
Drift detection for Corvus CKD Prediction (Phase 5).

Uses Evidently AI to detect data drift between reference (training) and
current (production) datasets. Generates HTML reports and JSON summaries.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset

from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()


def load_config_section(key: str) -> dict:
    """Load a section from the project config."""
    cfg = load_config()
    return cfg.get(key, {})


def detect_data_drift(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    column_names: list[str],
    output_path: str | Path = None,
) -> dict[str, Any]:
    """
    Run drift detection between reference and current datasets.

    Args:
        reference_data: Reference (training) dataframe
        current_data: Current (production) dataframe
        column_names: Column names to check for drift
        output_path: Path to save HTML report

    Returns:
        Dictionary with drift detection results
    """
    log.info("Starting data drift detection...")

    report = Report(metrics=[DataDriftPreset()])

    report.run(
        reference_data=reference_data[column_names],
        current_data=current_data[column_names],
    )

    result = report.as_dict()

    # Extract drift metrics
    drift_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "dataset_drift": report.as_dict()["metrics"][0]["value"]["dataset_drift"],
        "n_features": report.as_dict()["metrics"][0]["value"]["n_features"],
        "n_drifted_features": report.as_dict()["metrics"][0]["value"]["n_drifted_features"],
        "share_drifted_features": report.as_dict()["metrics"][0]["value"]["share_drifted_features"],
        "feature_drift_details": report.as_dict()["metrics"][0]["value"]["drift_by_columns"],
    }

    log.info(
        f"Drift detection complete: {drift_results['n_drifted_features']}/{drift_results['n_features']} "
        f"features drifted ({drift_results['share_drifted_features']:.2%})"
    )

    # Save HTML report if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.save_html(str(output_path))
        log.info(f"Drift report saved to {output_path}")

    # Save JSON summary
    summary_path = Path(output_path).parent / "drift_summary.json" if output_path else Path("drift_summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(drift_results, f, indent=2)
    log.info(f"Drift summary saved to {summary_path}")

    return drift_results


def detect_target_drift(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    target_column: str,
    output_path: str | Path = None,
) -> dict[str, Any]:
    """
    Run drift detection on target variable (predictions vs actuals).

    Args:
        reference_data: Reference (training) dataframe
        current_data: Current (production) dataframe
        target_column: Name of the target column
        output_path: Path to save HTML report

    Returns:
        Dictionary with drift detection results
    """
    log.info("Starting target drift detection...")

    report = Report(metrics=[TargetDriftPreset()])

    report.run(
        reference_data=reference_data,
        current_data=current_data,
        column_mapping=None,  # Will auto-detect target column
    )

    result = report.as_dict()

    drift_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "target_drift_detected": report.as_dict()["metrics"][0]["value"].get("drift_detected", False),
        "drift_score": report.as_dict()["metrics"][0]["value"].get("drift_score", 0.0),
        "stat_test_name": report.as_dict()["metrics"][0]["value"].get("stat_test_name", ""),
        "stat_test_value": report.as_dict()["metrics"][0]["value"].get("stat_test_value", 0.0),
        "stat_test_threshold": report.as_dict()["metrics"][0]["value"].get("stat_test_threshold", 0.0),
    }

    log.info(
        f"Target drift detection complete: drift_detected={drift_results['target_drift_detected']}, "
        f"drift_score={drift_results['drift_score']:.4f}"
    )

    # Save HTML report if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.save_html(str(output_path))
        log.info(f"Target drift report saved to {output_path}")

    return drift_results


def check_drift_thresholds(
    data_drift_result: dict,
    target_drift_result: dict | None = None,
    drift_threshold: float = 0.3,
    target_drift_threshold: float = 0.3,
) -> dict[str, bool]:
    """
    Check if drift exceeds thresholds.

    Args:
        data_drift_result: Data drift detection result
        target_drift_result: Target drift detection result (optional)
        drift_threshold: Threshold for data drift share
        target_drift_threshold: Threshold for target drift score

    Returns:
        Dictionary with drift check results
    """
    share_drifted = data_drift_result.get("share_drifted_features", 0.0)

    # Only a share of drifted features counts as dataset drift. Firing on
    # ``n_drifted > 0`` would trigger on any single column out of 23, which
    # is the normal state of a live clinical feed, not a drift event.
    data_drift_exceeded = share_drifted > drift_threshold

    target_drift_exceeded = False
    if target_drift_result:
        target_drift_exceeded = (
            target_drift_result.get("target_drift_detected", False)
            or target_drift_result.get("drift_score", 0.0) > target_drift_threshold
        )

    result = {
        "data_drift_exceeded": data_drift_exceeded,
        "target_drift_exceeded": target_drift_exceeded,
        "drift_detected": data_drift_exceeded or target_drift_exceeded,
        "share_drifted_features": share_drifted,
        "drift_threshold": drift_threshold,
        "target_drift_score": target_drift_result.get("drift_score", 0.0) if target_drift_result else 0.0,
        "target_drift_threshold": target_drift_threshold,
    }

    log.info(
        f"Drift check complete: data_drift_exceeded={data_drift_exceeded}, "
        f"target_drift_exceeded={target_drift_exceeded}, "
        f"drift_detected={result['drift_detected']}"
    )

    return result


def generate_drift_report(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    column_names: list[str],
    target_column: str | None = None,
    output_dir: str | Path = "reports/drift",
) -> dict[str, Any]:
    """
    Generate a complete drift detection report.

    Args:
        reference_data: Reference (training) dataframe
        current_data: Current (production) dataframe
        column_names: Column names to check for drift
        target_column: Target column name (optional)
        output_dir: Output directory for reports

    Returns:
        Dictionary with all drift detection results
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Data drift detection
    data_drift_result = detect_data_drift(
        reference_data=reference_data,
        current_data=current_data,
        column_names=column_names,
        output_path=output_path / "data_drift_report.html",
    )

    # Target drift detection (if target column provided)
    target_drift_result = None
    if target_column and target_column in current_data.columns:
        target_drift_result = detect_target_drift(
            reference_data=reference_data,
            current_data=current_data,
            target_column=target_column,
            output_path=output_path / "target_drift_report.html",
        )

    # Check thresholds
    check_result = check_drift_thresholds(
        data_drift_result=data_drift_result,
        target_drift_result=target_drift_result,
    )

    # Combined result
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "data_drift": data_drift_result,
        "target_drift": target_drift_result,
        "drift_check": check_result,
        "reports": {
            "data_drift_report": str(output_path / "data_drift_report.html"),
            "target_drift_report": str(output_path / "target_drift_report.html")
            if target_drift_result else None,
            "drift_summary": str(output_path / "drift_summary.json"),
        },
    }

    # Save combined result
    result_path = output_path / "drift_report.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    log.info(f"Drift report saved to {result_path}")
    log.info(f"Drift detected: {result['drift_check']['drift_detected']}")

    return result