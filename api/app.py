"""FastAPI prediction service for corvus-ckd (Phase 3 tracer slice).

Lifespan pins the serving model version once from config/env (D-02),
loads the estimator plus its co-logged preprocessing pipeline, binds the
Postgres log session, and fails loud on a pipeline/estimator shape
mismatch. Every ``/predict`` response and every ``predictions`` row
carries the same pinned ``model_version`` (Claim 4, D-04, FR-4.3).

Fail-closed branches (D-06 instinct): Pydantic rejects bad input with an
automatic 422 before inference; DATABASE_URL unset serves 503 naming
DATABASE_URL, never silent no-log serving and never SQLite (D-03);
unexpected inference errors log the type name server-side and return a
500 JSON with no traceback (T-03-04); DATABASE_URL values are never
logged.
"""

from __future__ import annotations

import datetime
import io
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from api import db, model_loader
from api.schemas import (
    BatchPredictionItem,
    BatchPredictionResponse,
    CKDRequest,
    CKDRequestNative,
    HealthResponse,
    ModelInfoResponse,
    NativeBatchItem,
    PredictionResponse,
)
from src.preprocessing.preprocess import (
    LINEAGE_ID_COL,
    LINEAGE_ROW_COL,
    get_column_lists,
)
from src.preprocessing.preprocess_nhanes import get_nhanes_column_lists
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()

_NUMERIC_COLS, _CATEGORICAL_COLS = get_column_lists()
COLUMN_ORDER = _NUMERIC_COLS + _CATEGORICAL_COLS
TARGET_COL = load_config()["data"]["target_column"]
DROP_COLS = {TARGET_COL, LINEAGE_ROW_COL, LINEAGE_ID_COL}

# v2 (NHANES-native) column order plus drop set: native target column plus
# the shared lineage constants, mirroring the v1 DROP pattern (D-07).
_NATIVE_NUMERIC_COLS, _NATIVE_CATEGORICAL_COLS = get_nhanes_column_lists()
COLUMN_ORDER_V2 = _NATIVE_NUMERIC_COLS + _NATIVE_CATEGORICAL_COLS
NATIVE_TARGET_COL = load_config()["data"]["nhanes_target_column"]
DROP_COLS_V2 = {NATIVE_TARGET_COL, LINEAGE_ROW_COL, LINEAGE_ID_COL}

PINNED_RESOLUTION = "pinned-at-startup"

