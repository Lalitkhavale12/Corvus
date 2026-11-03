"""Phase 7 - NHANES-native training entry point (9-config sweep, 07-02).

Native-schema counterpart to ``src/training/train.py``: the quarantine
gate runs before any split, the locked holdout is split once, CV folds
come from the dev split only with a fresh pipeline fit per fold-train,
and the winning config is refit on full dev and scored once on the
holdout. Each Claim-2 MLflow run (pipeline + model artifacts, 5 metrics)
lands under the ``corvus-ckd-nhanes`` experiment tagged
``schema=nhanes-native`` and registered as ``corvus-ckd``.

Selection is strict-max on CV-mean ROC-AUC. The holdout prediction
frame (row ids, true labels, probabilities) is logged as an artifact so
the paired comparison in ``src/evaluation/evaluate_nhanes.py`` can prove
same-rows same-labels without ever refitting on the holdout.

Invoked as ``python -m src.training.train_nhanes`` from the project root.
"""

import json
import os
import warnings
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from src.preprocessing.preprocess_nhanes import (
    DERIVED_LABEL_DISCLOSURE,
    QUARANTINE_11,
    assert_quarantine,
    build_native_pipeline,
    cycle_holdout_split,
    get_nhanes_column_lists,
    locked_holdout_split,
)
from src.training.train import compute_metrics
from src.training.train_mlp import ACTIVATIONS, MAX_ITER
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

REGISTERED_MODEL_NAME = "corvus-ckd"

# Full 9-config slate: the 6 classical Phase-2 hyperparameters verbatim
# (each seeded) plus the 3 MLP activations via the train_mlp map with the
# locked small hidden layer and fixed iteration budget, all seeded.
NATIVE_ESTIMATORS = {
    # Baseline linear model; random_state keeps the lbfgs shuffling reproducible.
    "logistic-regression": LogisticRegression(random_state=42),
    # Single-tree baseline isolating split quality from ensembling gains.
    "decision-tree": DecisionTreeClassifier(random_state=42),
    # Bagged trees tame single-tree variance on noisy clinical rows.
    "random-forest": RandomForestClassifier(random_state=42),
    # Sequential-error correction as the boosting foil to bagging.
    "gradient-boosting": GradientBoostingClassifier(random_state=42),
    # Gradient boosting with sparsity-aware splits for heavy-missingness columns.
    "xgboost": XGBClassifier(random_state=42),
    # Leaf-wise booster for a second gradient-boosting family; verbosity silenced.
    "lightgbm": LGBMClassifier(random_state=42, verbosity=-1),
    # MLP activations via the train_mlp map ("sigmoid" translates to
    # sklearn's "logistic"; never pass the literal "sigmoid" to sklearn).
    "mlp-sigmoid": MLPClassifier(
        hidden_layer_sizes=(50,),
        activation=ACTIVATIONS["sigmoid"],
        max_iter=MAX_ITER,
        random_state=42,
    ),
    "mlp-tanh": MLPClassifier(
        hidden_layer_sizes=(50,),
        activation=ACTIVATIONS["tanh"],
        max_iter=MAX_ITER,
        random_state=42,
    ),
    "mlp-relu": MLPClassifier(
        hidden_layer_sizes=(50,),
        activation=ACTIVATIONS["relu"],
        max_iter=MAX_ITER,
        random_state=42,
    ),
}

NATIVE_PIPELINE_FILENAME = "preprocessing_pipeline_nhanes.joblib"
HOLDOUT_PREDS_FILENAME = "holdout_predictions_native.csv"
# Deployed operating point: the probability cut-off the API uses to turn
# ``predict_proba`` into a yes/no. Bound to the model version it was
# selected for, because the cut-off depends on the estimator's scale.
THRESHOLD_FILENAME = "nhanes_decision_threshold.json"
THRESHOLD_ARTIFACT_PATH = "evaluation"


def build_native_estimator(name: str):
    """Return a fresh native estimator instance for a registered config name."""
    if name not in NATIVE_ESTIMATORS:
        raise KeyError(f"Unknown native estimator config: {name!r}")
    base = NATIVE_ESTIMATORS[name]
    return base.__class__(**base.get_params())


