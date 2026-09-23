"""Phase 3 API contract tests (03-02 tracer: FR-4.1 -> FR-4.4, FR-5.2).

No live server, no real mlruns, no real Postgres: the autouse
``_serving_stub`` fixture points the loader at stub artifacts, the DB
session at a MagicMock, table creation at a no-op, and DATABASE_URL at a
dummy value (never connected — the session is mocked). The 503 and
create_tables tests opt out of the DB-available setup explicitly.
"""
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.db as db_mod
from api.app import COLUMN_ORDER, MAX_BATCH_BYTES, app
from api.db import PredictionLog

_REAL_CREATE_TABLES = db_mod.create_tables


class _StubEstimator:
    n_features_in_ = 4

    def predict(self, X):
        return [1] * len(X)

    def predict_proba(self, X):
        return [[0.2, 0.8]] * len(X)


class _StubPipeline:
    def transform(self, df):
        return np.zeros((len(df), 4))


@pytest.fixture
def mock_session(monkeypatch):
    """Fresh mocked SQLAlchemy session per test; app calls db.Session()."""
    session = MagicMock()
    monkeypatch.setattr(db_mod, "Session", MagicMock(return_value=session))
    return session


@pytest.fixture(autouse=True)
def _serving_stub(monkeypatch, mock_session):  # noqa: ARG001
    """Serve stub artifacts with a mocked log store (never real backends)."""
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/test"
    )
    monkeypatch.setattr(db_mod, "create_tables", lambda *a, **k: True)
    monkeypatch.setattr(
        "api.app.model_loader.load_serving_artifacts",
        lambda version: (_StubEstimator(), _StubPipeline(), "test-run-id", "9"),
    )


def test_predict_returns_versioned_prediction(synthetic_ckd_request):
    with TestClient(app) as client:
        resp = client.post("/predict", json=synthetic_ckd_request)
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_version"] == "9"
    assert "prediction" in body and "probability" in body


def test_predict_missing_field_is_422(synthetic_ckd_request):
    synthetic_ckd_request.pop("age")
    with TestClient(app) as client:
        resp = client.post("/predict", json=synthetic_ckd_request)
    assert resp.status_code == 422


def test_predict_bad_literal_is_422(synthetic_ckd_request):
    synthetic_ckd_request["rbc"] = "green"
    with TestClient(app) as client:
        resp = client.post("/predict", json=synthetic_ckd_request)
    assert resp.status_code == 422


def test_predict_null_numeric_uses_imputer(synthetic_ckd_request):
    # rc None must flow through the fitted pipeline imputers (D-05), not 422.
    assert synthetic_ckd_request["rc"] is None
    with TestClient(app) as client:
        resp = client.post("/predict", json=synthetic_ckd_request)
    assert resp.status_code == 200


def test_health_reports_model_version():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "model_version": "9"}


def test_model_info_reports_pinned_version():
    # Pinned-at-startup resolution (D-02): version comes from config/env once,
    # never per-request registry resolution.
    with TestClient(app) as client:
        resp = client.get("/model_info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_name"] == "corvus-ckd"
    assert body["model_version"] == "9"
    assert body["run_id"] == "test-run-id"
    assert body["resolution"] == "pinned-at-startup"


def test_batch_all_or_nothing_names_row_2(synthetic_batch_csv):
    # Corrupt the 2nd data row: whole batch rejects with the offender named.
    lines = synthetic_batch_csv.splitlines()
    bad = lines[2].replace("normal", "green", 1)
    payload = "\n".join([lines[0], lines[1], bad, lines[3]])
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", payload, "text/csv")},
        )
    assert resp.status_code == 422
    assert "2" in resp.json()["detail"]


def test_batch_valid_rows_predict_and_log(synthetic_batch_csv, mock_session):
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", synthetic_batch_csv, "text/csv")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["predictions"]) == 3
    assert body["model_version"] == "9"
    assert mock_session.add.call_count == 3
    assert mock_session.commit.call_count == 1


def test_logged_row_carries_model_version(synthetic_ckd_request, mock_session):
    # Claim 4: the Postgres row carries the same startup-pinned version.
    with TestClient(app) as client:
        resp = client.post("/predict", json=synthetic_ckd_request)
    assert resp.status_code == 200
    logged = mock_session.add.call_args[0][0]
    assert isinstance(logged, PredictionLog)
    for col in COLUMN_ORDER:
        assert getattr(logged, col) == synthetic_ckd_request[col]
    assert logged.prediction == 1
    assert logged.probability == 0.8
    assert logged.model_version == "9"
    assert mock_session.commit.call_count == 1


