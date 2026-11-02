"""Profile and patient-doctor mapping tests (Phase 8-02).

Uses SQLite in-memory via DATABASE_URL env var so tests run without
PostgreSQL. Tables are created once per session.
"""

from __future__ import annotations

import os

# Reset the auth DB engine cache so this test file gets its own SQLite
# database (test_auth.py caches the engine under test_auth.db).
import src.database as _db_module  # noqa: E402

_db_module._engine = None  # type: ignore[attr-defined]
_db_module._SessionLocal = None  # type: ignore[attr-defined]

os.environ["DATABASE_URL"] = "sqlite:///./test_profiles.db"

if os.path.exists("test_profiles.db"):
    os.remove("test_profiles.db")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402
from src.database import Base, get_engine  # noqa: E402

# Create all tables (users + profiles + mapping) before tests run
engine = get_engine()
if engine is not None:
    Base.metadata.create_all(bind=engine)

client = TestClient(app)

PATIENT_PROFILE = {
    "first_name": "Maria",
    "last_name": "Gonzalez",
    "sex": "F",
    "phone": "+1-555-0100",
    "mrn": "MRN-001",
}

DOCTOR_PROFILE = {
    "first_name": "Sarah",
    "last_name": "Jenkins",
    "license_number": "MD-12345",
    "specialization": "Nephrology",
    "phone": "+1-555-0200",
}


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def _register(email: str, password: str, role: str = "patient"):
    return client.post("/auth/register", json={"email": email, "password": password, "role": role})


def _new_patient(suffix: str) -> str:
    email = f"patient_{suffix}@example.com"
    _register(email, "securepass123", "patient")
    return email


def _new_doctor(suffix: str) -> str:
    email = f"doctor_{suffix}@example.com"
    _register(email, "securepass456", "doctor")
    return email


def test_patient_profile_create_and_retrieve():
    email = _new_patient("create")
    token = _login(email, "securepass123").json()["access_token"]

    r = client.post(
        "/auth/profile",
        json={**PATIENT_PROFILE, "mrn": "MRN-CREATE-001"},
        headers=_auth_header(token),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["role"] == "patient"
    assert data["patient_profile"]["first_name"] == "Maria"
    assert data["patient_profile"]["mrn"] == "MRN-CREATE-001"
    assert data["patient_profile"]["user_id"] is not None

    r = client.get("/auth/profile", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "patient"
    assert data["patient_profile"]["first_name"] == "Maria"


def test_patient_profile_already_exists():
    email = _new_patient("exists")
    token = _login(email, "securepass123").json()["access_token"]

    client.post("/auth/profile", json={**PATIENT_PROFILE, "mrn": "MRN-EXISTS-001"}, headers=_auth_header(token))
    r = client.post("/auth/profile", json={**PATIENT_PROFILE, "mrn": "MRN-EXISTS-001"}, headers=_auth_header(token))
    assert r.status_code == 400, r.text
    assert "already exists" in r.json()["detail"]


def test_patient_profile_not_found():
    email = _new_patient("notfound")
    token = _login(email, "securepass123").json()["access_token"]

    r = client.get("/auth/profile", headers=_auth_header(token))
    assert r.status_code == 404, r.text


def test_doctor_profile_create_and_retrieve():
    email = _new_doctor("create")
    token = _login(email, "securepass456").json()["access_token"]

    r = client.post(
        "/auth/profile",
        json={**DOCTOR_PROFILE, "license_number": "MD-CREATE-001"},
        headers=_auth_header(token),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["role"] == "doctor"
    assert data["doctor_profile"]["first_name"] == "Sarah"
    assert data["doctor_profile"]["license_number"] == "MD-CREATE-001"
    assert data["doctor_profile"]["user_id"] is not None

    r = client.get("/auth/profile", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["role"] == "doctor"
    assert data["doctor_profile"]["specialization"] == "Nephrology"


def test_doctor_profile_already_exists():
    email = _new_doctor("exists")
    token = _login(email, "securepass456").json()["access_token"]

    client.post(
        "/auth/profile", json={**DOCTOR_PROFILE, "license_number": "MD-EXISTS-001"}, headers=_auth_header(token)
    )
    r = client.post(
        "/auth/profile", json={**DOCTOR_PROFILE, "license_number": "MD-EXISTS-001"}, headers=_auth_header(token)
    )
    assert r.status_code == 400, r.text
    assert "already exists" in r.json()["detail"]


def test_doctor_lists_assigned_patients_empty():
    email = _new_doctor("empty")
    token = _login(email, "securepass456").json()["access_token"]

    r = client.get("/doctors/patients", headers=_auth_header(token))
    assert r.status_code == 200, r.text
    assert r.json() == []


def test_patient_cannot_list_doctor_patients():
    email = _new_patient("guard")
    token = _login(email, "securepass123").json()["access_token"]

    r = client.get("/doctors/patients", headers=_auth_header(token))
    assert r.status_code == 403, r.text


def test_doctor_assigns_patient():
    patient_email = _new_patient("assign")
    doctor_email = _new_doctor("assign")
    doctor_token = _login(doctor_email, "securepass456").json()["access_token"]

    r = client.post(
        "/doctors/patients/assign",
        json={"patient_email": patient_email},
        headers=_auth_header(doctor_token),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["patient_id"] is not None
    assert data["doctor_id"] is not None
    assert data["is_active"] is True

    # Patient now appears in doctor's list
    r = client.get("/doctors/patients", headers=_auth_header(doctor_token))
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    assert r.json()[0]["patient_id"] is not None


def test_doctor_assigns_patient_duplicate():
    patient_email = _new_patient("dup")
    doctor_email = _new_doctor("dup")
    doctor_token = _login(doctor_email, "securepass456").json()["access_token"]

    client.post(
        "/doctors/patients/assign",
        json={"patient_email": patient_email},
        headers=_auth_header(doctor_token),
    )
    r = client.post(
        "/doctors/patients/assign",
        json={"patient_email": patient_email},
        headers=_auth_header(doctor_token),
    )
    assert r.status_code == 400, r.text
    assert "already assigned" in r.json()["detail"]


def test_doctor_assigns_nonexistent_patient():
    doctor_email = _new_doctor("nonexist")
    doctor_token = _login(doctor_email, "securepass456").json()["access_token"]

    r = client.post(
        "/doctors/patients/assign",
        json={"patient_email": "nonexistent@example.com"},
        headers=_auth_header(doctor_token),
    )
    assert r.status_code == 404, r.text


def test_doctor_assigns_non_patient_user():
    other_doctor_email = _new_doctor("other")
    doctor_email = _new_doctor("guard")
    doctor_token = _login(doctor_email, "securepass456").json()["access_token"]

    r = client.post(
        "/doctors/patients/assign",
        json={"patient_email": other_doctor_email},
        headers=_auth_header(doctor_token),
    )
    assert r.status_code == 400, r.text
    assert "not a patient" in r.json()["detail"]