def _fit_native(estimator, X_train_t, y_train, name: str):
    """Fit one estimator; record-and-log ConvergenceWarning, never raise."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        estimator.fit(X_train_t, y_train)
    for warning in caught:
        log.warning(f"Native ({name}) training notice: {warning.message}")
    return estimator


def load_native_frame():
    """Load the derived CSV and project the native allow-list frame.

    Returns ``(X, y, numeric_cols, categorical_cols)``. The quarantined
    label-source columns ride along in the locked CSV by design and are
    dropped by the allow-list projection, never model inputs.
    """
    cfg = load_config()
    target_col = cfg["data"]["nhanes_target_column"]
    positive_label = cfg["data"]["nhanes_positive_label"]
    csv_path = PROJECT_ROOT / cfg["data"]["nhanes_csv"]

    df = pd.read_csv(csv_path).copy()

    numeric_cols, categorical_cols = get_nhanes_column_lists()
    numeric_cols = [c for c in numeric_cols if c in df.columns]
    categorical_cols = [c for c in categorical_cols if c in df.columns]
    dropped_quarantine = sorted(set(df.columns) & QUARANTINE_11)
    if dropped_quarantine:
        log.info(f"Excluded quarantined label-source columns: {dropped_quarantine}")
    unexpected = (
        set(df.columns)
        - set(numeric_cols)
        - set(categorical_cols)
        - {target_col}
        - QUARANTINE_11
    )
    if unexpected:
        log.warning(f"Unexpected columns in {csv_path.name}: {unexpected}")

    y_raw = df[target_col]
    if set(pd.to_numeric(y_raw, errors="coerce").dropna().unique()) <= {0, 1}:
        y = pd.to_numeric(y_raw).astype(int)
    else:
        y = (
            y_raw.astype(str).str.strip().str.lower()
            == str(positive_label).strip().lower()
        ).astype(int)
    X = df[numeric_cols + categorical_cols]
    cycle = df["SDDSRVYR"] if "SDDSRVYR" in df.columns else pd.Series(np.nan, index=X.index)
    return X, y, numeric_cols, categorical_cols, cycle


def split_native(X: pd.DataFrame, y: pd.Series, cycle: pd.Series):
    """Hold out the configured cycle when set, else the locked random split."""
    holdout_cycle = load_config()["data"].get("nhanes_holdout_cycle")
    if holdout_cycle is None:
        return locked_holdout_split(X, y)
    dev, hold, y_dev, y_hold = cycle_holdout_split(X, y, cycle, holdout_cycle)
    log.info(
        f"Forward split: holdout cycle {holdout_cycle} "
        f"({len(hold)} rows, {int(y_hold.sum())} positive), "
        f"fit pool {len(dev)} rows"
    )
    return dev, hold, y_dev, y_hold


def run_cv_native(
    name: str,
    X_dev: pd.DataFrame,
    y_dev: pd.Series,
    numeric_cols: list,
    categorical_cols: list,
    n_splits: int = 5,
) -> dict:
    """Stratified 5-fold CV for one config over the dev split only.

    Fresh ``build_native_pipeline`` fit per fold-train; per-fold ROC-AUC
    from probabilities. The holdout is never referenced here.
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_aucs = []
    oof = np.full(len(y_dev), np.nan)
    for tr, va in skf.split(X_dev, y_dev):
        pipe = build_native_pipeline(numeric_cols, categorical_cols)
        pipe.fit(X_dev.iloc[tr])  # fit on fold-train only (leak-safe)
        estimator = build_native_estimator(name)
        _fit_native(
            estimator,
            pipe.transform(X_dev.iloc[tr]),
            y_dev.iloc[tr],
            name,
        )
        proba = estimator.predict_proba(pipe.transform(X_dev.iloc[va]))[:, 1]
        oof[va] = proba
        fold_aucs.append(float(roc_auc_score(y_dev.iloc[va], proba)))
    return {
        "mean_auc": float(np.mean(fold_aucs)),
        "std_auc": float(np.std(fold_aucs)),
        "fold_aucs": fold_aucs,
        # Out-of-fold probabilities, assembled across folds: dev-split only,
        # so a cut-off chosen from these never sees the holdout.
        "oof_proba": oof,
    }


