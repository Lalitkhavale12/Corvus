"""Regression tests for the registry + profile auth gates (bug fix, Nov 2026).

Two defects shipped before these tests existed:

1. ``mlflow.ModelVersion`` has no ``metadata`` attribute in MLflow 3.x, so
   ``mv.metadata.metrics`` raised on every version; ``list_all_model_versions``
   swallowed it and returned ``[]`` and ``/api/v1/models/{v}/details`` 500'd.
2. ``/api/v1/models*``, ``/auth/profile`` (GET and POST) depended on the
   *optional* ``get_current_user``, so unauthenticated calls dereferenced
   ``None`` -> 500 AttributeError instead of 401.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

# Own SQLite DB, isolated from the other auth test modules.
import src.database as _db_module  # noqa: E402

_db_module._engine = None  # type: ignore[attr-defined]
_db_module._SessionLocal = None  # type: ignore[attr-defined]

_DB_PATH = Path(tempfile.gettempdir()) / "corvus_test_registry_api.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH.as_posix()}"
if _DB_PATH.exists():
    _DB_PATH.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from api import model_loader  # noqa: E402
from api.app import app  # noqa: E402
from src.database import Base, get_engine  # noqa: E402

engine = get_engine()
if engine is not None:
    Base.metadata.create_all(bind=engine)

client = TestClient(app)

PROTECTED_PATHS = [
    "/api/v1/models",
    "/api/v1/models/15/details",
    "/api/v1/models/compare",
    "/auth/profile",
]


def test_registry_and_profile_require_auth():
    """No token -> 401 everywhere (previously 500 / 200-with-empty-list)."""
    for path in PROTECTED_PATHS:
        response = client.get(path)
        assert response.status_code == 401, f"{path} -> {response.status_code}"


def test_create_profile_requires_auth():
    response = client.post("/auth/profile", json={"first_name": "A"})
    assert response.status_code == 401


def test_version_details_read_metrics_from_the_run(tmp_mlflow_store):
    """Details/list must work on MLflow 3.x, where ModelVersion has no .metadata."""
    client_mlflow = MlflowClient()
    client_mlflow.create_registered_model(model_loader.REGISTERED_MODEL_NAME)

    with mlflow.start_run() as run:
        mlflow.log_metric("roc_auc", 0.8123)
        run_id = run.info.run_id

    client_mlflow.create_model_version(
        name=model_loader.REGISTERED_MODEL_NAME, source="dummy", run_id=run_id
    )

    details = model_loader.get_model_version_details(version="1")
    assert details is not None
    assert details["metrics"]["roc_auc"] == 0.8123

    listed = model_loader.list_all_model_versions()
    assert [m["version"] for m in listed] == ["1"]
    assert listed[0]["metrics"]["roc_auc"] == 0.8123


def test_unknown_version_returns_none(tmp_mlflow_store):
    MlflowClient().create_registered_model(model_loader.REGISTERED_MODEL_NAME)
    assert model_loader.get_model_version_details(version="99") is None
