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
    assert set(nhanes_mod.NATIVE_ESTIMATORS) == {
        "logistic-regression",
        "decision-tree",
        "random-forest",
        "gradient-boosting",
        "xgboost",
        "lightgbm",
        "mlp-sigmoid",
        "mlp-tanh",
        "mlp-relu",
    }
    est = nhanes_mod.build_native_estimator("logistic-regression")
    assert type(est).__name__ == "LogisticRegression"
    assert est.get_params()["random_state"] == 42
    # Every seeded estimator carries random_state 42; lightgbm stays silent.
    for name in nhanes_mod.NATIVE_ESTIMATORS:
        params = nhanes_mod.build_native_estimator(name).get_params()
        assert params["random_state"] == 42, name
    assert nhanes_mod.build_native_estimator("lightgbm").get_params()["verbosity"] == -1
    # MLP configs reuse the train_mlp activation map with the locked shape.
    from src.training.train_mlp import ACTIVATIONS, MAX_ITER

    for display in ("sigmoid", "tanh", "relu"):
        mlp = nhanes_mod.build_native_estimator(f"mlp-{display}")
        assert type(mlp).__name__ == "MLPClassifier"
        assert mlp.get_params()["activation"] == ACTIVATIONS[display]
        assert mlp.get_params()["hidden_layer_sizes"] == (50,)
        assert mlp.get_params()["max_iter"] == MAX_ITER
    with pytest.raises(KeyError):
        nhanes_mod.build_native_estimator("no-such-config")


def _cv_means(synthetic_nhanes_df):
    """CV mean-AUC strings for every config on the synthetic fixture."""
    df = _native_frame(synthetic_nhanes_df)
    numeric_cols, categorical_cols = get_nhanes_column_lists()
    X = df[numeric_cols + categorical_cols]
    y = df["ckd"].astype(int)
    X_dev, _, y_dev, _ = locked_holdout_split(X, y)
    means = {}
    for name in nhanes_mod.NATIVE_ESTIMATORS:
        cv = nhanes_mod.run_cv_native(name, X_dev, y_dev, numeric_cols, categorical_cols)
        assert len(cv["fold_aucs"]) == 5
        means[name] = f"{cv['mean_auc']:.6f}"
    return means


def test_cv_determinism(synthetic_nhanes_df):
    # Two consecutive CV sweeps at seed 42 must produce identical means.
    assert _cv_means(synthetic_nhanes_df) == _cv_means(synthetic_nhanes_df)


def test_bootstrap_ci_determinism_and_bounds(synthetic_nhanes_df):
    import pathlib

    df = _native_frame(synthetic_nhanes_df)
    numeric_cols, categorical_cols = get_nhanes_column_lists()
    X = df[numeric_cols + categorical_cols]
    y = df["ckd"].astype(int)
    pipe = build_native_pipeline(numeric_cols, categorical_cols)
    pipe.fit(X)
    est = nhanes_mod.build_native_estimator("logistic-regression")
    est.fit(pipe.transform(X), y)
    proba = est.predict_proba(pipe.transform(X))[:, 1]
    lo, hi = nhanes_mod.bootstrap_auc_ci(y, proba, n_reps=50, seed=42)
    lo2, hi2 = nhanes_mod.bootstrap_auc_ci(y, proba, n_reps=50, seed=42)
    assert (lo, hi) == (lo2, hi2)  # seed-fixed determinism
    from sklearn.metrics import roc_auc_score

    auc = roc_auc_score(y, proba)
    assert lo <= auc <= hi
    assert lo <= hi


def test_no_recorded_uci_auc_reference():
    # The cross-dataset comparison against the recorded v9 UCI test AUC
    # must never be built: no source line may reference it.
    import pathlib
    import re

    src = pathlib.Path(nhanes_mod.__file__).read_text()
    assert re.search(r"\buci\b", src, re.IGNORECASE) is None
    assert "1.0" not in src


# --- 07-02 Task 2: harmonization adapter plus paired comparison ---

from types import SimpleNamespace

from src.evaluation import evaluate_nhanes as eval_mod
from src.training import harmonize_v9 as harm_mod


def _paired_inputs(seed: int = 7):
    rng = np.random.default_rng(seed)
    y = np.array([1] * 12 + [0] * 48)
    p_challenger = np.clip(rng.normal(0.62, 0.2, 60), 0.01, 0.99)
    p_v9 = np.clip(rng.normal(0.55, 0.2, 60), 0.01, 0.99)
    return y, p_challenger, p_v9