def bootstrap_auc_ci(y_true, y_proba, n_reps=None, seed: int = 42):
    """Stratified bootstrap CI for holdout ROC-AUC (percentile bounds).

    Positives and negatives are resampled separately with
    ``default_rng(seed)``; returns the 2.5 and 97.5 percentile bounds.
    """
    if n_reps is None:
        n_reps = int(load_config()["data"].get("nhanes_bootstrap_reps", 2000))
    y = np.asarray(y_true)
    p = np.asarray(y_proba, dtype=float)
    pos = np.flatnonzero(y == 1)
    neg = np.flatnonzero(y == 0)
    rng = np.random.default_rng(seed)
    aucs = []
    for _ in range(int(n_reps)):
        idx = np.concatenate(
            [
                rng.choice(pos, len(pos), replace=True),
                rng.choice(neg, len(neg), replace=True),
            ]
        )
        aucs.append(roc_auc_score(y[idx], p[idx]))
    lo, hi = np.percentile(aucs, [2.5, 97.5])
    return float(lo), float(hi)


def sweep_native(
    X_dev: pd.DataFrame,
    y_dev: pd.Series,
    numeric_cols: list,
    categorical_cols: list,
) -> dict:
    """CV-mean sweep over all 9 configs (in-memory; no MLflow, no holdout)."""
    results = {}
    for name in NATIVE_ESTIMATORS:
        cv = run_cv_native(name, X_dev, y_dev, numeric_cols, categorical_cols)
        log.info(
            f"CV native-{name}: mean_auc={cv['mean_auc']:.4f} "
            f"std={cv['std_auc']:.4f}"
        )
        results[name] = cv
    return results


def select_by_cv(cv_results: dict) -> str:
    """Strict-max on CV-mean ROC-AUC. No tie-break logic by design."""
    return max(cv_results, key=lambda n: cv_results[n]["mean_auc"])


def threshold_for_recall(y_true, y_proba, target_recall: float) -> float:
    """Highest probability cut-off that still reaches ``target_recall``.

    Candidate cut-offs are the observed probabilities themselves, so the
    result is reproducible and needs no grid. Because the candidates are
    walked high-to-low, the *first* one that reaches the target is also the
    most specific one; using the last would land on every-row-positive.
    """
    if not 0 < target_recall <= 1:
        raise ValueError("target_recall must be in (0, 1]")
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(y_proba, dtype=float)
    total_pos = int(y.sum())
    if total_pos == 0:
        raise ValueError("cannot target a recall with no positive labels")

    order = np.argsort(-p)
    proba_sorted = p[order]
    tp = np.cumsum(y[order])
    reaching = np.flatnonzero(tp / total_pos >= target_recall)
    if reaching.size == 0:  # unreachable only via float slop; take the floor
        return 0.0
    return float(proba_sorted[reaching[0]])


