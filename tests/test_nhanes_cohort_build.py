"""Golden test for the NHANES cohort builder.

The locked training cohort (5343 rows) was produced ad-hoc and never
reproducible from raw files. Before adding cycles, the builder must prove it
regenerates that cohort exactly from the cycle L XPTs on disk.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.build_nhanes_cohort import (
    LOCKED_CSV,
    RAW_DIR,
    contract_columns,
    extract_cycle,
)
from src.preprocessing.preprocess_nhanes import cycle_holdout_split

pytestmark = pytest.mark.skipif(
    not (RAW_DIR / "DEMO_L.xpt").exists(), reason="raw NHANES XPTs not present"
)


@pytest.fixture(scope="module")
def built():
    return extract_cycle("L")


@pytest.fixture(scope="module")
def locked():
    return pd.read_csv(LOCKED_CSV)


def test_cycle_l_reproduces_locked_cohort(built, locked):
    assert len(built) == len(locked), f"{len(built)} built vs {len(locked)} locked"
    assert set(built["SEQN"]) == set(locked["SEQN"])


def test_label_matches_locked(built, locked):
    merged = built.merge(locked[["SEQN", "ckd"]], on="SEQN", suffixes=("", "_locked"))
    assert (merged["ckd"] == merged["ckd_locked"]).all()
    assert merged["ckd"].sum() == locked["ckd"].sum()


def test_contract_values_match_locked(built, locked):
    cols = contract_columns()
    merged = built.merge(locked[["SEQN", *cols]], on="SEQN", suffixes=("", "_locked"))
    for col in cols:
        pd.testing.assert_series_equal(
            merged[col].reset_index(drop=True),
            merged[f"{col}_locked"].reset_index(drop=True),
            check_names=False,
            check_dtype=False,
            atol=1e-6,
            obj=f"column {col}",
        )


def test_cycle_holdout_split_selects_whole_cycle():
    X = pd.DataFrame({"a": range(6)})
    y = pd.Series([0, 1, 0, 1, 0, 1])
    cycle = pd.Series([9, 9, 9, 9, 12, 12])

    X_dev, X_hold, y_dev, y_hold = cycle_holdout_split(X, y, cycle, 12)

    assert list(X_hold["a"]) == [4, 5]
    assert list(y_hold) == [0, 1]
    assert list(X_dev["a"]) == [0, 1, 2, 3]
    assert list(y_dev) == [0, 1, 0, 1]