def test_paired_comparison_same_rows_same_labels():
    y, p_c, p_v = _paired_inputs()
    assert len(y) == len(p_c) == len(p_v)  # identical row counts
    result = eval_mod.compare_challenger(y, p_c, p_v, n_reps=50, seed=42)
    assert result.success
    # Same label vector scores both models: recompute matches the report.
    from sklearn.metrics import roc_auc_score

    assert result.challenger_auc == roc_auc_score(y, p_c)
    assert result.v9_auc == roc_auc_score(y, p_v)
    assert result.qualifies == (result.challenger_auc > result.v9_auc)
    assert result.disclosure == DERIVED_LABEL_DISCLOSURE
    # Strict-greater: dead heat never qualifies.
    tied = eval_mod.compare_challenger(y, p_c, p_c, n_reps=50, seed=42)
    assert tied.qualifies is False
    # Mismatched row counts are refused, never silently compared.
    with pytest.raises(ValueError):
        eval_mod.paired_bootstrap_diff(y, p_c[:30], p_v, n_reps=10)


def test_paired_bootstrap_determinism():
    y, p_c, p_v = _paired_inputs()
    first = eval_mod.paired_bootstrap_diff(y, p_c, p_v, n_reps=50, seed=42)
    second = eval_mod.paired_bootstrap_diff(y, p_c, p_v, n_reps=50, seed=42)
    assert first == second  # seed-fixed determinism
    assert first["lo"] <= first["hi"]


def test_aggregate_cv_strict_max():
    cv_results = {
        "logistic-regression": {"mean_auc": 0.80, "std_auc": 0.01},
        "mlp-relu": {"mean_auc": 0.83, "std_auc": 0.02},
        "xgboost": {"mean_auc": 0.81, "std_auc": 0.01},
    }
    assert eval_mod.aggregate_cv(cv_results) == "mlp-relu"


def test_harmonize_frame_shape_and_fill(synthetic_nhanes_df):
    df = _native_frame(synthetic_nhanes_df)
    numeric_cols, categorical_cols = get_nhanes_column_lists()
    modes = {col: f"{col}_mode" for col in harm_mod.V9_CATEGORICALS}
    harmonized = harm_mod.harmonize_frame(df[numeric_cols + categorical_cols], modes)
    from src.preprocessing.preprocess import get_column_lists

    uci_numeric, uci_cats = get_column_lists()
    assert list(harmonized.columns) == uci_numeric + uci_cats  # full UCI-24 frame
    assert len(harmonized) == len(df)
    for col in harm_mod.V9_CATEGORICALS:  # frozen most-frequent fills
        assert (harmonized[col] == modes[col]).all()
    for uci_col, nh_col in harm_mod.NHANES_TO_UCI_MAP.items():  # mapped numerics
        assert np.allclose(
            harmonized[uci_col].to_numpy(dtype=float),
            pd.to_numeric(df[nh_col], errors="coerce").to_numpy(dtype=float),
            equal_nan=True,
        )
    unmapped = set(uci_numeric) - set(harm_mod.NHANES_TO_UCI_MAP)
    assert unmapped  # the handicap is real: v9 imputes these itself
    for col in unmapped:
        assert harmonized[col].isna().all()
    assert set(harm_mod.NHANES_TO_UCI_MAP) == {
        "age", "bu", "bgr", "sod", "pot", "hemo", "pcv", "wc", "rc",
    }
    assert len(harm_mod.UNIT_NOTES) == 9


class _StubRegistryClient:
    """Minimal MlflowClient stand-in recording stage transitions."""

    def __init__(self, production_version: str = "9"):
        self.calls = []
        self._production = production_version

    def get_model_version(self, name, version):
        stage = "Production" if str(version) == self._production else "None"
        return SimpleNamespace(current_stage=stage)

    def transition_model_version_stage(
        self, name, version, stage, archive_existing_versions=False
    ):
        self.calls.append((str(version), stage))


def test_apply_challenger_stages_keeps_production():
    client = _StubRegistryClient(production_version="9")
    eval_mod.apply_challenger_stages(client, "corvus-ckd", "11", ["10"], "9")
    assert ("11", "Staging") in client.calls
    assert ("10", "Archived") in client.calls
    # Production is never a transition target and still reads Production.
    assert all(version != "9" for version, _stage in client.calls)
    assert client.get_model_version("corvus-ckd", "9").current_stage == "Production"
    with pytest.raises(ValueError):
        eval_mod.apply_challenger_stages(client, "corvus-ckd", "9", [], "9")


def test_adapter_not_served():
    # The harmonization adapter is eval-only: no serving module may import it.
    import pathlib

    api_dir = pathlib.Path(eval_mod.__file__).resolve().parents[2] / "api"
    offenders = [
        path.name
        for path in sorted(api_dir.glob("*.py"))
        if "harmonize_v9" in path.read_text()
    ]
    assert offenders == []
