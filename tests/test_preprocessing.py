"""
Smoke tests for Phase 1 preprocessing. Uses a small synthetic frame shaped
like the UCI CKD dataset so tests don't depend on the real file being present.
Also asserts the leakage fix and Claim 2 pipeline-artifact behavior directly,
since those were the two things this module was refactored to fix.
"""
import numpy as np
import pandas as pd
import pytest

from src.preprocessing.preprocess import (
    clean_raw, split_raw, build_pipeline, fit_transform_split,
    get_column_lists,
)
from src.preprocessing.preprocess import (
    NUMERIC_COLS as _LEGACY_NUMERIC_COLS,
    CATEGORICAL_COLS as _LEGACY_CATEGORICAL_COLS,
)
from sklearn.pipeline import Pipeline

NUMERIC_COLS, CATEGORICAL_COLS = get_column_lists()


@pytest.fixture
def synthetic_df():
    n = 40
    data = {col: [float(i % 5) for i in range(n)] for col in NUMERIC_COLS}
    for col in CATEGORICAL_COLS:
        data[col] = ["yes" if i % 2 == 0 else "no" for i in range(n)]
    data["classification"] = ["ckd" if i % 3 == 0 else "notckd" for i in range(n)]
    df = pd.DataFrame(data)
    df.loc[0, NUMERIC_COLS[0]] = None
    df.loc[1, CATEGORICAL_COLS[0]] = None
    return df


def test_column_lists_come_from_config():
    """Column groups must match config.yaml (single source of truth)."""
    from src.utils.config import load_config

    cfg = load_config()
    assert NUMERIC_COLS == cfg["data"]["numeric_cols"]
    assert CATEGORICAL_COLS == cfg["data"]["categorical_cols"]
    # Legacy aliases still exist for old imports.
    assert _LEGACY_NUMERIC_COLS == NUMERIC_COLS
    assert _LEGACY_CATEGORICAL_COLS == CATEGORICAL_COLS


def test_clean_raw_no_missing_target(synthetic_df):
    cleaned = clean_raw(synthetic_df)
    assert cleaned["classification"].isna().sum() == 0
    assert set(cleaned["classification"].unique()) <= {0, 1}


def test_split_before_fit_no_overlap(synthetic_df):
    cleaned = clean_raw(synthetic_df)
    X_train, X_val, X_test, y_train, y_val, y_test = split_raw(cleaned)
    train_idx, val_idx, test_idx = set(X_train.index), set(X_val.index), set(X_test.index)
    assert train_idx.isdisjoint(val_idx)
    assert train_idx.isdisjoint(test_idx)
    assert val_idx.isdisjoint(test_idx)


def test_pipeline_is_single_sklearn_object(synthetic_df):
    """Patent Claim 2: preprocessing must be one fitted, serializable object."""
    cleaned = clean_raw(synthetic_df)
    X_train, X_val, X_test, y_train, y_val, y_test = split_raw(cleaned)
    pipeline, splits, ys = fit_transform_split(X_train, X_val, X_test, y_train, y_val, y_test)
    assert isinstance(pipeline, Pipeline)
    # fitted: transform should work without raising NotFittedError
    pipeline.transform(X_test)


def test_fit_only_on_train_not_val_or_test(synthetic_df):
    """
    Leakage proof: the fitted numeric imputer's statistics must equal the
    TRAIN medians exactly — i.e. .fit() saw X_train and nothing else.
    """
    cleaned = clean_raw(synthetic_df)
    X_train, X_val, X_test, y_train, y_val, y_test = split_raw(cleaned)
    pipeline, splits, ys = fit_transform_split(X_train, X_val, X_test, y_train, y_val, y_test)
    train_df, val_df, test_df = splits
    assert len(train_df) == len(X_train)
    assert len(val_df) == len(X_val)
    assert len(test_df) == len(X_test)
    assert train_df.isna().sum().sum() == 0
    assert val_df.isna().sum().sum() == 0
    assert test_df.isna().sum().sum() == 0

    num_transformer = pipeline.named_steps["preprocessor"].named_transformers_["num"]
    imputer = num_transformer.named_steps["imputer"]
    expected_medians = X_train[NUMERIC_COLS].apply(
        lambda s: pd.to_numeric(s, errors="coerce").median()
    ).to_numpy(dtype=float)
    assert np.allclose(imputer.statistics_, expected_medians, equal_nan=True)
