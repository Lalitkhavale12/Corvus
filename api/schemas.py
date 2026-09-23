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


class PredictionResponse(BaseModel):
    """Claim 4: every response carries the startup-pinned model_version."""

    prediction: int
    probability: float
    model_version: str


class HealthResponse(BaseModel):
    """Serve readiness plus the pinned version."""

    status: str
    model_version: str


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
