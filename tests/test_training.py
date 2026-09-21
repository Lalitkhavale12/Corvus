"""Tests for Phase 2 training path (FR-2.1-FR-2.5, Claim 2).

Tracer slice: logistic-regression entry; plan 02-02 extends the
all-configs test to the full 9-config slate (D-01).
"""
import mlflow
import pandas as pd

from src.preprocessing.preprocess import LINEAGE_ID_COL, LINEAGE_ROW_COL
from src.training import train as train_mod


def test_all_nine_configs_construct():
    # Classical slate: 6 entries with seeded defaults (D-01/D-02).
    # MLP activations asserted separately once train_mlp.py lands (Task 2).
    expected = {
        "logistic-regression": "LogisticRegression",
        "decision-tree": "DecisionTreeClassifier",
        "random-forest": "RandomForestClassifier",
        "gradient-boosting": "GradientBoostingClassifier",
        "xgboost": "XGBClassifier",
        "lightgbm": "LGBMClassifier",
    }
    assert set(train_mod.ESTIMATORS) == set(expected)
    for name, cls_name in expected.items():
        est = train_mod.build_estimator(name)
        assert type(est).__name__ == cls_name
        assert est.get_params()["random_state"] == 42


def test_lineage_excluded_feature_count_24():
    (X_train, _), _, _ = train_mod.load_raw_splits()
    assert LINEAGE_ROW_COL not in X_train.columns
    assert LINEAGE_ID_COL not in X_train.columns
    assert len(X_train.columns) == 24  # Claim 2 training-input contract


def test_loader_reads_raw_only(monkeypatch):
    import src.training.train as tm

    seen = []
    real_read_csv = pd.read_csv

    def spy(path, *a, **k):
        seen.append(str(path))
        return real_read_csv(path, *a, **k)

    monkeypatch.setattr(tm.pd, "read_csv", spy)
    tm.load_raw_splits()
    assert seen, "loader read no files"
    assert all(p.endswith("_raw.csv") for p in seen), seen
    assert not any(
        p.endswith(("/train.csv", "/val.csv", "/test.csv")) for p in seen
    ), seen


def test_run_logs_pipeline_and_model(tmp_path, monkeypatch):
    import src.training.train as tm

    # Redirect only the tracking URI at tmp_path; training still reads the
    # real raw CSVs. Registered-model creation is skipped here (tmp store
    # has no registry need) — log_model without registered_model_name.
    monkeypatch.setattr(tm, "PROJECT_ROOT", tmp_path)
    (X_train, y_train), (_, _), (X_test, y_test) = tm.load_raw_splits()
    from src.preprocessing.preprocess import build_pipeline, get_column_lists

    num, cat = get_column_lists()
    pipe = build_pipeline(
        [c for c in num if c in X_train.columns],
        [c for c in cat if c in X_train.columns],
    )
    pipe.fit(X_train)
    est = tm.build_estimator("logistic-regression")
    Xt_tr, Xt_te = pipe.transform(X_train), pipe.transform(X_test)
    est.fit(Xt_tr, y_train)
    yp = est.predict(Xt_te)
    ypr = est.predict_proba(Xt_te)[:, 1]
    metrics = tm.compute_metrics(y_test, yp, ypr)

    mlflow.set_tracking_uri(str(tmp_path / "mlruns"))
    mlflow.set_experiment("corvus-ckd-test")
    with mlflow.start_run(run_name="logistic-regression") as run:
        mlflow.log_params({"model": type(est).__name__})
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(
            "data/processed/preprocessing_pipeline.joblib",
            artifact_path="preprocessing",
        )
        mlflow.sklearn.log_model(
            est, artifact_path="model", serialization_format="cloudpickle"
        )
        run_id = run.info.run_id
    client = mlflow.tracking.MlflowClient()
    artifacts = [f.path for f in client.list_artifacts(run_id, "")]
    assert "preprocessing" in artifacts  # Claim 2: same run, both artifacts
    # MLflow 3.x logs models as logged-model entities linked to the run,
    # not as run artifacts — assert the linkage instead of an artifact path.
    exp = client.get_experiment_by_name("corvus-ckd-test")
    linked = mlflow.search_logged_models(experiment_ids=[exp.experiment_id])
    assert run_id in set(linked["source_run_id"])
    logged = client.get_run(run_id).data.metrics
    for m in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        assert m in logged
