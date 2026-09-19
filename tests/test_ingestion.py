"""
Ingestion tests for Phase 1. Every input is a synthetic CSV written to tmp_path;
nothing here reads the real raw file. Quirk normalization is asserted through
the real loader and summarize functions — the quirk-handling logic itself
is never duplicated in this file.
"""
import pandas as pd
import pytest
import yaml

import src.ingestion.load_data as load_data_mod
from src.ingestion.load_data import load_raw_data, summarize
from src.utils.config import load_config


def _write_quirky_csv(path):
    """Synthetic CSV carrying the known UCI CKD quirks in miniature."""
    lines = [
        " age ,rbc,classification ",
        "25,?,\tckd",
        "30, ? ,notckd ",
        " 120 , yes, ckd",
        "80,\tno,notckd",
        "45,abnormal, ckd\t",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_question_mark_cells_load_as_missing(tmp_path):
    quirky = _write_quirky_csv(tmp_path / "quirky.csv")
    df = load_raw_data(str(quirky))
    # Bare "?" and padded " ? " both normalize to missing.
    assert df["rbc"].isna().sum() == 2
    assert df["rbc"].dropna().tolist() == ["yes", "no", "abnormal"]


def test_whitespace_and_tab_affixes_stripped(tmp_path):
    quirky = _write_quirky_csv(tmp_path / "quirky.csv")
    df = load_raw_data(str(quirky))
    # Column names are stripped.
    assert list(df.columns) == ["age", "rbc", "classification"]
    # Tab-prefixed/trailing label variants normalize to the plain domain.
    assert set(df["classification"].tolist()) == {"ckd", "notckd"}
    # Whitespace-padded values are stripped.
    assert set(df["rbc"].dropna().tolist()) == {"yes", "no", "abnormal"}
    # Numeric-as-string cells with padding survive as the same numbers.
    assert set(df["age"].astype(str).tolist()) == {"25", "30", "120", "80", "45"}
    # No surviving string cell carries leading/trailing whitespace.
    for col in df.select_dtypes(include=["object", "string"]).columns:
        for value in df[col].dropna().tolist():
            assert value == value.strip()


def test_summarize_shape_sorted_and_bounded():
    df = pd.DataFrame(
        {
            "a": [1.0, None, None, 3.0],  # 50% missing
            "b": ["x", "y", "x", None],  # 25% missing
            "c": [1, 2, 3, 4],  # 0% missing
        }
    )
    summary = summarize(df)
    assert list(summary.columns) == ["dtype", "missing_count", "missing_pct", "n_unique"]
    assert summary.loc["a", "missing_pct"] == 50.0
    assert summary.loc["b", "missing_pct"] == 25.0
    assert summary.loc["c", "missing_pct"] == 0.0
    assert summary.loc["a", "missing_count"] == 2
    # Descending sort by missing_pct.
    assert summary["missing_pct"].tolist() == [50.0, 25.0, 0.0]
    assert summary.index[0] == "a"
    # Percentages are bounded.
    assert ((summary["missing_pct"] >= 0) & (summary["missing_pct"] <= 100)).all()


def test_config_override_redirects_default_path(tmp_path, monkeypatch):
    quirky = _write_quirky_csv(tmp_path / "quirky.csv")
    override_path = tmp_path / "override.yaml"
    override_path.write_text(
        yaml.safe_dump({"data": {"raw_path": str(quirky)}}), encoding="utf-8"
    )
    parsed = yaml.safe_load(override_path.read_text(encoding="utf-8"))
    load_config.cache_clear()
    monkeypatch.setattr(load_data_mod, "load_config", lambda *a, **k: parsed)
    df = load_raw_data()
    assert list(df.columns) == ["age", "rbc", "classification"]
    assert df["rbc"].isna().sum() == 2
