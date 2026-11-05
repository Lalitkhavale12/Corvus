"""Drift report parsing against the pinned evidently version.

The suite only exercised the pure threshold logic, so the report-dict keys
that ``detect_data_drift`` / ``detect_target_drift`` read went unchecked and
broke on an evidently upgrade. These tests run a real (tiny) report.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("evidently", reason="declared optional at dev time")

from src.monitoring.drift import detect_data_drift, detect_target_drift

COLUMNS = ["age", "bmi", "scr"]


def _frames(seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    reference = pd.DataFrame({c: rng.normal(0, 1, 200) for c in COLUMNS})
    current = pd.DataFrame({c: rng.normal(0, 1, 200) for c in COLUMNS})
    current["bmi"] = current["bmi"] + 6  # one column drifts hard
    return reference, current


def test_data_drift_report_keys_and_one_drifted_column(tmp_path):
    reference, current = _frames()

    result = detect_data_drift(
        reference, current, COLUMNS, output_path=tmp_path / "drift.html"
    )

    assert result["n_features"] == len(COLUMNS)
    assert 0 <= result["n_drifted_features"] <= len(COLUMNS)
    assert 0.0 <= result["share_drifted_features"] <= 1.0
    assert isinstance(result["dataset_drift"], bool)
    assert "bmi" in result["feature_drift_details"]
    assert result["feature_drift_details"]["bmi"]["drift_detected"] is True
    assert (tmp_path / "drift.html").exists()


def test_target_drift_report_keys(tmp_path):
    reference, current = _frames()
    rng = np.random.default_rng(1)
    reference["target"] = (rng.random(len(reference)) < 0.3).astype(int)
    current["target"] = (rng.random(len(current)) < 0.7).astype(int)

    result = detect_target_drift(
        reference, current, "target", output_path=tmp_path / "target_drift.html"
    )

    assert isinstance(result["target_drift_detected"], bool)
    assert isinstance(result["drift_score"], float)
    assert "stat_test_threshold" in result
    assert (tmp_path / "target_drift.html").exists()