def test_predict_db_unavailable_returns_503(synthetic_ckd_request, monkeypatch):
    # Fail closed (D-03): unset DATABASE_URL serves 503 naming DATABASE_URL,
    # never silent no-log serving and never SQLite.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        resp = client.post("/predict", json=synthetic_ckd_request)
    assert resp.status_code == 503
    assert "DATABASE_URL" in resp.json()["detail"]


def test_create_tables_unset_returns_false(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db_mod, "create_tables", _REAL_CREATE_TABLES)
    assert db_mod.create_tables() is False


def test_create_tables_unreachable_fails_loud(monkeypatch):
    # T-03-06: a configured-but-unreachable store retries then raises.
    monkeypatch.setattr(db_mod, "create_tables", _REAL_CREATE_TABLES)

    def _boom(*a, **k):
        raise ConnectionError("db down")

    monkeypatch.setattr(db_mod, "create_engine", _boom)
    monkeypatch.setattr("api.db.time.sleep", lambda *a, **k: None)
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        db_mod.create_tables()


def test_batch_valid_returns_count_and_row_items(valid_batch_csv, mock_session):
    # 5 clean rows: 200 with count 5, per-row items, pinned version, 1 commit.
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", valid_batch_csv, "text/csv")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 5
    assert len(body["predictions"]) == 5
    assert body["model_version"] == "9"
    for i, item in enumerate(body["predictions"], start=1):
        assert item["row"] == i
        assert item["prediction"] == 1
        assert item["probability"] == 0.8
    assert mock_session.add.call_count == 5
    assert mock_session.commit.call_count == 1


def test_batch_bad_row_3_rejects_with_zero_writes(bad_row_batch_csv, mock_session):
    # D-08 all-or-nothing: offender row 3 named, nothing logged.
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", bad_row_batch_csv, "text/csv")},
        )
    assert resp.status_code == 422
    assert "row 3" in resp.json()["detail"]
    assert mock_session.add.call_count == 0
    assert mock_session.commit.call_count == 0


def test_batch_missing_column_is_422(valid_batch_csv):
    # Drop the first column: 422 must name it (exactly-24 per D-07).
    dropped = COLUMN_ORDER[0]
    lines = valid_batch_csv.splitlines()
    payload = "\n".join([",".join(l.split(",")[1:]) for l in lines])
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", payload, "text/csv")},
        )
    assert resp.status_code == 422
    assert dropped in resp.json()["detail"]


def test_batch_oversize_body_is_413(mock_session):
    # T-03-07: bodies over MAX_BATCH_BYTES reject with 413 before parsing.
    payload = "a" * (MAX_BATCH_BYTES + 1)
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", payload, "text/csv")},
        )
    assert resp.status_code == 413
    assert mock_session.add.call_count == 0
    assert mock_session.commit.call_count == 0


def test_batch_extra_columns_warn_ignored(valid_batch_csv, mock_session):
    # T-03-08: unexpected extras are ignored, never fed to the pipeline.
    lines = valid_batch_csv.splitlines()
    payload = "\n".join([lines[0] + ",mystery_col"] + [l + ",zzz" for l in lines[1:]])
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", payload, "text/csv")},
        )
    assert resp.status_code == 200
    assert resp.json()["count"] == 5
    assert mock_session.commit.call_count == 1


def test_batch_logged_rows_carry_full_record(valid_batch_csv, mock_session):
    # D-04: every logged row holds all 24 fields + outcome + version + ts.
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", valid_batch_csv, "text/csv")},
        )
    assert resp.status_code == 200
    assert mock_session.add.call_count == 5
    for call in mock_session.add.call_args_list:
        logged = call[0][0]
        assert isinstance(logged, PredictionLog)
        for col in COLUMN_ORDER:
            assert getattr(logged, col) is not None or col == "rc"
        assert logged.prediction == 1
        assert logged.probability == 0.8
        assert logged.model_version == "9"
        assert logged.created_at is not None


def test_batch_db_unavailable_returns_503(valid_batch_csv, monkeypatch):
    # Fail closed (D-03): unset DATABASE_URL serves 503 naming DATABASE_URL.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        resp = client.post(
            "/batch_predict",
            files={"file": ("batch.csv", valid_batch_csv, "text/csv")},
        )
    assert resp.status_code == 503
    assert "DATABASE_URL" in resp.json()["detail"]
