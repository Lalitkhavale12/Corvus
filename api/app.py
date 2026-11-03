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
import os
import time
from contextlib import asynccontextmanager
from typing import List

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session

from api import db, model_loader
from api.db import PredictionLog, PredictionLogV2
from api.schemas import (
    BatchPredictionItem,
    BatchPredictionResponse,
    CKDRequest,
    CKDRequestNative,
    HealthResponse,
    ModelInfoResponse,
    NativeBatchItem,
    PredictionHistoryOut,
    PredictionResponse,
)
from src.auth.auth import authenticate_user, create_user, get_user_by_email
from src.auth.dependencies import (
    get_current_doctor,
    get_current_patient,
    get_current_user,
    require_user,
)
from src.auth.models import (
    DoctorProfile,
    PatientDoctorMapping,
    PatientProfile,
    User,
)
from src.auth.schemas import (
    DoctorProfileCreate,
    DoctorProfileOut,
    PatientDoctorAssign,
    PatientDoctorMappingOut,
    PatientProfileCreate,
    PatientProfileOut,
    ProfileOut,
    Token,
    UserLogin,
    UserOut,
    UserRegister,
)
from src.auth.security import create_access_token, get_secret_key
from src.database import Base, get_db, get_engine
from src.preprocessing.preprocess import (
    LINEAGE_ID_COL,
    LINEAGE_ROW_COL,
    get_column_lists,
)
from src.preprocessing.preprocess_nhanes import get_nhanes_column_lists
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()

# Prometheus metrics (Phase 4)
REQUEST_COUNT = Counter(
    "corvus_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_DURATION = Histogram(
    "corvus_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
PREDICTIONS_TOTAL = Counter(
    "corvus_predictions_total",
    "Total predictions served",
    ["model_version", "result"],
)
PREDICTION_PROBABILITY = Histogram(
    "corvus_prediction_probability",
    "Prediction probability distribution",
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)
DB_CONNECTIONS = Gauge(
    "corvus_db_connections_active",
    "Active database connections",
)
USERS_TOTAL = Gauge(
    "corvus_users_total",
    "Total registered users",
)

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
    # Refuse to serve without a signing key: an unset SECRET_KEY would
    # otherwise mean tokens signed with a published default.
    get_secret_key()
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
        # Operating point chosen on dev out-of-fold probabilities; 0.5 is
        # unusable here (it misses roughly two thirds of true cases).
        app.state.v2_threshold = model_loader.load_v2_threshold(v2_version)
    else:
        # No approved challenger pin: v2 slots stay empty and every /v2
        # route fails closed via _require_v2 (T-07-14). v1 serves on.
        app.state.v2_model_version = ""
        app.state.v2_model = None
        app.state.v2_pipeline = None
        app.state.v2_run_id = ""
        app.state.v2_threshold = model_loader.DEFAULT_DECISION_THRESHOLD
        log.warning(
            "api.v2_pinned_version unset — /v2 routes will 503 until "
            "an approved challenger version is pinned"
        )
    engine = db.get_engine()
    if engine is not None:
        db.Session.configure(bind=engine)
    db.create_tables()
    # Auth tables live on src.database.Base, a different metadata from the
    # prediction log's Base (api/db.py), so db.create_tables() never makes
    # them. Without this a fresh Postgres 500s on /auth/register.
    auth_engine = get_engine()
    if auth_engine is not None:
        Base.metadata.create_all(bind=auth_engine)
    yield


app = FastAPI(title="Corvus CKD Prediction API", lifespan=lifespan)

# CORS_ORIGINS (comma separated) wins; the localhost defaults keep the dev
# server and the built nginx image working out of the box.
_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def _cors_origins(raw: str | None = None) -> list[str]:
    """Allowed browser origins: explicit CORS_ORIGINS, else the dev list."""
    if raw is None:
        raw = os.environ.get("CORS_ORIGINS", "")
    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return parsed or list(_DEFAULT_CORS_ORIGINS)


CORS_ORIGINS = _cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Login throttle (brute-force guard)
# ---------------------------------------------------------------------------

LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60
_login_attempts: dict[str, list[float]] = {}


def _throttle_login(client: str) -> None:
    """Reject the 6th login attempt within a minute from one client.

    ponytail: process-local sliding window, so it resets on restart and does
    not span replicas. Move the counter to Redis when the API runs more than
    one instance; a shared store is the only way the limit still means
    something behind a load balancer.
    """
    now = time.monotonic()
    recent = [
        seen for seen in _login_attempts.get(client, []) if now - seen < LOGIN_WINDOW_SECONDS
    ]
    if len(recent) >= LOGIN_MAX_ATTEMPTS:
        _login_attempts[client] = recent
        raise HTTPException(
            status_code=429,
            detail="too many login attempts, try again later",
            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)},
        )
    recent.append(now)
    _login_attempts[client] = recent


