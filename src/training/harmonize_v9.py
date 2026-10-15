"""Phase 7 - eval-only NHANES-to-UCI harmonization adapter (07-02).

Lets the frozen v9 champion score locked NHANES holdout rows it cannot
natively read (10 absent fields). Nine shared numeric fields are mapped
per the table below; v9's 10 categorical inputs are filled with the
frozen UCI pipeline's own most-frequent imputations; unmapped UCI
numerics ride through as NaN into v9's own fitted median imputer. The
resulting v9 score carries a documented handicap and exists only for
the paired same-rows same-labels comparison — never for serving.

EVAL-ONLY: ``api/`` must never import this module (enforced by
``test_adapter_not_served``). v9 artifacts load read-only at the pinned
version; this module never calls ``fit`` on anything.
"""

import os

import joblib
import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient

from src.preprocessing.preprocess import get_column_lists
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger

log = get_logger()

# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

REGISTERED_MODEL_NAME = "corvus-ckd"
V9_PINNED_VERSION = "9"

# UCI-24 name -> NHANES column. Unit notes record the correspondence
# assumption per field (conventional vs SI units are numerically
# identical where mmol/L meets mEq/L or 10^9/L meets 10^3/uL).
NHANES_TO_UCI_MAP = {
    "age": "RIDAGEYR",
    "bu": "LBDSBUSI",
    "bgr": "LBDSGLSI",
    "sod": "LBXSNASI",
    "pot": "LBXSKSI",
    "hemo": "LBXHGB",
    "pcv": "LBXHCT",
    "wc": "LBXWBCSI",
    "rc": "LBXRBCSI",
}

UNIT_NOTES = {
    # Demographics: years at screening on both sides.
    "age": "RIDAGEYR years; same unit as UCI age",
    # BUN conventional mg/dL; UCI bu is blood urea mg/dL.
    "bu": "LBDSBUSI BUN mg/dL; matches UCI bu mg/dL",
    # Serum glucose mg/dL on both sides (NHANES cycle draws are non-fasting).
    "bgr": "LBDSGLSI glucose mg/dL; matches UCI bgr mg/dL",
    # Electrolytes: NHANES reports mmol/L, UCI reports mEq/L — numerically
    # identical for monovalent Na and K.
    "sod": "LBXSNASI serum sodium mmol/L; numerically identical to UCI sod mEq/L",
    "pot": "LBXSKSI serum potassium mmol/L; numerically identical to UCI pot mEq/L",
    # Hemoglobin g/dL on both sides.
    "hemo": "LBXHGB hemoglobin g/dL; matches UCI hemo gms",
    # Hematocrit percent on both sides.
    "pcv": "LBXHCT hematocrit %; matches UCI pcv %",
    # WBC: NHANES SI x10^9/L == conventional x10^3/uL; UCI wc cells/cumm.
    "wc": "LBXWBCSI WBC SI x10^9/L; numerically identical to UCI wc cells/cumm",
    # RBC: NHANES SI x10^12/L == conventional x10^6/uL; UCI rc millions/cmm.
    "rc": "LBXRBCSI RBC SI x10^12/L; numerically identical to UCI rc millions/cmm",
}

# v9's 10 categorical inputs, filled with the frozen pipeline's own
# most-frequent imputations (documented handicap: v9 sees no real
# categorical signal on NHANES rows).
V9_CATEGORICALS = [
    "rbc",
    "pc",
    "pcc",
    "ba",
    "htn",
    "dm",
    "cad",
    "appet",
    "pe",
    "ane",
]


def load_v9_artifacts(version: str = V9_PINNED_VERSION):
    """Load v9's frozen estimator plus fitted UCI pipeline, read-only.

    No ``fit`` is ever called on NHANES data here or by any caller: the
    champion baseline stays exactly as promoted.
    """
    cfg = load_config()
    mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))
    client = MlflowClient()
    details = client.get_model_version(REGISTERED_MODEL_NAME, str(version))
    run_id = details.run_id
    model = mlflow.sklearn.load_model(
        f"models:/{REGISTERED_MODEL_NAME}/{version}"
    )
    pipe_path = mlflow.artifacts.download_artifacts(
        run_id=run_id,
        artifact_path="preprocessing/preprocessing_pipeline.joblib",
    )
    pipeline = joblib.load(pipe_path)
    log.info(
        f"Loaded frozen {REGISTERED_MODEL_NAME} version={version} "
        f"run_id={run_id} for eval-only harmonized scoring"
    )
    return model, pipeline


def fitted_categorical_modes(pipeline) -> dict:
    """Read the frozen UCI pipeline's own most-frequent fills per column."""
    preprocessor = pipeline.named_steps["preprocessor"]
    modes = {}
    for _name, transformer, columns in preprocessor.transformers_:
        steps = getattr(transformer, "named_steps", {})
        imputer = steps.get("imputer")
        stats = getattr(imputer, "statistics_", None)
        if stats is None:
            continue
        for col, fill in zip(columns, stats):
            if col in V9_CATEGORICALS:
                modes[col] = fill
    missing = set(V9_CATEGORICALS) - set(modes)
    if missing:
        raise ValueError(
            f"Frozen pipeline has no imputations for categoricals: {sorted(missing)}"
        )
    return modes


def harmonize_frame(nhanes_df: pd.DataFrame, modes: dict) -> pd.DataFrame:
    """Project NHANES rows onto the UCI-24 frame v9's pipeline expects.

    Mapped numerics are coerced with ``pd.to_numeric(errors="coerce")``;
    unmapped UCI numerics stay NaN for v9's own fitted median imputer;
    categoricals take the frozen most-frequent fills. Immutable inputs.
    """
    df = nhanes_df.copy()
    numeric_cols, categorical_cols = get_column_lists()
    out = pd.DataFrame(index=df.index)
    for col in numeric_cols:
        nh_col = NHANES_TO_UCI_MAP.get(col)
        if nh_col is not None and nh_col in df.columns:
            out[col] = pd.to_numeric(df[nh_col], errors="coerce")
        else:
            out[col] = np.nan  # frozen median imputer fills downstream
    for col in categorical_cols:
        out[col] = modes[col]
    return out[numeric_cols + categorical_cols]


def score_frozen(pipeline, model, harmonized_df: pd.DataFrame):
    """Score harmonized rows through frozen artifacts (transform + proba)."""
    proba = model.predict_proba(pipeline.transform(harmonized_df))[:, 1]
    return np.asarray(proba, dtype=float)
