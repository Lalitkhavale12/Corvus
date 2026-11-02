"""Phase 7 - NHANES-native preprocessing.

Native-schema counterpart to ``src/preprocessing/preprocess.py``: column
lists come from the additive ``data.nhanes_*`` config keys (merged v2
derivation per D-01, unweighted per D-02), a hard quarantine gate aborts
training before any split when any of the 11 banned columns is present,
and the locked 20 percent holdout is split once with a fixed seed.

Every metric logged or reported from this phase carries
``DERIVED_LABEL_DISCLOSURE`` next to the numbers (D-08): the labels are
KDIGO-derived from single-measure eGFR/ACR, not clinical diagnoses, and
results are internal-only on unweighted NHANES 2021-2023 data.
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from src.feature_engineering.nhanes_features import (
    ENGINEERED_COLS,
    derive_nhanes_features,
)
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()

# Banned from model inputs — violation aborts training (NHANES_PROTOCOL.md).
# Every one of these participated in the label rule directly or via CKD-EPI.
QUARANTINE_11 = frozenset(
    {
        "eGFR",
        "URXUMA",
        "URXUMS",
        "URXUCR",
        "URXCRS",
        "URDACT",
        "URDUMALC",
        "URDUCRLC",
        "LBXSCR",
        "LBDSCRSI",
        "ACR",
    }
)

# D-08 disclosure string, defined once here and reused everywhere metrics
# are logged or reported in this phase.
DERIVED_LABEL_DISCLOSURE = (
    "Labels are KDIGO-derived from single-measure eGFR/ACR, not clinical "
    "diagnoses; metrics are internal-only on unweighted NHANES 2021-2023 data."
)


def get_nhanes_column_lists() -> tuple[list[str], list[str]]:
    """Native numeric/categorical column lists from config (single source)."""
    cfg = load_config()
    numeric = list(cfg["data"]["nhanes_numeric_cols"])
    categorical = list(cfg["data"]["nhanes_categorical_cols"])
    return numeric, categorical


def assert_quarantine(df: pd.DataFrame) -> None:
    """Abort before any split or fit when a quarantined column is present.

    Call this on the TRAINING frame (the allow-list projection), not the
    raw CSV: the locked derived CSV carries the quarantined label-source
    columns by design, and the allow-list projection drops them. Any
    banned name surviving into the training frame — or present in the
    configured allow-list itself — raises ``SystemExit`` (fail-closed);
    this is the one deliberate exception to the warning-not-crash rule.
    """
    numeric, categorical = get_nhanes_column_lists()
    breach_cfg = QUARANTINE_11 & (set(numeric) | set(categorical))
    if breach_cfg:
        raise SystemExit(
            "QUARANTINE BREACH in config allow-list — aborting: "
            f"{sorted(breach_cfg)}"
        )
    breach = QUARANTINE_11 & set(df.columns)
    if breach:
        raise SystemExit(f"QUARANTINE BREACH — aborting: {sorted(breach)}")


def build_native_pipeline(
    numeric_cols: list[str] | None = None,
    categorical_cols: list[str] | None = None,
) -> Pipeline:
    """Return an UNFITTED native pipeline; caller fits it on dev only.

    Numerics: median impute + StandardScaler. Categoricals: most-frequent
    impute + OneHotEncoder(handle_unknown="ignore", drop="first").

    The first step derives the engineered clinical features from the raw
    allow-list. Deriving inside the pipeline (rather than baking the
    columns into the training frame) keeps the serving contract equal to
    the raw 20+5 allow-list: the API posts raw labs, the pipeline expands
    them, so a co-logged artifact cannot drift from the estimator width.
    """
    if numeric_cols is None or categorical_cols is None:
        cfg_numeric, cfg_categorical = get_nhanes_column_lists()
        numeric_cols = cfg_numeric if numeric_cols is None else numeric_cols
        categorical_cols = (
            cfg_categorical if categorical_cols is None else categorical_cols
        )
    cfg = load_config()

    # Engineered names are appended here, never to data.nhanes_numeric_cols:
    # that config list is the raw serving contract read by the API probe.
    numeric_cols = list(numeric_cols) + [
        col for col in ENGINEERED_COLS if col not in numeric_cols
    ]

    numeric_steps = [
        (
            "imputer",
            SimpleImputer(strategy=cfg["preprocessing"]["numeric_impute_strategy"]),
        )
    ]
    if cfg["preprocessing"]["scale_numeric"]:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric_pipeline = Pipeline(numeric_steps)

    categorical_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy=cfg["preprocessing"]["categorical_impute_strategy"]
                ),
            ),
            ("encoder", OneHotEncoder(handle_unknown="ignore", drop="first")),
        ]
    )

    transformers = []
    if numeric_cols:
        transformers.append(("num", numeric_pipeline, numeric_cols))
    if categorical_cols:
        transformers.append(("cat", categorical_pipeline, categorical_cols))

    preprocessor = ColumnTransformer(transformers)
    return Pipeline(
        [
            ("features", FunctionTransformer(derive_nhanes_features, validate=False)),
            ("preprocessor", preprocessor),
        ]
    )


def locked_holdout_split(
    X: pd.DataFrame, y: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Single locked split: 80 percent dev, 20 percent holdout (seed 42).

    The holdout is sealed — no pipeline or estimator is ever fitted on it.
    """
    cfg = load_config()
    test_size = cfg["data"].get("nhanes_holdout_size", 0.2)
    random_state = cfg["data"].get("nhanes_random_state", 42)
    return train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
