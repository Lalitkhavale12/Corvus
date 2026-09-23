"""Shared Wave 0 fixtures for Phase 2 training/registry tests.

Provides a 40-row synthetic CKD-shaped fixture plus a tmp MLflow
tracking-URI fixture. Never touches real data/ or real mlruns/.
"""
import csv
import io

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


# Phase 3 Wave 0 fixtures: API request shapes for tests/test_api.py (03-01).
# Valid categorical literals verified against the 400-row raw source
# (03-RESEARCH.md 24-field schema table); never real data/ or real Postgres.
_VALID_CATEGORICALS = {
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


@pytest.fixture
def synthetic_ckd_request():
    """One valid 24-field /predict body; rc None exercises the imputer path."""
    request = {col: 1.0 for col in NUMERIC_COLS}
    request["rc"] = None
    for col in CATEGORICAL_COLS:
        request[col] = _VALID_CATEGORICALS[col]
    return request


@pytest.fixture
def synthetic_batch_csv(synthetic_ckd_request):
    """CSV text of 3 valid rows under the 24-column header for /batch_predict."""
    header = list(NUMERIC_COLS) + list(CATEGORICAL_COLS)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header)
    writer.writeheader()
    for _ in range(3):
        writer.writerow(
            {k: ("" if v is None else v) for k, v in synthetic_ckd_request.items()}
        )
    return buf.getvalue()


def _batch_csv_from_rows(rows: list[dict]) -> str:
    """Render request dicts as CSV text under the exact 24-column header."""
    header = list(NUMERIC_COLS) + list(CATEGORICAL_COLS)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return buf.getvalue()


@pytest.fixture
def valid_batch_csv(synthetic_ckd_request):
    """CSV text of 5 clean rows under the exact 24-column header."""
    return _batch_csv_from_rows([dict(synthetic_ckd_request) for _ in range(5)])


@pytest.fixture
def bad_row_batch_csv(synthetic_ckd_request):
    """5-row CSV whose 3rd data row carries an invalid rbc value (D-08)."""
    rows = [dict(synthetic_ckd_request) for _ in range(5)]
    rows[2]["rbc"] = "ripe"
    return _batch_csv_from_rows(rows)
