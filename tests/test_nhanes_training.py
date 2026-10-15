"""Wave 0 tests for Phase 7 NHANES-native training (FR-2.1-FR-2.3).

Covers the quarantine abort gate, the native pipeline shape, the Claim-2
run contract on a tmp MLflow store, locked-holdout disjointness, and the
seeded LR estimator. Synthetic fixture only — never the real derived CSV,
never the real mlruns directory.
"""

import joblib
import mlflow
import numpy as np
import pandas as pd
import pytest

from src.preprocessing.preprocess_nhanes import (
    DERIVED_LABEL_DISCLOSURE,
    QUARANTINE_11,
    assert_quarantine,
    build_native_pipeline,
    get_nhanes_column_lists,
    locked_holdout_split,
)
from src.training import train_nhanes as nhanes_mod
from src.training.train import compute_metrics


def _native_frame(synthetic_nhanes_df):
    """Training frame: fixture minus the 11 quarantined label-source cols."""
    return synthetic_nhanes_df.drop(columns=list(QUARANTINE_11))


def _dense(arr):
    if hasattr(arr, "toarray"):  # sparse one-hot output; dense is fine here
        arr = arr.toarray()
    return np.asarray(arr, dtype=float)


def test_quarantine_aborts(synthetic_nhanes_df):
    # The fixture carries all 11 banned columns by design — the gate must
    # abort before any split or fit.
    with pytest.raises(SystemExit):
        assert_quarantine(synthetic_nhanes_df)


def test_native_pipeline_shape(synthetic_nhanes_df):
    df = _native_frame(synthetic_nhanes_df)
    assert_quarantine(df)  # clean training frame passes the gate
    numeric_cols, categorical_cols = get_nhanes_column_lists()
    assert len(numeric_cols) == 16
    assert len(categorical_cols) == 5
    pipe = build_native_pipeline(numeric_cols, categorical_cols)
    from sklearn.pipeline import Pipeline as SkPipeline

    assert isinstance(pipe, SkPipeline)
    assert not hasattr(pipe.named_steps["preprocessor"], "transformers_")
    X = df[numeric_cols + categorical_cols]
    out = _dense(pipe.fit_transform(X))
    assert not np.isnan(out).any()


def test_claim2_native(synthetic_nhanes_df, tmp_mlflow_store, tmp_path):
    df = _native_frame(synthetic_nhanes_df)
    numeric_cols, categorical_cols = get_nhanes_column_lists()
    X = df[numeric_cols + categorical_cols]
    y = df["ckd"].astype(int)
    pipe = build_native_pipeline(numeric_cols, categorical_cols)
    pipe.fit(X)
    est = nhanes_mod.build_native_estimator("logistic-regression")
    est.fit(pipe.transform(X), y)
    y_proba = est.predict_proba(pipe.transform(X))[:, 1]
    metrics = compute_metrics(y, est.predict(pipe.transform(X)), y_proba)

    pipe_path = tmp_path / "preprocessing_pipeline_nhanes.joblib"
    joblib.dump(pipe, pipe_path)
    mlflow.set_experiment("corvus-ckd-nhanes-test")
    with mlflow.start_run(run_name="native-logistic-regression") as run:
        mlflow.set_tag("schema", "nhanes-native")
        mlflow.set_tag("label_disclosure", DERIVED_LABEL_DISCLOSURE)
        mlflow.log_params({"model": type(est).__name__})
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(pipe_path), artifact_path="preprocessing")
        mlflow.sklearn.log_model(
            est, artifact_path="model", serialization_format="cloudpickle"
        )
        run_id = run.info.run_id
    client = mlflow.tracking.MlflowClient()
    artifacts = [f.path for f in client.list_artifacts(run_id, "")]
    assert "preprocessing" in artifacts  # Claim 2: same run, both artifacts
    logged = client.get_run(run_id).data.metrics
    for m in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        assert m in logged
    assert client.get_run(run_id).data.tags["schema"] == "nhanes-native"


def test_holdout_disjoint(synthetic_nhanes_df):
    df = _native_frame(synthetic_nhanes_df)
    numeric_cols, categorical_cols = get_nhanes_column_lists()
    X = df[numeric_cols + categorical_cols]
    y = df["ckd"].astype(int)
    X_dev, X_hold, y_dev, y_hold = locked_holdout_split(X, y)
    assert set(X_dev.index).isdisjoint(set(X_hold.index))
    assert set(X_dev.index) | set(X_hold.index) == set(X.index)
    assert len(X_hold) == int(0.2 * len(df))  # locked 20 percent holdout


def test_lr_estimator_seeded():
    assert set(nhanes_mod.NATIVE_ESTIMATORS) == {"logistic-regression"}
    est = nhanes_mod.build_native_estimator("logistic-regression")
    assert type(est).__name__ == "LogisticRegression"
    assert est.get_params()["random_state"] == 42
    with pytest.raises(KeyError):
        nhanes_mod.build_native_estimator("no-such-config")