def _clear_login_throttle(client: str) -> None:
    _login_attempts.pop(client, None)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics for Prometheus."""
    start_time = time.time()
    method = request.method
    path = request.url.path
    response = await call_next(request)
    duration = time.time() - start_time
    REQUEST_COUNT.labels(method=method, endpoint=path, status_code=response.status_code).inc()
    REQUEST_DURATION.labels(method=method, endpoint=path).observe(duration)
    return response


# ---------------------------------------------------------------------------
# Prometheus metrics endpoint (Phase 4)
# ---------------------------------------------------------------------------

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


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


def _log_predictions(
    rows: list[dict], preds: list[int], probas: list[float], user_id: int | None = None
) -> None:
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
                    user_id=user_id,
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
def predict(
    body: CKDRequest,
    current_user: User = Depends(require_user),
):
    """Validate (422) → transform → predict → log → versioned JSON."""
    _require_log_store()
    frame = _frame_from_request(body)
    preds, probas = _predict_frame(frame)
    _log_predictions([body.model_dump()], preds, probas, user_id=current_user.id)
    # Track prediction metrics
    PREDICTIONS_TOTAL.labels(
        model_version=app.state.model_version,
        result=str(preds[0]),
    ).inc()
    PREDICTION_PROBABILITY.observe(probas[0])
    return PredictionResponse(
        prediction=preds[0],
        probability=probas[0],
        model_version=app.state.model_version,
    )


@app.post("/batch_predict", response_model=BatchPredictionResponse)
def batch_predict(
    file: UploadFile,
    current_user: User = Depends(require_user),
):
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
    _log_predictions(rows, preds, probas, user_id=current_user.id)
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
        probas = app.state.v2_model.predict_proba(features)
        threshold = getattr(
            app.state, "v2_threshold", model_loader.DEFAULT_DECISION_THRESHOLD
        )
        preds = (probas[:, 1] >= threshold).astype(int)
    except Exception as exc:
        log.warning(f"V2 inference failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="inference failed")
    return [int(p) for p in preds], [float(p[1]) for p in probas]


def _log_predictions_v2(
    rows: list[dict], preds: list[int], probas: list[float], user_id: int | None = None
) -> None:
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
                    user_id=user_id,
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
def predict_v2(
    body: CKDRequestNative,
    current_user: User = Depends(require_user),
):
    """Validate (422) → transform → predict → log to predictions_v2 → versioned JSON."""
    _require_v2()
    _require_log_store()
    frame = _frame_from_native_request(body)
    preds, probas = _predict_frame_v2(frame)
    _log_predictions_v2([body.model_dump()], preds, probas, user_id=current_user.id)
    # Track prediction metrics
    PREDICTIONS_TOTAL.labels(
        model_version=app.state.v2_model_version,
        result=str(preds[0]),
    ).inc()
    PREDICTION_PROBABILITY.observe(probas[0])
    return PredictionResponse(
        prediction=preds[0],
        probability=probas[0],
        model_version=app.state.v2_model_version,
    )


@app.post("/v2/batch_predict", response_model=BatchPredictionResponse)
def batch_predict_v2(
    file: UploadFile,
    current_user: User = Depends(require_user),
):
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
    _log_predictions_v2(rows, preds, probas, user_id=current_user.id)
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


# ---------------------------------------------------------------------------
# Model Management Endpoints (Phase 4 - Enhanced)
# ---------------------------------------------------------------------------

@app.get("/api/v1/models", response_model=List[dict])
def list_all_models(current_user: User = Depends(get_current_user)):
    """List all registered model versions in MLflow registry."""
    try:
        models = model_loader.list_all_model_versions()
        return models
    except Exception as e:
        log.warning(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@app.get("/api/v1/models/{version}/details", response_model=dict)
def get_model_details(version: str, current_user: User = Depends(get_current_user)):
    """Get detailed information about a specific model version."""
    try:
        details = model_loader.get_model_version_details(model_version=version)
        if not details:
            raise HTTPException(status_code=404, detail=f"Model version {version} not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        log.warning(f"Failed to get model details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model details")


@app.get("/api/v1/models/compare", response_model=dict)
def compare_models(
    current_user: User = Depends(get_current_user),
    champion_version: str = "9",
    challenger_version: str = "11",
):
    """Compare two model versions side by side."""
    try:
        comparison = model_loader.compare_model_versions(
            champion_version=champion_version,
            challenger_version=challenger_version,
        )
        return comparison
    except Exception as e:
        log.warning(f"Failed to compare models: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare models")


@app.post("/api/v1/models/promote", response_model=dict)
def promote_challenger_model(
    challenger_version: str,
    current_user: User = Depends(get_current_user),
):
    """Promote a challenger model to production."""
    try:
        from src.model_promotion import promote_challenger
        result = promote_challenger(
            model_name=model_loader.REGISTERED_MODEL_NAME,
            challenger_version=int(challenger_version),
        )
        if result.get("promoted"):
            # Update the pinned version in app state
            app.state.v2_model_version = challenger_version
            app.state.v2_model_version = challenger_version
        return result
    except Exception as e:
        log.warning(f"Failed to promote challenger: {e}")
        raise HTTPException(status_code=500, detail="Failed to promote challenger")


# ---------------------------------------------------------------------------
# Auth routes (Phase 8-01)
# ---------------------------------------------------------------------------

@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """Register a new user (patient or doctor)."""
    existing = get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="email already registered",
        )
    user = create_user(db, user_in)
    if user is None:
        raise HTTPException(
            status_code=400,
            detail="email already registered",
        )
    USERS_TOTAL.inc()
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@app.post("/auth/login", response_model=Token)
def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Authenticate with email + password, return JWT access token."""
    client = request.client.host if request.client else "unknown"
    _throttle_login(client)
    user = authenticate_user(db, user_in.email, user_in.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _clear_login_throttle(client)
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=access_token)


