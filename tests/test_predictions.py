"""Authenticated prediction and history tests (Phase 8-03).

SQLite is used for the auth DB so register/login/profile tests hit a real
database. The autouse _serving_stub fixture mocks the model loader (no
real MLflow) so the app lifespan can start in tests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.db as db_mod
from api.app import app
from src.database import Base, get_engine

# Reset the auth DB engine cache so this test file gets its own SQLite DB.
import src.database as _db_module  # noqa: E402

_db_module._engine = None  # type: ignore[attr-defined]
_db_module._SessionLocal = None  # type: ignore[attr-defined]

# Kept in the OS temp dir so test runs never litter the repo root.
_DB_PATH = Path(tempfile.gettempdir()) / "corvus_test_predictions.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH.as_posix()}"

if _DB_PATH.exists():
    _DB_PATH.unlink()

# Create all tables (users, profiles, predictions, predictions_v2) once.
engine = get_engine()
if engine is not None:
    Base.metadata.create_all(bind=engine)


class _StubEstimator:
    n_features_in_ = 4

    def predict(self, X):
        return [1] * len(X)

    def predict_proba(self, X):
        return [[0.2, 0.8]] * len(X)


class _StubPipeline:
    def transform(self, df):
        return np.zeros((len(df), 4))


@pytest.fixture(autouse=True)
def _serving_stub(monkeypatch):
    """Mock the model loader so the app lifespan starts without MLflow."""
    monkeypatch.setattr(
        "api.app.model_loader.load_serving_artifacts",
        lambda version: (_StubEstimator(), _StubPipeline(), "test-run-id", "9"),
    )


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


PATIENT_PAYLOAD = {
    "email": "predpatient@example.com",
    "password": "securepass123",
    "role": "patient",
}

DOCTOR_PAYLOAD = {
    "email": "preddoctor@example.com",
    "password": "securepass456",
    "role": "doctor",
}

VALID_CKD_REQUEST = {
    "age": 55.0,
    "bp": 80.0,
    "sg": 1.02,
    "al": 1.0,
    "su": 0.0,
    "bgr": 120.0,
    "bu": 30.0,
    "sc": 1.2,
    "sod": 140.0,
    "pot": 4.0,
    "hemo": 14.0,
    "pcv": 42.0,
    "wc": 7500.0,
    "rc": 4.8,
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

VALID_NATIVE_REQUEST = {
    "RIDAGEYR": 55.0,
    "INDFMPIR": 3.0,
    "LBDSBUSI": 100.0,
    "LBDSGLSI": 100.0,
    "LBXSNASI": 140.0,
    "LBXSKSI": 4.0,
    "LBDSCASI": 9.0,
    "LBDSPHSI": 7.4,
    "LBXHGB": 14.0,
    "LBXHCT": 42.0,
    "LBXWBCSI": 7500.0,
    "LBXRBCSI": 4.8,
    "LBXGH": 5.5,
    "BMXBMI": 28.0,
    "BPXOSY1": 130.0,
    "BPXODI1": 85.0,
    "RIAGENDR": 2,
    "DMDEDUC2": 3,
    "DIQ010": 2,
}


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client, email: str, password: str, role: str) -> str:
    client.post("/auth/register", json={"email": email, "password": password, "role": role})
    return client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]


def test_predict_requires_auth(client):
    r = client.post("/v2/predict", json=VALID_NATIVE_REQUEST)
    assert r.status_code == 401, r.text


def test_batch_predict_requires_auth(client):
    r = client.post("/v2/batch_predict", files={})
    assert r.status_code == 401, r.text


def test_predict_creates_history_row_for_patient(client):
    token = _register_and_login(client, PATIENT_PAYLOAD["email"], PATIENT_PAYLOAD["password"], "patient")
    # v2 may be 503 if no challenger pin; use v1 instead
    r = client.post(
        "/predict", json=VALID_CKD_REQUEST, headers=_auth_header(token)
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "prediction" in data
    assert "probability" in data
    assert "model_version" in data

    # History should contain this prediction
    r = client.get("/auth/predictions", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) >= 1
    assert rows[0]["prediction"] == data["prediction"]
    assert rows[0]["probability"] == data["probability"]
    assert rows[0]["model_version"] == data["model_version"]


def test_history_excludes_other_users_rows(client):
    patient_token = _register_and_login(client, "histpatient@example.com", "securepass123", "patient")
    doctor_token = _register_and_login(client, "histdoctor@example.com", "securepass456", "doctor")

    # Patient makes a prediction
    client.post(
        "/predict", json=VALID_CKD_REQUEST, headers=_auth_header(patient_token)
    )

    # Patient's history should have 1 row
    r = client.get("/auth/predictions", headers=_auth_header(patient_token))
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1

    # Doctor's history should have 0 rows (no predictions made by doctor)
    r = client.get("/auth/predictions", headers=_auth_header(doctor_token))
    assert r.status_code == 200, r.text
    assert r.json() == []


def test_get_single_prediction_owned_by_user(client):
    token = _register_and_login(client, "single@example.com", "securepass123", "patient")
    r = client.post(
        "/predict", json=VALID_CKD_REQUEST, headers=_auth_header(token)
    )
    assert r.status_code == 200, r.text

    rows = client.get("/auth/predictions", headers=_auth_header(token)).json()
    pred_id = rows[0]["id"]

    r = client.get(f"/auth/predictions/{pred_id}", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    assert r.json()["id"] == pred_id


def test_get_single_prediction_wrong_owner_404(client):
    token_a = _register_and_login(client, "ownera@example.com", "securepass123", "patient")
    token_b = _register_and_login(client, "ownerb@example.com", "securepass456", "patient")

    client.post(
        "/predict", json=VALID_CKD_REQUEST, headers=_auth_header(token_a)
    )

    rows = client.get("/auth/predictions", headers=_auth_header(token_a)).json()
    pred_id = rows[0]["id"]

    # User B tries to access User A's prediction
    r = client.get(f"/auth/predictions/{pred_id}", headers=_auth_header(token_b))
    assert r.status_code == 404, r.text


def test_get_single_prediction_nonexistent_404(client):
    token = _register_and_login(client, "nonexist@example.com", "securepass123", "patient")
    r = client.get("/auth/predictions/99999", headers=_auth_header(token))
    assert r.status_code == 404, r.text


def test_predict_without_token_401(client):
    r = client.post("/predict", json=VALID_CKD_REQUEST)
    assert r.status_code == 401, r.text


def test_history_without_token_401(client):
    r = client.get("/auth/predictions")
    assert r.status_code == 401, r.text
