"""Native-schema clinical feature derivation for the NHANES CKD model.

Derivations run INSIDE the fitted sklearn pipeline
(``preprocess_nhanes.build_native_pipeline``), never as a pre-step on the
training frame. That keeps the serving contract equal to the raw allow-list:
the API posts raw labs, the pipeline expands them, so a co-logged artifact
can never drift from the estimator's ``n_features_in_``.

Each engineered column is an interaction or ratio that a single raw lab
cannot express: pulse pressure and MAP isolate vascular stiffness from the
two pressures, MCHC separates haemoglobin from haematocrit, RDW/HGB scales
red-cell variability by oxygen-carrying capacity, BUN/albumin contrasts the
nitrogen load against the protein stores, and age x HbA1c measures
cumulative glycaemic exposure rather than a point-in-time value.

No derived column may read a quarantined label source (eGFR, creatinine,
albuminuria); every input below is a member of the non-quarantined
allow-list, which ``assert_quarantine`` re-checks on the training frame.
"""

import numpy as np
import pandas as pd

# name -> raw allow-list inputs, so provenance stays auditable in one place.
ENGINEERED_FEATURES = {
    "f_pulse_pressure": ("BPXOSY1", "BPXODI1"),
    "f_map": ("BPXOSY1", "BPXODI1"),
    "f_mchc": ("LBXHGB", "LBXHCT"),
    "f_rdw_hgb": ("LBXRDW", "LBXHGB"),
    "f_bun_albumin": ("LBDSBUSI", "LBXSAL"),
    "f_age_hba1c": ("RIDAGEYR", "LBXGH"),
}

ENGINEERED_COLS = list(ENGINEERED_FEATURES)


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    """Column as float, missing column -> all-NaN (imputer handles it)."""
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Safe ratio: zero and negative denominators become NaN, not inf."""
    safe = denominator.where(denominator > 0)
    return numerator / safe


def derive_nhanes_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with ``ENGINEERED_COLS`` appended.

    ``df`` is left untouched; raw columns are preserved so the caller's
    column selection keeps working. Non-finite ratios are emitted as NaN
    rather than inf so the pipeline imputer owns the decision.
    """
    out = df.copy()

    sbp = _num(out, "BPXOSY1")
    dbp = _num(out, "BPXODI1")
    hgb = _num(out, "LBXHGB")
    hct = _num(out, "LBXHCT")
    rdw = _num(out, "LBXRDW")
    bun = _num(out, "LBDSBUSI")
    albumin = _num(out, "LBXSAL")
    age = _num(out, "RIDAGEYR")
    a1c = _num(out, "LBXGH")

    out["f_pulse_pressure"] = sbp - dbp
    out["f_map"] = (sbp + 2.0 * dbp) / 3.0
    out["f_mchc"] = _ratio(hgb, hct) * 100.0
    out["f_rdw_hgb"] = _ratio(rdw, hgb)
    out["f_bun_albumin"] = _ratio(bun, albumin)
    out["f_age_hba1c"] = age * a1c
    return out


def demo() -> None:
    """Self-check: derivation math, NaN-not-inf, and input immutability."""
    frame = pd.DataFrame(
        {
            "BPXOSY1": [140.0, 120.0],
            "BPXODI1": [90.0, 80.0],
            "LBXHGB": [14.0, 0.0],
            "LBXHCT": [42.0, 0.0],
            "LBXRDW": [14.0, 13.0],
            "LBDSBUSI": [20.0, 10.0],
            "LBXSAL": [4.0, 0.0],
            "RIDAGEYR": [60.0, 40.0],
            "LBXGH": [7.0, 5.0],
        }
    )
    before = list(frame.columns)
    out = derive_nhanes_features(frame)

    assert list(frame.columns) == before, "input frame must not gain columns"
    assert set(ENGINEERED_COLS) <= set(out.columns)
    assert out.loc[0, "f_pulse_pressure"] == 50.0
    assert abs(out.loc[0, "f_map"] - (140.0 + 180.0) / 3.0) < 1e-9
    assert abs(out.loc[0, "f_mchc"] - (14.0 / 42.0) * 100.0) < 1e-9
    assert abs(out.loc[0, "f_age_hba1c"] - 420.0) < 1e-9
    # Zero denominator -> NaN, never inf.
    assert np.isnan(out.loc[1, "f_mchc"])
    assert np.isnan(out.loc[1, "f_bun_albumin"])
    assert not np.isinf(out[ENGINEERED_COLS].to_numpy(dtype=float)).any()
    print("nhanes_features demo: OK")


if __name__ == "__main__":
    demo()