def run_experiment_native(name: str = "logistic-regression", cv_stats: dict = None) -> dict:
    """Refit the winning config on full dev, score the holdout once, log Claim-2."""
    X, y, numeric_cols, categorical_cols, cycle = load_native_frame()
    assert_quarantine(X)  # gate on the training frame, before any split or fit

    X_dev, X_hold, y_dev, y_hold = split_native(X, y, cycle)
    if cv_stats is None:
        cv_stats = run_cv_native(name, X_dev, y_dev, numeric_cols, categorical_cols)

    pipeline = build_native_pipeline(numeric_cols, categorical_cols)
    pipeline.fit(X_dev)  # fit on dev only (leak-safe)
    X_hold_t = pipeline.transform(X_hold)

    estimator = build_native_estimator(name)
    _fit_native(estimator, pipeline.transform(X_dev), y_dev, name)
    y_proba = estimator.predict_proba(X_hold_t)[:, 1]

    cfg = load_config()
    target_recall = float(cfg["data"].get("nhanes_target_recall", 0.80))
    oof = cv_stats.get("oof_proba")
    if oof is not None and not np.isnan(oof).any():
        # Chosen on dev out-of-fold probabilities only: the holdout below is
        # scored with a cut-off that never saw it.
        threshold = threshold_for_recall(y_dev, oof, target_recall)
    else:
        threshold = 0.5
        log.warning("no out-of-fold probabilities; falling back to threshold 0.5")

    y_pred = (y_proba >= threshold).astype(int)
    metrics = compute_metrics(y_hold, y_pred, y_proba)
    ci_lo, ci_hi = bootstrap_auc_ci(y_hold, y_proba)
    # Keep the previous default operating point alongside the deployed one so
    # this run stays directly comparable with every earlier native run.
    y_pred_default = (y_proba >= 0.5).astype(int)
    pr_auc = float(average_precision_score(y_hold, y_proba))
    brier = float(brier_score_loss(y_hold, y_proba))

    pipeline_path = Path(cfg["data"]["processed_dir"]) / NATIVE_PIPELINE_FILENAME
    pipeline_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, pipeline_path)
    holdout_path = Path(cfg["data"]["processed_dir"]) / HOLDOUT_PREDS_FILENAME
    pd.DataFrame(
        {
            "row_id": np.asarray(X_hold.index),
            "y_true": np.asarray(y_hold, dtype=int),
            "y_proba": np.asarray(y_proba, dtype=float),
        }
    ).to_csv(holdout_path, index=False)

    threshold_path = Path(cfg["data"]["processed_dir"]) / THRESHOLD_FILENAME
    threshold_path.write_text(
        json.dumps(
            {
                "threshold": threshold,
                "target_recall": target_recall,
                "selected_on": "dev_out_of_fold",
                "config": name,
                "holdout_precision": float(metrics["precision"]),
                "holdout_recall": float(metrics["recall"]),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))
    mlflow.set_experiment(cfg["mlflow"]["nhanes_experiment_name"])
    with mlflow.start_run(run_name=f"native-{name}") as run:
        mlflow.set_tag("schema", "nhanes-native")
        mlflow.set_tag("label_disclosure", DERIVED_LABEL_DISCLOSURE)
        mlflow.set_tag("quarantine_attested", "true")
        mlflow.log_params({**estimator.get_params(), "model": type(estimator).__name__})
        mlflow.log_metrics(
            {
                **metrics,
                "holdout_roc_auc": metrics["roc_auc"],
                "cv_mean_auc": cv_stats["mean_auc"],
                "cv_std_auc": cv_stats["std_auc"],
                "holdout_auc_ci_lo": ci_lo,
                "holdout_auc_ci_hi": ci_hi,
                "holdout_pr_auc": pr_auc,
                "holdout_brier": brier,
                "decision_threshold": threshold,
                "target_recall": target_recall,
                "holdout_precision_at_0_50": float(
                    precision_score(y_hold, y_pred_default, zero_division=0)
                ),
                "holdout_recall_at_0_50": float(
                    recall_score(y_hold, y_pred_default, zero_division=0)
                ),
            }
        )
        mlflow.log_artifact(str(pipeline_path), artifact_path="preprocessing")
        mlflow.log_artifact(str(holdout_path), artifact_path="evaluation")
        mlflow.log_artifact(str(threshold_path), artifact_path=THRESHOLD_ARTIFACT_PATH)
        mlflow.sklearn.log_model(
            estimator,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME,
            serialization_format="cloudpickle",  # pin: 3.x default is skops
        )
        run_id = run.info.run_id
    log.info(f"Logged native run {name} ({run_id}) with metrics {metrics}")
    log.info(
        f"CV mean_auc={cv_stats['mean_auc']:.4f} "
        f"std={cv_stats['std_auc']:.4f}; holdout AUC CI [{ci_lo:.4f}, {ci_hi:.4f}]"
    )
    log.info(f"Disclosure: {DERIVED_LABEL_DISCLOSURE}")
    return {
        "run_id": run_id,
        "metrics": metrics,
        "features": list(X.columns),
        "cv": cv_stats,
        "ci": (ci_lo, ci_hi),
        "threshold": threshold,
    }


def main():
    X, y, numeric_cols, categorical_cols, cycle = load_native_frame()
    assert_quarantine(X)
    X_dev, X_hold, y_dev, y_hold = split_native(X, y, cycle)  # holdout sealed
    cv_results = sweep_native(X_dev, y_dev, numeric_cols, categorical_cols)
    print("CV SUMMARY (dev-only folds; holdout untouched):")
    for name, cv in cv_results.items():
        print(
            f"  native-{name} cv_mean_auc={cv['mean_auc']:.4f} "
            f"cv_std={cv['std_auc']:.4f}"
        )
    winner = select_by_cv(cv_results)
    result = run_experiment_native(winner, cv_stats=cv_results[winner])
    print(
        f"TRAINED native-{winner} roc_auc={result['metrics']['roc_auc']:.4f} "
        f"cv_mean={result['cv']['mean_auc']:.4f}"
    )
    print(f"Disclosure: {DERIVED_LABEL_DISCLOSURE}")


if __name__ == "__main__":
    main()
