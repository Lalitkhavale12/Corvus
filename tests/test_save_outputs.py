"""
save_outputs() integration test for Phase 1. Builds a synthetic CKD-shaped
frame, runs the real clean/split/fit path, then redirects persistence into an
isolated tmp dir via a monkeypatched load_config. Never reads the real raw
file; the real processed dir is snapshotted before and after to prove it is
untouched.
"""
import copy

import joblib
import pandas as pd
import pytest

import src.preprocessing.preprocess as preprocess_mod
from src.preprocessing.preprocess import (
    clean_raw,
    split_raw,
    fit_transform_split,
    save_outputs,
    NUMERIC_COLS,
    CATEGORICAL_COLS,
)
from src.utils.config import load_config


def _snapshot_dir(path):
    """Map each file under path to (size, mtime) for byte-level comparison."""
    snap = {}
    if path.exists():
        for child in sorted(path.iterdir()):
            if child.is_file():
                snap[child.name] = (child.stat().st_size, child.stat().st_mtime_ns)
    return snap


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


def test_save_outputs_round_trip_isolated(tmp_path, monkeypatch, synthetic_df):
    real_cfg = load_config()
    from pathlib import Path as _Path

    real_processed = _Path(real_cfg["data"]["processed_dir"])
    before = _snapshot_dir(real_processed)

    cleaned = clean_raw(synthetic_df)
    X_train, X_val, X_test, y_train, y_val, y_test = split_raw(cleaned)
    pipeline, splits, ys = fit_transform_split(
        X_train, X_val, X_test, y_train, y_val, y_test
    )

    override = copy.deepcopy(real_cfg)
    override["data"]["processed_dir"] = str(tmp_path)
    load_config.cache_clear()
    monkeypatch.setattr(preprocess_mod, "load_config", lambda *a, **k: override)

    save_outputs(pipeline, splits, ys)

    # All four artifacts exist under the isolated dir.
    for name in ("train.csv", "val.csv", "test.csv"):
        assert (tmp_path / name).exists()
    assert (tmp_path / "preprocessing_pipeline.joblib").exists()

    # Row counts conserve exactly.
    train_df = pd.read_csv(tmp_path / "train.csv")
    val_df = pd.read_csv(tmp_path / "val.csv")
    test_df = pd.read_csv(tmp_path / "test.csv")
    assert len(train_df) + len(val_df) + len(test_df) == len(cleaned)
    assert len(train_df) == len(splits[0])
    assert len(val_df) == len(splits[1])
    assert len(test_df) == len(splits[2])

    # The reloaded artifact transforms held-out features without error.
    reloaded = joblib.load(tmp_path / "preprocessing_pipeline.joblib")
    reloaded.transform(X_test)

    # The real output dir is byte-identical before and after.
    assert _snapshot_dir(real_processed) == before
