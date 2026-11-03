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
from src.preprocessing.preprocess_nhanes import QUARANTINE_11, get_nhanes_column_lists

NUMERIC_COLS, CATEGORICAL_COLS = get_column_lists()
NHANES_NUMERIC_COLS, NHANES_CATEGORICAL_COLS = get_nhanes_column_lists()


@pytest.fixture
def synthetic_ckd_df():
    n = 40
    data = {col: [float(i % 5) for i in range(n)] for col in NUMERIC_COLS}
    for col in CATEGORICAL_COLS:
        data[col] = ["yes" if i % 2 == 0 else "no" for i in range(n)]
    data["classification"] = ["ckd" if i % 2 == 0 else "notckd" for i in range(n)]
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


# Phase 7 Wave 0 fixture: NHANES-native synthetic frame for
# tests/test_nhanes_training.py (07-01). 60 rows over the 16+5 native
# columns plus a 0/1 ckd label at ~17 percent positive (10/60) plus all
# 11 quarantine columns with dummy values so the abort path is testable.
# Purely synthetic with tmp isolation; never reads the real derived CSV.
@pytest.fixture
def synthetic_nhanes_df():
    n = 60
    data = {col: [float(i % 5) for i in range(n)] for col in NHANES_NUMERIC_COLS}
    for col in NHANES_CATEGORICAL_COLS:
        data[col] = [f"{col}_a" if i % 2 == 0 else f"{col}_b" for i in range(n)]
    data["ckd"] = [1 if i % 6 == 0 else 0 for i in range(n)]
    for col in QUARANTINE_11:
        data[col] = [0.0 for _ in range(n)]
    df = pd.DataFrame(data)
    df.loc[0, NHANES_NUMERIC_COLS[0]] = None
    df.loc[1, NHANES_CATEGORICAL_COLS[0]] = None
    return df


# ---------------------------------------------------------------------------
# Phase 8-03: authenticated test client fixture
# ---------------------------------------------------------------------------

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import api.db as db_mod  # noqa: E402
from api.app import app  # noqa: E402


class _StubEstimator:  # noqa: E402
    n_features_in_ = 4

    def predict(self, X):
        return [1] * len(X)

    def predict_proba(self, X):
        return [[0.2, 0.8]] * len(X)


class _StubPipeline:  # noqa: E402
    def transform(self, df):
        return np.zeros((len(df), 4))


@pytest.fixture
def auth_client(monkeypatch):
    """TestClient with auth headers and stubbed model loader.

    Creates a test user in a scratch SQLite DB, mints a JWT, and yields an
    authenticated TestClient. The engine is disposed after the test to release
    file locks on Windows.
    """
    import os
    import tempfile
    from pathlib import Path

    import src.database as _db_module  # noqa: E402

    _db_module._engine = None  # type: ignore[attr-defined]
    _db_module._SessionLocal = None  # type: ignore[attr-defined]

    # Kept in the OS temp dir so test runs never litter the repo root.
    db_path = Path(tempfile.gettempdir()) / "corvus_test_auth_client.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    try:
        if db_path.exists():
            db_path.unlink()
    except PermissionError:
        pass  # File locked by a previous test; tables are idempotent

    from src.database import Base, get_engine, get_session_local  # noqa: E402
    from src.auth.auth import create_user  # noqa: E402
    from src.auth.schemas import UserRegister  # noqa: E402
    from src.auth.security import create_access_token  # noqa: E402

    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    SessionLocal = get_session_local()
    db = SessionLocal()
    user = create_user(
        db,
        UserRegister(email="authtest@example.com", password="securepass123", role="patient"),
    )
    if user is None:
        # User already exists from a previous test run; fetch their id
        from src.auth.auth import get_user_by_email  # noqa: E402

        user = get_user_by_email(db, "authtest@example.com")
    user_id = user.id
    user_role = user.role
    db.commit()
    db.close()

    token = create_access_token({"sub": str(user_id), "role": user_role})

    monkeypatch.setattr(
        "api.app.model_loader.load_serving_artifacts",
        lambda version: (_StubEstimator(), _StubPipeline(), "test-run-id", "9"),
    )

    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        yield client

    engine.dispose()
    _db_module._engine = None
    _db_module._SessionLocal = None
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass
