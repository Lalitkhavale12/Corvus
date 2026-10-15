"""Phase 7 - native evaluation: paired comparison plus challenger staging (07-02).

Protocol: the challenger and v9 score the identical locked holdout rows
against the identical derived labels. v9 reads through the eval-only
``harmonize_v9`` adapter (documented handicap); the challenger's holdout
probabilities come from its own Claim-2 run artifact, so nothing native
is ever refit here and the holdout is never rescored. Promotion
qualifies iff the challenger holdout ROC-AUC strictly exceeds v9's, with
the paired-bootstrap difference CI shown. Staging moves the winner to
Staging and parks superseded challengers in Archived; Production is
never touched (the human gate in ``scripts/promote_challenger.py``
owns that boundary).

Invoked as ``python -m src.evaluation.evaluate_nhanes`` from the project
root with the challenger version (e.g. ``11``) as the argument.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.metrics import roc_auc_score

from src.preprocessing.preprocess_nhanes import (
    DERIVED_LABEL_DISCLOSURE,
    assert_quarantine,
    get_nhanes_column_lists,
    locked_holdout_split,
)
from src.training import harmonize_v9
from src.training.train_nhanes import HOLDOUT_PREDS_FILENAME, load_native_frame
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

REGISTERED_MODEL_NAME = "corvus-ckd"
V9_PINNED_VERSION = harmonize_v9.V9_PINNED_VERSION


def aggregate_cv(cv_results: dict) -> str:
    """Strict-max on CV-mean ROC-AUC. No tie-break logic by design."""
    return max(cv_results, key=lambda n: cv_results[n]["mean_auc"])


def paired_bootstrap_diff(y_true, p_challenger, p_v9, n_reps=None, seed: int = 42):
    """Paired bootstrap CI of (AUC challenger minus AUC v9).

    Holdout indices are resampled once per replicate and both models are
    scored on that resample, so the comparison is paired by construction.
    """
    if n_reps is None:
        n_reps = int(load_config()["data"].get("nhanes_bootstrap_reps", 2000))
    y = np.asarray(y_true)
    p_c = np.asarray(p_challenger, dtype=float)
    p_v = np.asarray(p_v9, dtype=float)
    if not (len(y) == len(p_c) == len(p_v)):
        raise ValueError(
            "Paired comparison needs identical row counts: "
            f"got {len(y)}, {len(p_c)}, {len(p_v)}"
        )
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(int(n_reps)):
        idx = rng.integers(0, len(y), len(y))
        diffs.append(roc_auc_score(y[idx], p_c[idx]) - roc_auc_score(y[idx], p_v[idx]))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {
        "diff": float(roc_auc_score(y, p_c) - roc_auc_score(y, p_v)),
        "lo": float(lo),
        "hi": float(hi),
    }


def compare_challenger(y_true, p_challenger, p_v9, n_reps=None, seed: int = 42):
    """Strict-greater promotion rule on identical rows and identical labels."""
    auc_c = float(roc_auc_score(y_true, p_challenger))
    auc_v = float(roc_auc_score(y_true, p_v9))
    boot = paired_bootstrap_diff(y_true, p_challenger, p_v9, n_reps, seed)
    qualifies = bool(auc_c > auc_v)
    log.info(
        f"Challenger holdout AUC={auc_c:.4f} vs v9 harmonized AUC={auc_v:.4f}; "
        f"diff CI [{boot['lo']:.4f}, {boot['hi']:.4f}]; qualifies={qualifies}"
    )
    log.info(f"Disclosure: {DERIVED_LABEL_DISCLOSURE}")
    return SimpleNamespace(
        success=True,
        challenger_auc=auc_c,
        v9_auc=auc_v,
        diff=boot["diff"],
        ci_lo=boot["lo"],
        ci_hi=boot["hi"],
        qualifies=qualifies,
        disclosure=DERIVED_LABEL_DISCLOSURE,
    )


def apply_challenger_stages(
    client, model_name: str, winner_version: str, superseded_versions: list,
    production_version: str,
) -> None:
    """Winner to Staging, superseded challengers to Archived, Production intact."""
    if production_version in ([str(winner_version)] + [str(v) for v in superseded_versions]):
        raise ValueError("Refusing: the Production version is not stageable here")
    before = client.get_model_version(model_name, str(production_version)).current_stage
    client.transition_model_version_stage(
        name=model_name,
        version=str(winner_version),
        stage="Staging",
        archive_existing_versions=True,
    )
    for version in superseded_versions:
        client.transition_model_version_stage(
            name=model_name, version=str(version), stage="Archived"
        )
    after = client.get_model_version(model_name, str(production_version)).current_stage
    if before != "Production" or after != "Production":
        raise RuntimeError(
            f"Production guard tripped: {production_version} {before} -> {after}"
        )


def run_evaluation(challenger_version: str, n_reps=None):
    """Paired comparison for one challenger version plus Staging transition."""
    cfg = load_config()
    mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))
    client = MlflowClient()
    try:
        X, y, _numeric, _categorical = load_native_frame()
        assert_quarantine(X)
        _dev, X_hold, _ydev, y_hold = locked_holdout_split(X, y)

        details = client.get_model_version(REGISTERED_MODEL_NAME, str(challenger_version))
        preds_path = mlflow.artifacts.download_artifacts(
            run_id=details.run_id, artifact_path=f"evaluation/{HOLDOUT_PREDS_FILENAME}"
        )
        stored = pd.read_csv(preds_path)
        if set(stored["row_id"]) != set(np.asarray(X_hold.index)):
            log.warning("Challenger artifact rows do not match the locked holdout")
            return SimpleNamespace(success=False, winner=None)
        stored = stored.set_index("row_id").loc[X_hold.index]
        if not np.array_equal(
            np.asarray(stored["y_true"], dtype=int), np.asarray(y_hold, dtype=int)
        ):
            log.warning("Challenger artifact labels differ from the locked holdout")
            return SimpleNamespace(success=False, winner=None)

        v9_model, v9_pipeline = harmonize_v9.load_v9_artifacts(V9_PINNED_VERSION)
        modes = harmonize_v9.fitted_categorical_modes(v9_pipeline)
        numeric_cols, _cats = get_nhanes_column_lists()
        harmonized = harmonize_v9.harmonize_frame(X_hold[numeric_cols + _cats], modes)
        p_v9 = harmonize_v9.score_frozen(v9_pipeline, v9_model, harmonized)
        p_challenger = np.asarray(stored["y_proba"], dtype=float)
        y_true = np.asarray(y_hold, dtype=int)

        comparison = compare_challenger(y_true, p_challenger, p_v9, n_reps)
        versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
        superseded = [
            v.version
            for v in versions
            if v.current_stage == "None" and str(v.version) != str(challenger_version)
        ]
        apply_challenger_stages(
            client,
            REGISTERED_MODEL_NAME,
            str(challenger_version),
            superseded,
            V9_PINNED_VERSION,
        )
        print(
            f"CHALLENGER v{challenger_version} holdout AUC={comparison.challenger_auc:.4f} "
            f"vs v9 harmonized AUC={comparison.v9_auc:.4f} "
            f"diff CI [{comparison.ci_lo:.4f}, {comparison.ci_hi:.4f}] "
            f"qualifies={comparison.qualifies}"
        )
        print(f"Disclosure: {DERIVED_LABEL_DISCLOSURE}")
        log.info(
            f"Challenger v{challenger_version} staged; "
            f"v{V9_PINNED_VERSION} remains Production"
        )
        return SimpleNamespace(
            success=True,
            qualifies=comparison.qualifies,
            challenger_version=str(challenger_version),
            challenger_auc=comparison.challenger_auc,
            v9_auc=comparison.v9_auc,
            ci_lo=comparison.ci_lo,
            ci_hi=comparison.ci_hi,
            disclosure=DERIVED_LABEL_DISCLOSURE,
        )
    except Exception as exc:
        log.warning(f"Native evaluation failed: {type(exc).__name__}: {exc}")
        return SimpleNamespace(success=False, winner=None)


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python -m src.evaluation.evaluate_nhanes <challenger_version>")
        return 1
    result = run_evaluation(args[0])
    if result.success:
        return 0
    print("NATIVE EVALUATION FAILED — see log for details")
    return 1


if __name__ == "__main__":
    sys.exit(main())
