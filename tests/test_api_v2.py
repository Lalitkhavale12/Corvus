"""Phase 7 v2 serving contract tests (07-03: FR-4.1 -> FR-4.3).

Mirrors the tests/test_api.py stub pattern with a dual-slot serving stub
(v1 loader pinned at 9, v2 loader pinned at 11), a no-op create_tables, a
dummy DATABASE_URL env, and a MagicMock db Session. Never touches real
mlruns/ or Postgres. Covers native validation strictness, fail-closed
unconfigured v2, batch guards, isolated v2 logging, and v1 regression.
"""

import csv
import io
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.db as db_mod
from api import model_loader
from api.app import COLUMN_ORDER, COLUMN_ORDER_V2, MAX_BATCH_BYTES, MAX_BATCH_ROWS, app
from api.db import PredictionLog, PredictionLogV2
from src.preprocessing.preprocess_nhanes import get_nhanes_column_lists
from src.training.train_nhanes import NATIVE_PIPELINE_FILENAME

# Derived from config, not hardcoded: the numeric/categorical split moves
# whenever the native allow-list grows.
_NATIVE_NUMERIC_COLS, _NATIVE_CATEGORICAL_COLS = get_nhanes_column_lists()
NATIVE_NUMERIC = COLUMN_ORDER_V2[: len(_NATIVE_NUMERIC_COLS)]
NATIVE_CATEGORICAL = COLUMN_ORDER_V2[len(_NATIVE_NUMERIC_COLS) :]

_VALID_NATIVE_CATEGORICALS = {
    "RIAGENDR": 1,
    "DMDEDUC2": 1,
    "DIQ010": 1,
}


class _StubEstimator:
    n_features_in_ = 4

    def predict(self, X):
        return [1] * len(X)

    def predict_proba(self, X):
        # Real sklearn always returns a 2-D ndarray; the serving path indexes
        # the positive column, so the stub must carry the same shape.
        return np.tile([0.2, 0.8], (len(X), 1))


class _StubPipeline:
    def transform(self, df):
        return np.zeros((len(df), 4))


@pytest.fixture
def native_request():
    """One valid 21-field /v2/predict body; BMXBMI None exercises imputation."""
    request = {col: 1.0 for col in NATIVE_NUMERIC}
    request["BMXBMI"] = None
    for col in NATIVE_CATEGORICAL:
        request[col] = _VALID_NATIVE_CATEGORICALS[col]
    return request


def _native_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMN_ORDER_V2)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return buf.getvalue()


@pytest.fixture
def native_batch_csv(native_request):
    return _native_csv([dict(native_request) for _ in range(3)])


@pytest.fixture
def mock_session(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(db_mod, "Session", MagicMock(return_value=session))
    return session


@pytest.fixture
def dual_serving_stub(monkeypatch, mock_session):  # noqa: ARG001
    """Dual-slot stub: v1 serves 9, v2 serves 11, log store mocked."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_v2_stub.db")
    monkeypatch.delenv("MODEL_VERSION_V2", raising=False)
    monkeypatch.setattr(db_mod, "create_tables", lambda *a, **k: True)
    monkeypatch.setattr(
        "api.app.model_loader.load_serving_artifacts",
        lambda version: (_StubEstimator(), _StubPipeline(), "run-v9", "9"),
    )
    monkeypatch.setattr(
        "api.app.model_loader.load_v2_artifacts",
        lambda version: (_StubEstimator(), _StubPipeline(), "run-v11", "11"),
    )
    monkeypatch.setattr(
        "api.app.model_loader.resolve_v2_version", lambda: "11"
    )
    monkeypatch.setattr(
        "api.app.model_loader.load_v2_threshold", lambda version: 0.5
    )


@pytest.fixture
def unconfigured_v2_stub(monkeypatch, mock_session):  # noqa: ARG001
    """No challenger pin: every /v2 route must fail closed with 503."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_v2_stub.db")
    monkeypatch.delenv("MODEL_VERSION_V2", raising=False)
    monkeypatch.setattr(db_mod, "create_tables", lambda *a, **k: True)
    monkeypatch.setattr(
        "api.app.model_loader.load_serving_artifacts",
        lambda version: (_StubEstimator(), _StubPipeline(), "run-v9", "9"),
    )
    monkeypatch.setattr("api.app.model_loader.resolve_v2_version", lambda: "")


def test_v2_predict_returns_versioned_prediction(dual_serving_stub, native_request, auth_client):
    resp = auth_client.post("/v2/predict", json=native_request)
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_version"] == "11"
    assert body["prediction"] == 1
    assert body["probability"] == 0.8


def test_v2_threshold_governs_decision(
    dual_serving_stub, native_request, auth_client
):
    # Same 0.8 probability as the default test; only the cut-off moves. If the
    # serving path ignored the threshold this would still return 1. The state
    # slot is set directly because lifespan already ran when the client was
    # built.
    assert auth_client.app.state.v2_threshold == 0.5  # fixture default
    auth_client.app.state.v2_threshold = 0.9
    resp = auth_client.post("/v2/predict", json=native_request)
    assert resp.status_code == 200
    body = resp.json()
    assert body["probability"] == 0.8
    assert body["prediction"] == 0


def test_v2_predict_missing_field_is_422(dual_serving_stub, native_request, auth_client):
    native_request.pop("BMXBMI")
    resp = auth_client.post("/v2/predict", json=native_request)
    assert resp.status_code == 422
    assert "BMXBMI" in resp.text


