"""
Validation-gate tests for Phase 1. All frames are synthetic in-memory builds
covering the suite contract (label domain, target presence, row-count range);
the real raw file is never touched. The runner is imported from the validation
module via a sys.path insert because that directory is not a package.
"""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "data" / "validation"))

from validate import run_raw_validation  # noqa: E402

ALL_COLUMNS = [
    "age", "al", "ane", "appet", "ba", "bgr", "bp", "bu", "cad",
    "classification", "dm", "hemo", "htn", "id", "pc", "pcc", "pcv",
    "pe", "pot", "rbc", "rc", "sc", "sg", "sod", "su", "wc",
]
CATEGORICAL_like = ["rbc", "pc", "pcc", "ba", "htn", "dm", "cad", "appet", "pe", "ane"]


def _good_frame(n=320):
    data = {}
    for col in ALL_COLUMNS:
        if col == "classification":
            data[col] = ["ckd" if i % 3 == 0 else "notckd" for i in range(n)]
        elif col == "id":
            data[col] = [f"row-{i}" for i in range(n)]
        elif col in CATEGORICAL_like:
            data[col] = ["yes" if i % 2 == 0 else "no" for i in range(n)]
        else:
            data[col] = [float(i % 7) for i in range(n)]
    return pd.DataFrame(data)


def test_good_frame_accepted():
    result = run_raw_validation(_good_frame())
    assert result.success is True


def test_unknown_label_rejected():
    df = _good_frame()
    df.loc[0, "classification"] = "maybe"
    result = run_raw_validation(df)
    assert result.success is False


def test_missing_target_column_rejected():
    df = _good_frame().drop(columns=["classification"])
    result = run_raw_validation(df)
    assert result.success is False


def test_tiny_frame_rejected():
    result = run_raw_validation(_good_frame(n=2))
    assert result.success is False
