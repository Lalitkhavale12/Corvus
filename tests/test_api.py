"""Wave 0 API contract stubs for Phase 3 (03-01, FR-4.1 -> FR-4.4, FR-5.2).

RED BY DESIGN: api/app.py does not exist yet -- collection fails on the
api.app import until 03-02 implements the endpoints. Each stub below is a
real assertion 03-02 turns green; no live server, no real mlruns, no real
Postgres (tmp_mlflow_store plus mocked SQLAlchemy session only).
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.app import app


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
    assert resp.json()["model_version"] == "9"


def test_model_info_reports_pinned_version():
    # Pinned-at-startup resolution (D-02): version comes from config/env once,
    # never per-request registry resolution.
    with TestClient(app) as client:
        resp = client.get("/model_info")
    assert resp.status_code == 200
    assert resp.json()["pinned_version"] == "9"


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


def test_logged_row_carries_model_version(synthetic_ckd_request):
    # Claim 4: the Postgres row carries the same startup-pinned version.
    # 03-02 wires the patch target to the real session factory in api/db.py.
    session = MagicMock()
    with patch("api.db.Session", return_value=session):
        with TestClient(app) as client:
            resp = client.post("/predict", json=synthetic_ckd_request)
    assert resp.status_code == 200
    logged = session.add.call_args[0][0]
    assert logged.model_version == "9"
