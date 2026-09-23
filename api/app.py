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
    HealthResponse,
    ModelInfoResponse,
    PredictionResponse,
)
from src.preprocessing.preprocess import LINEAGE_ID_COL, LINEAGE_ROW_COL, get_column_lists
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()

_NUMERIC_COLS, _CATEGORICAL_COLS = get_column_lists()
COLUMN_ORDER = _NUMERIC_COLS + _CATEGORICAL_COLS
TARGET_COL = load_config()["data"]["target_column"]
DROP_COLS = {TARGET_COL, LINEAGE_ROW_COL, LINEAGE_ID_COL}

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