@app.get("/auth/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


# ---------------------------------------------------------------------------
# Auth routes (Phase 8-02)
# ---------------------------------------------------------------------------

@app.post("/auth/profile", response_model=ProfileOut, status_code=201)
def create_profile(
    profile_in: PatientProfileCreate | DoctorProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create the current user's profile (branches on role)."""
    if current_user.role == "patient":
        existing = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="patient profile already exists",
            )
        profile = PatientProfile(
            user_id=current_user.id,
            first_name=profile_in.first_name,
            last_name=profile_in.last_name,
            date_of_birth=profile_in.date_of_birth,
            sex=profile_in.sex,
            phone=profile_in.phone,
            mrn=profile_in.mrn,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return ProfileOut(role="patient", patient_profile=profile)
    else:
        existing = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="doctor profile already exists",
            )
        profile = DoctorProfile(
            user_id=current_user.id,
            first_name=profile_in.first_name,
            last_name=profile_in.last_name,
            license_number=profile_in.license_number,
            specialization=profile_in.specialization,
            phone=profile_in.phone,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return ProfileOut(role="doctor", doctor_profile=profile)


@app.get("/auth/profile", response_model=ProfileOut)
def read_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the current user's role-appropriate profile."""
    if current_user.role == "patient":
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
        if profile is None:
            raise HTTPException(status_code=404, detail="patient profile not found")
        return ProfileOut(role="patient", patient_profile=profile)
    else:
        profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
        if profile is None:
            raise HTTPException(status_code=404, detail="doctor profile not found")
        return ProfileOut(role="doctor", doctor_profile=profile)


@app.get("/doctors/patients", response_model=list[PatientDoctorMappingOut])
def list_doctor_patients(
    current_user: User = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """Doctor lists assigned patients (requires doctor role)."""
    mappings = (
        db.query(PatientDoctorMapping)
        .filter(PatientDoctorMapping.doctor_id == current_user.id, PatientDoctorMapping.is_active == True)  # noqa: E712
        .all()
    )
    return mappings


@app.post("/doctors/patients/assign", response_model=PatientDoctorMappingOut, status_code=201)
def assign_patient(
    assign_in: PatientDoctorAssign,
    current_user: User = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """Doctor assigns a patient by email (requires doctor role)."""
    patient = get_user_by_email(db, assign_in.patient_email)
    if patient is None:
        raise HTTPException(status_code=404, detail="patient not found")
    if patient.role != "patient":
        raise HTTPException(status_code=400, detail="user is not a patient")
    existing = (
        db.query(PatientDoctorMapping)
        .filter(
            PatientDoctorMapping.patient_id == patient.id,
            PatientDoctorMapping.doctor_id == current_user.id,
            PatientDoctorMapping.is_active == True,  # noqa: E712
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="patient already assigned to this doctor")
    mapping = PatientDoctorMapping(patient_id=patient.id, doctor_id=current_user.id)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


# ---------------------------------------------------------------------------
# Prediction history (Phase 8-03)
# ---------------------------------------------------------------------------

@app.get("/auth/predictions", response_model=list[PredictionHistoryOut])
def list_predictions(current_user: User = Depends(require_user), session: Session = Depends(get_db)):
    """Return the current user's prediction history (v1 + v2 rows)."""
    v1_rows = (
        session.query(PredictionLog)
        .filter(PredictionLog.user_id == current_user.id)
        .order_by(PredictionLog.created_at.desc())
        .all()
    )
    v2_rows = (
        session.query(PredictionLogV2)
        .filter(PredictionLogV2.user_id == current_user.id)
        .order_by(PredictionLogV2.created_at.desc())
        .all()
    )
    combined = []
    for row in v1_rows:
        combined.append(
            PredictionHistoryOut(
                id=row.id,
                model_version=row.model_version,
                prediction=row.prediction,
                probability=row.probability,
                created_at=row.created_at,
            )
        )
    for row in v2_rows:
        combined.append(
            PredictionHistoryOut(
                id=row.id,
                model_version=row.model_version,
                prediction=row.prediction,
                probability=row.probability,
                created_at=row.created_at,
            )
        )
    combined.sort(key=lambda r: r.created_at or "", reverse=True)
    return combined


@app.get("/auth/predictions/{prediction_id}", response_model=PredictionHistoryOut)
def get_prediction(
    prediction_id: int,
    current_user: User = Depends(require_user),
    session: Session = Depends(get_db),
):
    """Return a single prediction if owned by the current user."""
    row = (
        session.query(PredictionLog)
        .filter(PredictionLog.id == prediction_id, PredictionLog.user_id == current_user.id)
        .first()
    )
    if row is not None:
        return PredictionHistoryOut(
            id=row.id,
            model_version=row.model_version,
            prediction=row.prediction,
            probability=row.probability,
            created_at=row.created_at,
        )
    row = (
        session.query(PredictionLogV2)
        .filter(
            PredictionLogV2.id == prediction_id,
            PredictionLogV2.user_id == current_user.id,
        )
        .first()
    )
    if row is not None:
        return PredictionHistoryOut(
            id=row.id,
            model_version=row.model_version,
            prediction=row.prediction,
            probability=row.probability,
            created_at=row.created_at,
        )
    raise HTTPException(status_code=404, detail="prediction not found")
