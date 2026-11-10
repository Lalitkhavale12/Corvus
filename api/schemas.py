"""Pydantic v2 request/response schemas for the Corvus prediction API.

The 24 fields mirror ``config.yaml`` ``data.numeric_cols`` /
``data.categorical_cols`` (single source of truth lives in config; this
module pins the same names). Numerics are ``float | None`` so blanks flow
to the fitted pipeline imputers (D-05); categoricals are ``Literal``
vocabularies verified against the 400-row raw source, so bad values fail
fast with an automatic 422 before inference (D-06). No ``ge``/``le`` range
bounds: verified raw extremes (bp 180, sc 76) are wider than any test
split, and range checks would false-reject real patients.

FR-4.4 deviation (locked D-02): the serving model version is pinned once
at startup from config/env, not resolved per request — model swaps need
restarts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from src.utils.logger import get_logger

log = get_logger()


class CKDRequest(BaseModel):
    """All 24 clinical fields required (D-05); null numerics imputed."""

    age: float | None
    bp: float | None
    sg: float | None
    al: float | None
    su: float | None
    bgr: float | None
    bu: float | None
    sc: float | None
    sod: float | None
    pot: float | None
    hemo: float | None
    pcv: float | None
    wc: float | None
    rc: float | None
    rbc: Literal["abnormal", "normal"]
    pc: Literal["abnormal", "normal"]
    pcc: Literal["notpresent", "present"]
    ba: Literal["notpresent", "present"]
    htn: Literal["no", "yes"]
    dm: Literal["no", "yes"]
    cad: Literal["no", "yes"]
    appet: Literal["good", "poor"]
    pe: Literal["no", "yes"]
    ane: Literal["no", "yes"]


class CKDRequestNative(BaseModel):
    """23 NHANES-native fields (D-05 native schema for /v2).

    The 20 numerics are ``float | None`` so blanks flow to the fitted
    native pipeline imputers, mirroring ``CKDRequest``. The 3
    categoricals are NHANES-coded ``Literal`` vocabularies verified
    against the locked derived CSV (observed codes: RIAGENDR {1,2},
    DMDEDUC2 {1..5,9}, DIQ010 {1,2,3}),
    so out-of-vocabulary codes fail fast with an automatic 422 before
    inference. ``None`` means "not recorded": those rows are imputed like
    the numerics rather than rejected.
    No ``ge``/``le`` range bounds per the established raw-extremes
    rationale.

    ``RIDRETH1`` and ``MCQ035`` were removed: both are US-specific and
    unfillable by a non-NHANES clinician, and the measured cost of
    dropping them is inside noise (dev dROC -0.0015, holdout -0.0031).
    """

    RIDAGEYR: float | None
    INDFMPIR: float | None
    LBDSBUSI: float | None
    LBDSGLSI: float | None
    LBXSNASI: float | None
    LBXSKSI: float | None
    LBDSCASI: float | None
    LBDSPHSI: float | None
    LBXHGB: float | None
    LBXHCT: float | None
    LBXWBCSI: float | None
    LBXRBCSI: float | None
    LBXGH: float | None
    BMXBMI: float | None
    BPXOSY1: float | None
    BPXODI1: float | None
    LBXRDW: float | None
    LBDSUASI: float | None
    LBXSAL: float | None
    LBXSGTSI: float | None
    RIAGENDR: Literal[1, 2] | None = None
    DMDEDUC2: Literal[1, 2, 3, 4, 5, 9] | None = None
    DIQ010: Literal[1, 2, 3] | None = None


class NativeBatchItem(CKDRequestNative):
    """Per-row v2 batch item — identical native validation, named for the batch path."""


class PredictionResponse(BaseModel):
    """Claim 4: every response carries the startup-pinned model_version."""

    prediction: int
    probability: float
    model_version: str


class HealthResponse(BaseModel):
    """Serve readiness plus the pinned versions of both serving slots."""

    status: str
    # Legacy v1 slot (UCI 24-field /predict), kept for backward compatibility.
    model_version: str
    # NHANES-native v2 slot; empty when no challenger is pinned, in which
    # case every /v2 route fails closed with 503.
    model_version_v2: str = ""


class ModelInfoResponse(BaseModel):
    """Pinned model identity; resolution documents the D-02 deviation."""

    model_name: str
    model_version: str
    run_id: str
    resolution: str


class BatchPredictionItem(BaseModel):
    """One scored batch row: 1-indexed data-row number plus outcome."""

    row: int
    prediction: int
    probability: float


class BatchPredictionResponse(BaseModel):
    """All-or-nothing batch outcome stamped with the pinned version (D-08)."""

    predictions: list[BatchPredictionItem]
    count: int
    model_version: str


# ---------------------------------------------------------------------------
# Prediction history schemas (Phase 8-03)
# ---------------------------------------------------------------------------


class PredictionHistoryOut(BaseModel):
    """One historical prediction row for the authenticated user's history."""

    id: int
    model_version: str
    prediction: int
    probability: float
    created_at: datetime | None = None

    class Config:
        from_attributes = True
