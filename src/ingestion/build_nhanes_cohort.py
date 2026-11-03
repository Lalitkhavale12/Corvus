"""Build the NHANES CKD cohort from raw CDC XPT files.

The locked 5,343-row cohort was produced by an ad-hoc join that was never kept,
which made adding cycles impossible. This rebuilds it from the XPTs on disk and
is validated by tests/test_nhanes_cohort_build.py against that locked file.

Label rule (unchanged): ckd = 1 iff eGFR < 60 (CKD-EPI 2021, race-free) or
ACR >= 30, among adults 20+. Both are single-measure KDIGO proxies, and eGFR /
ACR stay quarantined from model inputs.

Usage:
    python -m src.ingestion.build_nhanes_cohort L
    python -m src.ingestion.build_nhanes_cohort J L
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.preprocessing.preprocess_nhanes import get_nhanes_column_lists
from src.utils.logger import get_logger

logger = get_logger()

RAW_DIR = Path("data/nhanes")
LOCKED_CSV = RAW_DIR / "nhanes_ckd_derived.csv"
MULTI_CSV = RAW_DIR / "nhanes_ckd_multi.csv"

# Only the components the 23-field contract needs. GLU and MCQ are not read.
COMPONENT_COLUMNS: dict[str, list[str]] = {
    "DEMO": ["SEQN", "RIDAGEYR", "RIAGENDR", "INDFMPIR", "DMDEDUC2", "SDDSRVYR"],
    "BIOPRO": [
        "SEQN",
        "LBXSCR",
        "LBDSBUSI",
        "LBDSGLSI",
        "LBXSNASI",
        "LBXSKSI",
        "LBDSCASI",
        "LBDSPHSI",
        "LBDSUASI",
        "LBXSAL",
        "LBXSGTSI",
    ],
    "ALB_CR": ["SEQN", "URXUMA", "URXUCR"],
    "BMX": ["SEQN", "BMXBMI"],
    "BPXO": ["SEQN", "BPXOSY1", "BPXODI1"],
    "DIQ": ["SEQN", "DIQ010"],
    "GHB": ["SEQN", "LBXGH"],
    "CBC": ["SEQN", "LBXHGB", "LBXHCT", "LBXWBCSI", "LBXRBCSI", "LBXRDW"],
}

# Fallback only; DEMO's own SDDSRVYR wins when present.
CYCLE_SDDSRVYR = {"G": 7, "H": 8, "I": 9, "J": 10, "L": 12}

# Cycles before 2017 measured blood pressure with the manual device, so the
# component and its columns are named BPX / BPXSY1 / BPXDI1 instead.
LEGACY_BP_CYCLES = frozenset({"G", "H", "I"})
LEGACY_BP = {
    "component": "BPX",
    "columns": ["SEQN", "BPXSY1", "BPXDI1"],
    "rename": {"BPXSY1": "BPXOSY1", "BPXDI1": "BPXODI1"},
}


def contract_columns() -> list[str]:
    """The ordered native inputs the model consumes."""
    numeric, categorical = get_nhanes_column_lists()
    return numeric + categorical


def _read(component: str, suffix: str) -> pd.DataFrame:
    spec = dict(
        component=component,
        columns=COMPONENT_COLUMNS[component],
        rename={},
    )
    if component == "BPXO" and suffix in LEGACY_BP_CYCLES:
        spec = LEGACY_BP

    path = RAW_DIR / f"{spec['component']}_{suffix}.xpt"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing; download {path.name} from wwwn.cdc.gov"
        )
    frame = pd.read_sas(path, format="xport")
    wanted = spec["columns"]
    missing = [c for c in wanted if c not in frame.columns]
    if missing:
        raise KeyError(f"{path.name} lacks {missing}")
    frame = frame[wanted].copy()
    return frame.rename(columns=spec["rename"])


def ckd_epi_2021(scr: pd.Series, age: pd.Series, female: pd.Series) -> pd.Series:
    """Race-free 2021 creatinine equation."""
    k = np.where(female, 0.7, 0.9)
    alpha = np.where(female, -0.241, -0.302)
    return (
        142
        * np.minimum(scr / k, 1) ** alpha
        * np.maximum(scr / k, 1) ** -1.200
        * 0.9938**age
        * np.where(female, 1.012, 1.0)
    )


def extract_cycle(suffix: str) -> pd.DataFrame:
    """One cycle, filtered to adults with the three label inputs present."""
    parts = [_read(name, suffix) for name in COMPONENT_COLUMNS]
    frame = parts[0]
    for part in parts[1:]:
        frame = frame.merge(part, on="SEQN", how="inner")

    frame["female"] = frame["RIAGENDR"] == 2
    frame["eGFR"] = ckd_epi_2021(frame["LBXSCR"], frame["RIDAGEYR"], frame["female"])
    frame["ACR"] = 100 * frame["URXUMA"] / frame["URXUCR"]

    keep = (
        (frame["RIDAGEYR"] >= 20)
        & frame[["LBXSCR", "URXUMA", "URXUCR"]].notna().all(axis=1)
    )
    frame = frame[keep].drop(columns="female").reset_index(drop=True)

    frame["ckd"] = ((frame["eGFR"] < 60) | (frame["ACR"] >= 30)).astype(int)
    if "SDDSRVYR" not in frame:
        frame["SDDSRVYR"] = CYCLE_SDDSRVYR.get(suffix, np.nan)
    frame = frame.drop_duplicates(subset="SEQN")
    return frame[["SEQN", "SDDSRVYR", "ckd", "eGFR", "ACR", *contract_columns()]]


def build(suffixes: list[str], output: Path) -> pd.DataFrame:
    frames = []
    for suffix in suffixes:
        one = extract_cycle(suffix)
        logger.info(
            f"cycle {suffix}: {len(one)} adults, "
            f"{one['ckd'].mean():.1%} positive"
        )
        frames.append(one)
    cohort = pd.concat(frames, ignore_index=True)
    if output.exists() and output == LOCKED_CSV:
        raise SystemExit(f"{output} is the locked cohort; it is never overwritten")
    cohort.to_csv(output, index=False)
    logger.info(
        f"wrote {output}: {len(cohort)} rows, {cohort['ckd'].sum()} positives "
        f"({cohort['ckd'].mean():.1%}), cycles {suffixes}"
    )
    return cohort


def demo() -> None:
    """Self-check on the arithmetic that defines the label."""
    egfr = ckd_epi_2021(pd.Series([0.9]), pd.Series([40]), pd.Series([False]))
    assert abs(float(egfr.iloc[0]) - 110.7) < 0.2, egfr.iloc[0]
    assert abs(float(100 * 30 / 100) - 30) < 1e-9
    print("demo OK: eGFR(0.9 mg/dL, 40y male) =", round(float(egfr.iloc[0]), 1))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        cycles = sys.argv[1:] or ["L"]
        out = MULTI_CSV if len(cycles) > 1 else LOCKED_CSV.with_name(f"nhanes_ckd_{cycles[0]}.csv")
        build(cycles, out)
