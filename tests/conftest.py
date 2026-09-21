"""Shared Wave 0 fixtures for Phase 2 training/registry tests.

Provides a 40-row synthetic CKD-shaped fixture plus a tmp MLflow
tracking-URI fixture. Never touches real data/ or real mlruns/.
"""
import mlflow
import pandas as pd
import pytest

from src.preprocessing.preprocess import get_column_lists

NUMERIC_COLS, CATEGORICAL_COLS = get_column_lists()


@pytest.fixture
def synthetic_ckd_df():
    n = 40
    data = {col: [float(i % 5) for i in range(n)] for col in NUMERIC_COLS}
    for col in CATEGORICAL_COLS:
        data[col] = ["yes" if i % 2 == 0 else "no" for i in range(n)]
    data["classification"] = [
        "ckd" if i % 2 == 0 else "notckd" for i in range(n)
    ]
    df = pd.DataFrame(data)
    df.loc[0, NUMERIC_COLS[0]] = None
    df.loc[1, CATEGORICAL_COLS[0]] = None
    return df


@pytest.fixture
def tmp_mlflow_store(tmp_path, monkeypatch):
    """Point the MLflow tracking URI at tmp_path (never real mlruns/)."""
    uri = str(tmp_path / "mlruns")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    mlflow.set_tracking_uri(uri)
    yield uri
    mlflow.set_tracking_uri(uri)