def test_v2_predict_bad_literal_is_422(dual_serving_stub, native_request, auth_client):
    native_request["RIAGENDR"] = 7
    resp = auth_client.post("/v2/predict", json=native_request)
    assert resp.status_code == 422


def test_v2_predict_null_numeric_uses_imputer(dual_serving_stub, native_request, auth_client):
    # BMXBMI None must flow through the native pipeline imputers, not 422.
    assert native_request["BMXBMI"] is None
    resp = auth_client.post("/v2/predict", json=native_request)
    assert resp.status_code == 200


def test_v2_unconfigured_predict_503(unconfigured_v2_stub, native_request, auth_client):
    # With auth, user is authenticated; no v2 pin → 503 from _require_v2.
    resp = auth_client.post("/v2/predict", json=native_request)
    assert resp.status_code == 503
    assert "v2_pinned_version" in resp.json()["detail"]


def test_v2_model_info_reports_v2_version(dual_serving_stub):
    with TestClient(app) as client:
        resp = client.get("/v2/model_info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_name"] == "corvus-ckd"
    assert body["model_version"] == "11"
    assert body["run_id"] == "run-v11"
    assert body["resolution"] == "pinned-at-startup"


def test_v2_batch_valid_rows_predict_and_log(
    dual_serving_stub, native_batch_csv, mock_session, auth_client
):
    resp = auth_client.post(
        "/v2/batch_predict",
        files={"file": ("batch.csv", native_batch_csv, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    assert body["model_version"] == "11"
    assert [p["row"] for p in body["predictions"]] == [1, 2, 3]
    assert mock_session.add.call_count == 3
    assert mock_session.commit.call_count == 1


def test_v2_batch_bad_row_rejects_with_zero_writes(
    dual_serving_stub, native_request, mock_session, auth_client
):
    rows = [dict(native_request) for _ in range(3)]
    rows[1]["RIAGENDR"] = 7
    resp = auth_client.post(
        "/v2/batch_predict",
        files={"file": ("batch.csv", _native_csv(rows), "text/csv")},
    )
    assert resp.status_code == 422
    assert "row 2" in resp.json()["detail"]
    assert mock_session.add.call_count == 0
    assert mock_session.commit.call_count == 0


def test_v2_batch_oversize_body_is_413(dual_serving_stub, mock_session, auth_client):
    payload = "a" * (MAX_BATCH_BYTES + 1)
    resp = auth_client.post(
        "/v2/batch_predict",
        files={"file": ("batch.csv", payload, "text/csv")},
    )
    assert resp.status_code == 413
    assert mock_session.add.call_count == 0


def test_v2_batch_too_many_rows_is_413(
    dual_serving_stub, native_request, mock_session, auth_client
):
    header = ",".join(COLUMN_ORDER_V2)
    row = ",".join(["1"] * len(COLUMN_ORDER_V2))
    payload = "\n".join([header] + [row] * (MAX_BATCH_ROWS + 1))
    resp = auth_client.post(
        "/v2/batch_predict",
        files={"file": ("batch.csv", payload, "text/csv")},
    )
    assert resp.status_code == 413
    assert mock_session.add.call_count == 0


def test_v2_batch_extra_columns_warn_ignored(
    dual_serving_stub, native_batch_csv, mock_session, auth_client
):
    lines = native_batch_csv.splitlines()
    payload = "\n".join([lines[0] + ",mystery_col"] + [l + ",zzz" for l in lines[1:]])
    resp = auth_client.post(
        "/v2/batch_predict",
        files={"file": ("batch.csv", payload, "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 3
    assert mock_session.commit.call_count == 1


def test_v2_logged_row_shape(dual_serving_stub, native_request, mock_session, auth_client):
    resp = auth_client.post("/v2/predict", json=native_request)
    assert resp.status_code == 200
    logged = mock_session.add.call_args[0][0]
    assert isinstance(logged, PredictionLogV2)
    assert PredictionLogV2.__tablename__ == "predictions_v2"
    assert not isinstance(logged, PredictionLog)
    for col in COLUMN_ORDER_V2:
        assert getattr(logged, col) == native_request[col]
    assert logged.prediction == 1
    assert logged.probability == 0.8
    assert logged.model_version == "11"
    assert logged.created_at is not None
    assert mock_session.commit.call_count == 1


def test_v1_predict_regression_still_v9(
    dual_serving_stub, synthetic_ckd_request, mock_session, auth_client
):
    # v1 contract pinned: v9-stamped answers while the v2 slot serves 11.
    resp = auth_client.post("/predict", json=synthetic_ckd_request)
    assert resp.status_code == 200
    assert resp.json()["model_version"] == "9"
    logged = mock_session.add.call_args[0][0]
    assert isinstance(logged, PredictionLog)
    assert PredictionLog.__tablename__ == "predictions"
    for col in COLUMN_ORDER:
        assert getattr(logged, col) == synthetic_ckd_request[col]


def test_serving_never_imports_harmonization_adapter():
    # The eval-only NHANES→UCI adapter must stay out of the serving path.
    api_dir = Path(__file__).resolve().parents[1] / "api"
    offenders = [
        p.name
        for p in sorted(api_dir.glob("*.py"))
        if "harmonize_v9" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_v2_pipeline_artifact_path_tracks_training():
    # The v2 loader must read the native pipeline filename the training
    # run actually logged (distinct from v1 by 07-01 design).
    assert model_loader.V2_PIPELINE_ARTIFACT_PATH == (
        f"preprocessing/{NATIVE_PIPELINE_FILENAME}"
    )
    assert model_loader.V2_PIPELINE_ARTIFACT_PATH != model_loader.PIPELINE_ARTIFACT_PATH
