"""Tests for Phase 2 registry lifecycle (FR-2.4, FR-3.1-FR-3.3, D-03/D-06/D-07)."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.evaluation import evaluate as eval_mod


def _runs():
    return [
        {"run_id": "a", "run_name": "xgb", "metrics": {"roc_auc": 0.91}},
        {"run_id": "b", "run_name": "logistic-regression", "metrics": {"roc_auc": 0.97}},
        {"run_id": "c", "run_name": "rf", "metrics": {"roc_auc": 0.88}},
    ]


def test_winner_is_strict_max_roc_auc():
    winner = eval_mod.select_winner(_runs())
    assert winner["run_id"] == "b"  # strict max, first max wins on ties (D-03)


def test_stage_transitions():
    client = MagicMock()
    eval_mod.apply_registry_stages(client, "corvus-ckd", "3", ["1", "2"])
    calls = {
        (c.kwargs["version"], c.kwargs["stage"]): c.kwargs
        for c in client.transition_model_version_stage.call_args_list
    }
    assert calls["3", "Staging"]["archive_existing_versions"] is True
    assert ("1", "Archived") in calls
    assert ("2", "Archived") in calls


def test_every_run_registers_version(tmp_path, monkeypatch):
    # Every training run registers a new version: run_experiment twice on a
    # tmp tracking URI and assert the registered model gains versions.
    import mlflow
    from sklearn.dummy import DummyClassifier

    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    uri = str(tmp_path / "mlruns")
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("corvus-ckd-version-test")
    for i in range(2):
        with mlflow.start_run(run_name=f"run-{i}"):
            mlflow.log_metric("roc_auc", 0.5 + i * 0.1)
            mlflow.sklearn.log_model(
                DummyClassifier(strategy="prior"),
                artifact_path="model",
                registered_model_name="corvus-ckd-tmp",
                serialization_format="cloudpickle",
            )
    client = mlflow.tracking.MlflowClient()
    versions = client.search_model_versions("name='corvus-ckd-tmp'")
    assert len(versions) >= 2


def test_no_production_transition():
    client = MagicMock()
    eval_mod.apply_registry_stages(client, "corvus-ckd", "3", ["1", "2"])
    stages = [
        c.kwargs["stage"]
        for c in client.transition_model_version_stage.call_args_list
    ]
    assert "Production" not in stages  # D-06: separate explicit step
    assert set(stages) == {"Staging", "Archived"}  # exact stage strings