# Upload guards (T-03-07): reject before parsing eats memory.
MAX_BATCH_BYTES = 5000000
MAX_BATCH_ROWS = 10000


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pin version, load artifacts, bind the log store — fail loud on skew."""
    version = model_loader.resolve_pinned_version()
    model, pipeline, run_id, version = model_loader.load_serving_artifacts(version)
    app.state.model_version = version
    app.state.model = model
    app.state.pipeline = pipeline
    app.state.run_id = run_id
    v2_version = model_loader.resolve_v2_version()
    if v2_version:
        v2_model, v2_pipeline, v2_run_id, v2_version = (
            model_loader.load_v2_artifacts(v2_version)
        )
        app.state.v2_model_version = v2_version
        app.state.v2_model = v2_model
        app.state.v2_pipeline = v2_pipeline
        app.state.v2_run_id = v2_run_id
    else:
        # No approved challenger pin: v2 slots stay empty and every /v2
        # route fails closed via _require_v2 (T-07-14). v1 serves on.
        app.state.v2_model_version = ""
        app.state.v2_model = None
        app.state.v2_pipeline = None
        app.state.v2_run_id = ""
        log.warning(
            "api.v2_pinned_version unset — /v2 routes will 503 until "
            "an approved challenger version is pinned"
        )
    engine = db.get_engine()
    if engine is not None:
        db.Session.configure(bind=engine)
    db.create_tables()
    yield


app = FastAPI(title="Corvus CKD Prediction API", lifespan=lifespan)


def _require_log_store() -> None:
    """Fail closed when there is nowhere to log (D-03: no silent serving)."""
    if not db.get_database_url():
        raise HTTPException(
            status_code=503,
            detail="prediction log unavailable: set DATABASE_URL to the Postgres log store",
        )


def _require_v2() -> None:
    """Fail closed when no approved challenger pin is configured (T-07-14)."""
    if not getattr(app.state, "v2_model_version", ""):
        raise HTTPException(
            status_code=503,
            detail="v2 model unavailable: set api.v2_pinned_version "
            "to an approved challenger version",
        )


def _frame_from_request(body: CKDRequest) -> pd.DataFrame:
    """Single-row frame in config column order for pipeline.transform."""
    return pd.DataFrame([body.model_dump()])[COLUMN_ORDER]


def _predict_frame(frame: pd.DataFrame) -> tuple[list[int], list[float]]:
    """pipeline.transform then predict/proba; 500 JSON on surprise failures."""
    try:
        features = app.state.pipeline.transform(frame)
        preds = app.state.model.predict(features)
        probas = app.state.model.predict_proba(features)
    except Exception as exc:
        log.warning(f"Inference failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="inference failed")
    return [int(p) for p in preds], [float(p[1]) for p in probas]


def _log_predictions(rows: list[dict], preds: list[int], probas: list[float]) -> None:
    """One PredictionLog row per prediction, a single commit (all-or-nothing)."""
    session = db.Session()
    try:
        for row, pred, proba in zip(rows, preds, probas):
            session.add(
                db.PredictionLog(
                    **row,
                    prediction=pred,
                    probability=proba,
                    model_version=app.state.model_version,
                    # Stamp here (not only server_default) so every row
                    # instance carries its D-04 timestamp, mocked or real.
                    created_at=datetime.datetime.now(),
                )
            )
        session.commit()
    except Exception as exc:
        session.rollback()
        log.warning(f"Prediction-log write failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="prediction log unavailable")
    finally:
        session.close()


@app.post("/predict", response_model=PredictionResponse)
def predict(body: CKDRequest):
    """Validate (422) → transform → predict → log → versioned JSON."""
    _require_log_store()
    frame = _frame_from_request(body)
    preds, probas = _predict_frame(frame)
    _log_predictions([body.model_dump()], preds, probas)
    return PredictionResponse(
        prediction=preds[0],
        probability=probas[0],
        model_version=app.state.model_version,
    )


@app.post("/batch_predict", response_model=BatchPredictionResponse)
def batch_predict(file: UploadFile):
    """CSV upload with the 24 columns; all-or-nothing per D-08.

    Every row validates first — one bad row rejects the whole batch with
    the offending 1-indexed data-row number. A single commit follows only
    after all rows predict successfully.
    """
    _require_log_store()
    raw = file.file.read()
    if len(raw) > MAX_BATCH_BYTES:
        raise HTTPException(status_code=413, detail="batch upload exceeds size limit")
    try:
        text = raw.decode("utf-8")
    except Exception as exc:
        log.warning(f"Batch CSV decode failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=422, detail="batch CSV could not be parsed")
    n_data_rows = len(text.strip().splitlines()) - 1
    if n_data_rows > MAX_BATCH_ROWS:
        raise HTTPException(status_code=413, detail="batch upload exceeds row limit")
    try:
        frame = pd.read_csv(io.StringIO(text))
    except Exception as exc:
        log.warning(f"Batch CSV parse failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=422, detail="batch CSV could not be parsed")
    # Lineage metadata plus the target never reach the pipeline (D-07):
    # dropped via the imported constants, never string literals.
    frame = frame.drop(columns=[c for c in DROP_COLS if c in frame.columns])
    unexpected = set(frame.columns) - set(COLUMN_ORDER)
    if unexpected:
        # Warn-and-ignore (train.py extras pattern): never fed to the pipeline.
        log.warning(f"Ignoring unexpected batch columns: {sorted(unexpected)}")
    missing = [c for c in COLUMN_ORDER if c not in frame.columns]
    if missing:
        raise HTTPException(status_code=422, detail=f"missing columns: {missing}")
    rows: list[dict] = []
    for i, record in enumerate(frame[COLUMN_ORDER].to_dict(orient="records"), start=1):
        clean = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        try:
            rows.append(CKDRequest(**clean).model_dump())
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"row {i}: {exc}")
    batch = pd.DataFrame(rows)[COLUMN_ORDER]
    preds, probas = _predict_frame(batch)
    _log_predictions(rows, preds, probas)
    return BatchPredictionResponse(
        predictions=[
            BatchPredictionItem(row=i, prediction=p, probability=q)
            for i, (p, q) in enumerate(zip(preds, probas), start=1)
        ],
        count=len(preds),
        model_version=app.state.model_version,
    )


@app.get("/health", response_model=HealthResponse)
def health():
    """Serve readiness plus the startup-pinned version."""
    return HealthResponse(status="ok", model_version=app.state.model_version)


@app.get("/model_info", response_model=ModelInfoResponse)
def model_info():
    """Pinned model identity; resolution records the D-02 deviation."""
    return ModelInfoResponse(
        model_name=model_loader.REGISTERED_MODEL_NAME,
        model_version=app.state.model_version,
        run_id=app.state.run_id,
        resolution=PINNED_RESOLUTION,
    )


@app.exception_handler(500)
async def _no_traceback_500(request, exc):  # noqa: ARG001
    """500 JSON shape without a traceback (T-03-04)."""
    return JSONResponse(status_code=500, content={"detail": "internal error"})


def _frame_from_native_request(body: CKDRequestNative) -> pd.DataFrame:
    """Single-row frame in native column order for the v2 pipeline."""
    return pd.DataFrame([body.model_dump()])[COLUMN_ORDER_V2]


def _predict_frame_v2(frame: pd.DataFrame) -> tuple[list[int], list[float]]:
    """v2 pipeline.transform then predict/proba; 500 JSON on surprise failures."""
    try:
        features = app.state.v2_pipeline.transform(frame)
        preds = app.state.v2_model.predict(features)
        probas = app.state.v2_model.predict_proba(features)
    except Exception as exc:
        log.warning(f"V2 inference failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="inference failed")
    return [int(p) for p in preds], [float(p[1]) for p in probas]


def _log_predictions_v2(rows: list[dict], preds: list[int], probas: list[float]) -> None:
    """One PredictionLogV2 row per prediction, a single commit (all-or-nothing)."""
    session = db.Session()
    try:
        for row, pred, proba in zip(rows, preds, probas):
            session.add(
                db.PredictionLogV2(
                    **row,
                    prediction=pred,
                    probability=proba,
                    model_version=app.state.v2_model_version,
                    created_at=datetime.datetime.now(),
                )
            )
        session.commit()
    except Exception as exc:
        session.rollback()
        log.warning(f"V2 prediction-log write failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="prediction log unavailable")
    finally:
        session.close()


@app.post("/v2/predict", response_model=PredictionResponse)
def predict_v2(body: CKDRequestNative):
    """Validate (422) → transform → predict → log to predictions_v2 → versioned JSON."""
    _require_v2()
    _require_log_store()
    frame = _frame_from_native_request(body)
    preds, probas = _predict_frame_v2(frame)
    _log_predictions_v2([body.model_dump()], preds, probas)
    return PredictionResponse(
        prediction=preds[0],
        probability=probas[0],
        model_version=app.state.v2_model_version,
    )


@app.post("/v2/batch_predict", response_model=BatchPredictionResponse)
def batch_predict_v2(file: UploadFile):
    """Native-schema CSV upload; all-or-nothing with 1-indexed offender rows.

    Mirrors the v1 batch shape: size/row caps (413) before full parse,
    lineage plus native target dropped via constants, unexpected columns
    warn-ignored, missing columns 422, per-row NativeBatchItem validation,
    single commit to predictions_v2 only after all rows predict.
    """
    _require_v2()
    _require_log_store()
    raw = file.file.read()
    if len(raw) > MAX_BATCH_BYTES:
        raise HTTPException(status_code=413, detail="batch upload exceeds size limit")
    try:
        text = raw.decode("utf-8")
    except Exception as exc:
        log.warning(f"V2 batch CSV decode failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=422, detail="batch CSV could not be parsed")
    n_data_rows = len(text.strip().splitlines()) - 1
    if n_data_rows > MAX_BATCH_ROWS:
        raise HTTPException(status_code=413, detail="batch upload exceeds row limit")
    try:
        frame = pd.read_csv(io.StringIO(text))
    except Exception as exc:
        log.warning(f"V2 batch CSV parse failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=422, detail="batch CSV could not be parsed")
    frame = frame.drop(columns=[c for c in DROP_COLS_V2 if c in frame.columns])
    unexpected = set(frame.columns) - set(COLUMN_ORDER_V2)
    if unexpected:
        log.warning(f"Ignoring unexpected v2 batch columns: {sorted(unexpected)}")
    missing = [c for c in COLUMN_ORDER_V2 if c not in frame.columns]
    if missing:
        raise HTTPException(status_code=422, detail=f"missing columns: {missing}")
    rows: list[dict] = []
    for i, record in enumerate(frame[COLUMN_ORDER_V2].to_dict(orient="records"), start=1):
        clean = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        try:
            rows.append(NativeBatchItem(**clean).model_dump())
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"row {i}: {exc}")
    batch = pd.DataFrame(rows)[COLUMN_ORDER_V2]
    preds, probas = _predict_frame_v2(batch)
    _log_predictions_v2(rows, preds, probas)
    return BatchPredictionResponse(
        predictions=[
            BatchPredictionItem(row=i, prediction=p, probability=q)
            for i, (p, q) in enumerate(zip(preds, probas), start=1)
        ],
        count=len(preds),
        model_version=app.state.v2_model_version,
    )


@app.get("/v2/model_info", response_model=ModelInfoResponse)
def model_info_v2():
    """v2 pinned model identity; 503 while no challenger pin is configured."""
    _require_v2()
    return ModelInfoResponse(
        model_name=model_loader.REGISTERED_MODEL_NAME,
        model_version=app.state.v2_model_version,
        run_id=app.state.v2_run_id,
        resolution=PINNED_RESOLUTION,
    )
