"""Authentication tests — register, login, get-me, role guards.

Uses SQLite in-memory via DATABASE_URL env var so tests run without
PostgreSQL. Tables are created once per session.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Use SQLite for auth tests so they run without PostgreSQL.
# Kept in the OS temp dir so test runs never litter the repo root.
_DB_PATH = Path(tempfile.gettempdir()) / "corvus_test_auth.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH.as_posix()}"

# Clean up any leftover test database from previous runs
if _DB_PATH.exists():
    _DB_PATH.unlink()

from fastapi.testclient import TestClient

from api.app import app
from src.database import Base, get_engine

# Create all tables (users) before tests run
engine = get_engine()
if engine is not None:
    Base.metadata.create_all(bind=engine)

client = TestClient(app)

REGISTER_PAYLOAD = {
    "email": "testpatient@example.com",
    "password": "securepass123",
    "role": "patient",
}

DOCTOR_PAYLOAD = {
    "email": "testdoctor@example.com",
    "password": "securepass456",
    "role": "doctor",
}


def test_register_patient():
    r = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["email"] == REGISTER_PAYLOAD["email"]
    assert data["role"] == "patient"
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert "id" in data


def test_register_duplicate_email():
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 400, r.text
    assert "already registered" in r.json()["detail"]


def test_register_invalid_role():
    payload = {**REGISTER_PAYLOAD, "email": "badrole@example.com", "role": "admin"}
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422, r.text


def test_register_invalid_email():
    payload = {**REGISTER_PAYLOAD, "email": "not-an-email"}
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422, r.text


def test_register_short_password():
    payload = {**REGISTER_PAYLOAD, "email": "shortpw@example.com", "password": "123"}
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422, r.text


def test_login_success():
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    r = client.post(
        "/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    r = client.post(
        "/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrongpassword"},
    )
    assert r.status_code == 401, r.text


def test_login_nonexistent_user():
    r = client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "whatever"},
    )
    assert r.status_code == 401, r.text


def test_get_me_with_token():
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    login = client.post(
        "/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    token = login.json()["access_token"]
    r = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == REGISTER_PAYLOAD["email"]
    assert data["role"] == "patient"


def test_get_me_without_token():
    r = client.get("/auth/me")
    assert r.status_code == 401, r.text


def test_get_me_with_invalid_token():
    r = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert r.status_code == 401, r.text


def test_register_doctor():
    r = client.post("/auth/register", json=DOCTOR_PAYLOAD)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["email"] == DOCTOR_PAYLOAD["email"]
    assert data["role"] == "doctor"
