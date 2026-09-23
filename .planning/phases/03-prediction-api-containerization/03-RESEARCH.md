# Phase 3: Prediction API + Containerization - Research

**Researched:** 2026-09-23
**Domain:** FastAPI model serving + MLflow Registry promotion + PostgreSQL prediction logging + Docker Compose + Streamlit
**Confidence:** MEDIUM

## Summary

Phase 3 serves the Phase 2 winner (`corvus-ckd` v9, mlp-relu) as a versioned FastAPI service with four endpoints, logs every prediction with its model version to PostgreSQL (Claim 4), composes API + MLflow + Postgres via Docker Compose, and ships a thin Streamlit UI. Training is NOT re-run: the phase opens with a Staging→Production promotion against the existing local `mlruns/` file store.

Registry state was verified live this session: v9 Staging, v1–v8 Archived, Production empty — so D-01's promotion is the true first act. The critical load-bearing facts are all verified in-repo: the serving input is exactly the 24 raw columns from `config.yaml`, the co-logged `preprocessing_pipeline.joblib` lives at artifact path `preprocessing` in the winner's run, the model at artifact path `model` (cloudpickle), and lineage columns `__source_row`/`__source_id` must never reach the model. The one structural tension the planner must respect: FR-4.4 says "per request" version resolution but locked decision D-02 pins the version at startup — D-02 wins.

**Primary recommendation:** Lifespan-pinned `models:/corvus-ckd/<version>` load at startup (model + pipeline artifact from the version's run), Pydantic v2 24-field schema with `float | None` numerics and Literal categoricals, SQLAlchemy 2.0 + `psycopg2-binary` prediction log, Compose with `pg_isready` health-gated startup, TestClient + synthetic fixtures for tests, thin Streamlit client over `httpx`.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Promote `corvus-ckd` v9 (mlp-relu) from Staging to Production as Phase 3's first act (the human gate from Phase 2 pays off here).
- **D-02:** The API pins the serving model version at startup (config/env), not per-request resolution. Simpler and faster; model swaps require restarts — accepted trade-off, recorded here.
- **D-03:** PostgreSQL running in Docker Compose. API logs there when `DATABASE_URL` points at it. No SQLite fallback — one backend, fully tested.
- **D-04:** Full record per prediction: request fields + prediction + probability + `model_version` + timestamp. This is the fuel Phases 4–5 monitoring and drift need.
- **D-05:** `/predict` requires all 24 clinical fields; missing values flow through the fitted pipeline's imputers. Serve-time distribution matches training — no skew by construction.
- **D-06:** Strict validation, reject fast: bad values get a clear 422 before any inference (same fail-closed instinct as the GX gate).
- **D-07:** `/batch_predict` accepts a CSV upload with the 24 columns; server parses and predicts per row.
- **D-08:** All-or-nothing: one bad row rejects the whole batch with the offending row number. No partial-success states.

### the agent's Discretion
None — the user decided every area directly. Planner has flexibility only on code organization (module split under `api/`, compose file layout), table schema naming, and test design.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FR-4.1 | FastAPI endpoints: `/predict`, `/batch_predict`, `/health`, `/model_info` | Lifespan + router patterns, UploadFile CSV handling |
| FR-4.2 | Request/response validation via Pydantic schemas | Pydantic v2 24-field schema section + code example |
| FR-4.3 | Log `model_version` per prediction (Claim 4) | Startup-pinned version in response + DB row |
| FR-4.4 | Resolve current production model version from MLflow Registry per request | **Superseded by locked D-02:** resolve once at startup via `models:/` URI; per-request resolution explicitly rejected |
| FR-5.1 | Dockerize FastAPI + MLflow + PostgreSQL via Docker Compose | Compose pattern + Dockerfile example |
| FR-5.2 | Prediction logging to PostgreSQL including model version | SQLAlchemy 2.0 log-table pattern + example |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Request validation (24 fields, 422) | API / Backend | — | Fail-closed before inference; never in Streamlit |
| Inference (pipeline.transform + predict) | API / Backend | — | Model + pipeline live in API process memory |
| Version pinning + Claim 4 stamping | API / Backend | — | Single startup resolution, stamped on every response/row |
| Prediction log persistence | Database / Storage | API / Backend | Postgres owns durability; API owns row shape |
| Batch CSV parsing | API / Backend | — | Server parses (D-07); client sends raw file |
| Model registry + artifacts | API / Backend (MLflow service) | — | Compose MLflow service fronts the store |
| UI rendering + file picking | Browser / Client (Streamlit) | — | Thin client; zero model logic in `frontend/` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.141.1 [VERIFIED: venv pip list] | HTTP service, lifespan, UploadFile | Locked by requirements; installed |
| pydantic | 2.13.5 [VERIFIED: venv pip list] | 24-field request/response validation | v2 `BaseModel` → automatic 422 [CITED: https://docs.pydantic.dev/latest] |
| uvicorn | 0.53.0 [VERIFIED: venv pip list] | ASGI server (`--host 0.0.0.0` in container) | Standard FastAPI server; installed |
| mlflow | 3.16.1 [VERIFIED: venv pip list] | Promotion + `models:/` load + pipeline artifact download | Registry already holds v1–v9; stages functional (verified live) |
| SQLAlchemy | 2.0.54 [VERIFIED: venv pip list] | Prediction-log ORM (`postgresql+psycopg2://` default dialect [CITED: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html]) | Installed; never hand-roll SQL |
| httpx | 0.28.1 [VERIFIED: venv pip list] | TestClient transport + Streamlit HTTP client | Already installed; TestClient requires it [CITED: https://fastapi.tiangolo.com] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `psycopg2-binary` [WARNING: flagged as suspicious — verify before using.] | latest on PyPI [ASSUMED] | Sync Postgres DBAPI for SQLAlchemy | Required for `postgresql+psycopg2://`; NOT installed — add to requirements |
| streamlit [WARNING: flagged as suspicious — verify before using.] | ≥1.32 per requirements comment [ASSUMED] | `frontend/app.py` thin UI (D4 React→Streamlit, STATE.md) | NOT installed — add to requirements |
| `python-multipart` [WARNING: flagged as suspicious — verify before using.] | latest on PyPI [ASSUMED] | `UploadFile`/form parsing (FastAPI requires it [CITED: https://fastapi.tiangolo.com]) | NOT installed — required for `/batch_predict` |
| postgres | 16 or 17 image [CITED: community compose examples] | Compose `db` service | Phase 3 Compose only; nothing local (Postgres NOT installed anywhere — verified) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `psycopg2-binary` | `psycopg` (v3) | v3 is the successor, but psycopg2 remains SQLAlchemy's default dialect [CITED: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html]; v2 binary wheel avoids build tools on Windows — stay with v2 |
| Startup pin (D-02) | Per-request `get_latest_versions` | Rejected by locked D-02; per-request adds registry latency to every prediction |
| SQLAlchemy log table | Raw `psycopg2` SQL / CSV log | Rejected: hand-rolled SQL loses schema discipline Phase 5 drift reads depend on |
| `fastapi-sqla` extension | Plain `sessionmaker` + `with Session(engine)` | Extension is overkill for one log table; stdlib-shaped SQLAlchemy per-request session is the documented norm [CITED: https://docs.sqlalchemy.org/en/20/orm/session_basics.html] |

**Installation:**
```bash
.\venv\python.exe -m pip install "psycopg2-binary" "streamlit>=1.32" "python-multipart"
```
Append the three to `requirements.txt` (API section is mislabeled "Phase 4" — fix label to Phase 3 while touching it [VERIFIED: requirements.txt:23]).

**Version verification:** Installed versions confirmed via `venv\Scripts\pip.exe list` this session (fastapi 0.141.1, pydantic 2.13.5, uvicorn 0.53.0, mlflow 3.16.1, SQLAlchemy 2.0.54, httpx 0.28.1, pytest 9.1.1). To-install packages could not be version-checked (not installed); planner gates each behind `checkpoint:human-verify`.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| psycopg2-binary | PyPI | unknown (seam: 2026-09-09 pub) | unknown | https://psycopg.org/ | SUS | Flagged — planner must add checkpoint:human-verify |
| streamlit | PyPI | unknown (seam: 2026-09-15 pub) | unknown | https://streamlit.io | SUS | Flagged — planner must add checkpoint:human-verify |
| python-multipart | PyPI | unknown (seam: 2026-06-04 pub) | unknown | https://github.com/Kludex/python-multipart | SUS | Flagged — planner must add checkpoint:human-verify |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious (SUS):** all three above — SUS reasons are seam-metadata gaps (`too-new`/`unknown-downloads`), not adverse signals; all three are the canonical packages for their job (SQLAlchemy default DBAPI; FastAPI-mandated upload parser; STATE.md D4 Streamlit decision). Planner inserts `checkpoint:human-verify` before each install per protocol, then approves.

*No postinstall scripts reported for any of the three (seam `postinstall: null`). No other new packages recommended — httpx/SQLAlchemy/pytest already installed cover tests, sessions, and HTTP.*

## Architecture Patterns

### System Architecture Diagram

```
test_raw.csv rows / Streamlit form / CSV upload
        │  (24 raw fields; lineage cols never leave disk)
        ▼
┌─ FastAPI (lifespan startup) ─────────────────────────┐
│ 1. transition v9 → Production (one-shot promote       │
│    script, first act D-01)                            │
│ 2. Pin MODEL_VERSION; mlflow.sklearn.load_model(      │
│    "models:/corvus-ckd/<v>") + download pipeline      │
│    artifact from version run_id                       │
│ 3. POST /predict → Pydantic 24-field check → 422 or   │
│    pipeline.transform → predict/proba → stamp         │
│    model_version → Postgres log → JSON response       │
│ 4. POST /batch_predict → parse CSV → validate ALL     │
│    rows → all-or-nothing predict+log                  │
│ 5. GET /health (serve readiness) /model_info (pinned  │
│    version + run_id + metrics)                        │
└──────────┬───────────────────────┬───────────────────┘
           │ DATABASE_URL          │ MLFLOW_TRACKING_URI
           ▼                       ▼
   ┌─ Postgres (compose) ─┐ ┌─ MLflow (compose/local) ─┐
   │ predictions table:   │ │ registry corvus-ckd +    │
   │ 24 fields +          │ │ run artifacts (model +  │
   │ prediction + proba + │ │ preprocessing/)          │
   │ model_version + ts   │ └──────────────────────────┘
   │ (Phase 5 drift reads │          ▲
   │  this table)         │          │ thin client
   └──────────────────────┘ ┌────────┴──────────┐
                            │ Streamlit frontend │
                            │ (httpx POST only)  │
                            └───────────────────┘
```

### Recommended Project Structure
```
api/
├── app.py           # FastAPI app + lifespan (load, pin version) + route wiring
├── schemas.py       # Pydantic v2: CKDRequest (24 fields), PredictionResponse (+model_version)
├── model_loader.py  # registry resolve + models:/ load + pipeline artifact download (planner discretion)
├── db.py            # engine/sessionmaker + PredictionLog model + create_all (planner discretion)
└── __init__.py
docker/
├── Dockerfile       # python:3.11-slim, install, uvicorn 0.0.0.0:8000
└── docker-compose.yml  # api + mlflow + postgres (postgres healthcheck-gated)
frontend/
└── app.py           # Streamlit thin client (API_URL env, localhost default)
scripts/ (or api/)   # promote_production.py — v9 Staging→Production one-shot (main() -> int)
tests/
└── test_api.py      # TestClient (with-block) + synthetic fixtures, never real mlruns/Postgres
config/config.yaml   # + api.* (model name, pinned version, tracking URI) and db.* (DATABASE_URL) sections
```

### Pattern 1: Lifespan-pinned model load
**What:** `@asynccontextmanager lifespan` resolves the Production version once, loads estimator + fitted pipeline into `app.state`, creates DB tables. [CITED: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/events.md] — lifespan is the recommended mechanism; `@app.on_event("startup")` is deprecated.
**When to use:** Always for this phase (D-02). Tests MUST use `with TestClient(app) as client:` or lifespan never runs [CITED: https://fastapi.tiangolo.com/advanced/testing-events].

### Pattern 2: Claim 4 stamping
**What:** Every `/predict` response and every Postgres row carries the same startup-pinned `model_version` string. This satisfies FR-4.3's acceptance test ("Each prediction response includes `model_version` field" [VERIFIED: REQUIREMENTS.md:95]) without per-request registry calls (D-02 overrides FR-4.4's "per request" wording).

### Pattern 3: Fail-closed request validation
**What:** Pydantic v2 types do the D-06 rejection — missing field or wrong Literal → automatic 422 before any inference code runs [CITED: https://docs.pydantic.dev/latest]. Numerics are `float | None` (missing flows to imputers, D-05); categoricals are `Literal[...]` vocabularies verified against the 400-row raw source this session (table in Code Examples). Mirror the existing `main() -> int` + `SystemExit` gate instinct [VERIFIED: src/preprocessing/preprocess.py:284-288].

### Anti-Patterns to Avoid
- **Loading the estimator without its pipeline:** the logged sklearn model consumes *transformed* features; serving raw 24-field input to it directly is a shape error. Always `pipeline.transform` first (Claim 2 contract [VERIFIED: src/training/train.py:144-150]).
- **Per-request `get_latest_versions`:** violates D-02, adds registry I/O to p99 latency.
- **SQLite fallback:** explicitly rejected by D-03; one backend, `DATABASE_URL`-gated (log writer no-ops or 503s loudly when unset in local dev — planner picks, but never a second schema).
- **Narrow range validation from test data:** raw ranges are wider than test ranges (e.g. bp max 180 raw vs 100 test, sc max 76 raw vs 18.1 test — verified this session). Hard-coding test-set min/max as `Field(ge/le)` false-422s real patients. Validate types + vocabularies, not ranges.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV multipart parsing | Custom body reader | `UploadFile` + `python-multipart` + `pandas.read_csv` | Boundary/streaming edge cases; FastAPI mandates the parser lib |
| Postgres log schema | Raw SQL strings | SQLAlchemy 2.0 `DeclarativeBase` + `sessionmaker` | Phase 5 drift reads depend on a stable schema; migrations stay sane |
| Registry promotion | Manual mlruns/ JSON edit | `client.transition_model_version_stage(..., stage="Production", archive_existing_versions=True)` | Stage bookkeeping + audit trail; pattern already in-repo [VERIFIED: src/evaluation/evaluate.py:75-80] |
| Model serialization format | Default `log_model` reload guess | `models:/corvus-ckd/<version>` URI (cloudpickle artifact already logged [VERIFIED: src/training/train.py:145-150]) | 3.x default flavor format differs (skops); the pinned URI + flavor loader removes ambiguity |
| API HTTP tests | Live server + real DB | `TestClient` (with-block) + tmp MLflow store (`tmp_mlflow_store` pattern [VERIFIED: tests/conftest.py:29-37]) + mocked session | Matches established synthetic-fixture + isolation pattern |

**Key insight:** Every hard problem here (validation, versioning, logging, serving) already has a canonical library answer installed or one `pip install` away; custom code should be limited to the 24-field schema, the four routes, one table, and compose wiring.

## Common Pitfalls

### Pitfall 1: Pipeline/model skew at serve time
**What goes wrong:** Response looks fine but predictions are garbage — raw input fed to estimator, or a re-fitted (not downloaded) pipeline used.
**Why it happens:** The estimator was trained on pipeline output; the fitted pipeline is an artifact in the winner's run, not next to the model.
**How to avoid:** Download `preprocessing_pipeline.joblib` via `mlflow.artifacts.download_artifacts` from the pinned version's `run_id` at startup; assert `pipeline.transform(one_row).shape[1]` equals the estimator's `n_features_in_` before accepting traffic.
**Warning signs:** Shape mismatch errors on first request; probability always ~0.5.

### Pitfall 2: `MLFLOW_ALLOW_FILE_STORE` missing in container
**What goes wrong:** MLflow 3.x refuses file-store tracking inside the API image.
**Why it happens:** The gate is opt-in per process (`os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")` [VERIFIED: src/training/train.py:43]); a fresh container process doesn't inherit repo shell env.
**How to avoid:** Set the env var in `Dockerfile`/`compose` AND keep the `setdefault` in loader code; prefer `MLFLOW_TRACKING_URI=http://mlflow:5000` in compose so the file-store path rarely triggers.

### Pitfall 3: Registry invisible from compose network
**What goes wrong:** `models:/corvus-ckd/9` resolves locally but not from the `api` container (relative `mlruns` path + `localhost` URI baked in).
**Why it happens:** `mlflow.tracking_uri: "mlruns"` is a host-relative path [VERIFIED: config/config.yaml:35-37]; containers need `http://mlflow:5000` or a mounted volume with identical absolute layout.
**How to avoid:** New `api.*` config section reads tracking URI from env (`MLFLOW_TRACKING_URI`, compose sets it to the service URL); keep `load_config()` as the only config mechanism, extend `config.yaml`, never a second one.

### Pitfall 4: Lineage columns leak into features
**What goes wrong:** Batch CSV contains `__source_row`/`classification` (test_raw.csv shape) and the server feeds them to the pipeline → feature-count mismatch or silent label leak.
**Why it happens:** `test_raw.csv` has 27 columns (24 + 2 lineage + target — verified this session); the pipeline expects exactly the 24 raw columns [VERIFIED: src/preprocessing/preprocess.py:78-83].
**How to avoid:** Drop `{target, __source_row, __source_id}` + warn-on-unexpected-extras (established pattern [VERIFIED: src/training/train.py:87-93]); `/batch_predict` requires exactly the 24 columns, extras rejected or ignored loudly, never silently fed.

### Pitfall 5: Missing values rejected instead of imputed
**What goes wrong:** 422 on rows with blank cells (rc is missing in 131/400 raw rows — verified), destroying D-05's "no skew by construction".
**Why it happens:** Numeric fields typed as bare `float` reject null; pandas CSV parse yields NaN which a strict schema drops.
**How to avoid:** Numerics `float | None`; pass None/NaN through to the fitted imputers (median/most_frequent [VERIFIED: config/config.yaml:25-29]).

### Pitfall 6: Partial batch writes
**What goes wrong:** 50/100 rows logged, then row 51 fails → log table and response disagree.
**Why it happens:** Per-row commit inside the loop.
**How to avoid:** D-08 all-or-nothing: validate ALL rows first (collect offending row numbers, 422 with first offender), single transaction commit after all predictions succeed.

### Pitfall 7: API starts before Postgres is ready
**What goes wrong:** `create_engine`/`create_all` fails at lifespan startup; container crash-loops.
**Why it happens:** `depends_on` without healthcheck only orders start, not readiness.
**How to avoid:** `pg_isready` healthcheck + `depends_on: condition: service_healthy` [CITED: community compose examples]; lifespan retries table creation a few times before failing loud.

## Code Examples

### 24-field schema (vocabularies verified against 400-row raw source this session)
```python
from typing import Literal
from pydantic import BaseModel

class CKDRequest(BaseModel):  # all 24 required (D-05); numerics nullable (D-05/D-06)
    age: float | None; bp: float | None; sg: float | None; al: float | None
    su: float | None; bgr: float | None; bu: float | None; sc: float | None
    sod: float | None; pot: float | None; hemo: float | None; pcv: float | None
    wc: float | None; rc: float | None
    rbc: Literal["abnormal", "normal"]; pc: Literal["abnormal", "normal"]
    pcc: Literal["notpresent", "present"]; ba: Literal["notpresent", "present"]
    htn: Literal["no", "yes"]; dm: Literal["no", "yes"]; cad: Literal["no", "yes"]
    appet: Literal["good", "poor"]; pe: Literal["no", "yes"]; ane: Literal["no", "yes"]

class PredictionResponse(BaseModel):  # Claim 4: model_version on every response
    prediction: int; probability: float; model_version: str
```
Vocabularies are exhaustive over `data/raw/kidney_disease.csv` (400 rows, checked this session) — not just the 81-row test split. Raw numeric extremes (bp≤180, sc≤76, wc≤26400) forbid narrow `ge/le` bounds.

### Lifespan startup (pin version + load both artifacts)
```python
# Source pattern: official lifespan docs + evaluate.py MlflowClient usage
from contextlib import asynccontextmanager
import mlflow
from mlflow.tracking import MlflowClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = MlflowClient()
    client.transition_model_version_stage(  # D-01 only in promote script, NOT here
        name="corvus-ckd", version="9", stage="Production",
        archive_existing_versions=True,
    ) if False else None
    app.state.model_version = cfg["api"]["pinned_version"]  # D-02: config/env pin
    app.state.model = mlflow.sklearn.load_model(
        f"models:/corvus-ckd/{app.state.model_version}")
    run_id = client.get_model_version("corvus-ckd",
        app.state.model_version).run_id  # run_id linkage [VERIFIED: src/evaluation/evaluate.py:62-65]
    pipe_path = mlflow.artifacts.download_artifacts(
        run_id=run_id, artifact_path="preprocessing/preprocessing_pipeline.joblib")
    app.state.pipeline = joblib.load(pipe_path)
    Base.metadata.create_all(bind=engine)  # prediction-log table
    yield
```
Registered name is `"corvus-ckd"` — verbatim `"corvus-ckd"` [VERIFIED: src/evaluation/evaluate.py:33]; artifact paths `"preprocessing"` + `"model"` — verbatim [VERIFIED: src/training/train.py:144-148].

### Prediction logging (SQLAlchemy 2.0 per-request session)
```python
# Source pattern: https://docs.sqlalchemy.org/en/20/orm/session_basics.html
from sqlalchemy.orm import Session
with Session(engine) as session:  # per-request context, auto-close
    session.add(PredictionLog(**record_24_fields,
        prediction=pred, probability=proba,
        model_version=app.state.model_version))  # Claim 4: D-04
    session.commit()
```
`with Session(engine) as session: session.add(...); session.commit()` is the documented unit-of-work shape [CITED: https://docs.sqlalchemy.org/en/20/orm/session_basics.html]. Table: 24 field columns + `prediction` + `probability` + `model_version` + `created_at` server default (Phase 5 reads this).

### Compose (health-gated) + Dockerfile
```yaml
services:
  db:
    image: postgres:16
    environment: {POSTGRES_USER: corvus, POSTGRES_PASSWORD: corvus, POSTGRES_DB: corvus}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U corvus -d corvus"], interval: 10s, retries: 5}
  api:
    build: {context: .., dockerfile: docker/Dockerfile}
    ports: ["8000:8000"]
    environment: {DATABASE_URL: "postgresql+psycopg2://corvus:corvus@db:5432/corvus",
                  MLFLOW_TRACKING_URI: "http://mlflow:5000"}
    depends_on: {db: {condition: service_healthy}}
```
`pg_isready` + `service_healthy` is the standard readiness gate [CITED: community compose examples + https://github.com/mlflow/mlflow/blob/master/examples/mlflow_artifacts/docker-compose.yml]. Dockerfile: `FROM python:3.11-slim`, copy requirements, `CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]`; venv Python is 3.11.0 (verified) so slim-3.11 matches training-time behavior.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan=` asynccontextmanager | FastAPI ≥0.93 | Old way deprecated; lifespan-only (never both) [CITED: FastAPI events docs] |
| Registry stages | Stages + aliases (`models:/name@alias`) | Aliases newer; stages deprecated since MLflow 2.9 | FR-3.1 mandates stages; they work in 3.16.1 (verified live) — follow the in-repo tech-debt note toward aliases later [VERIFIED: src/evaluation/evaluate.py:71-74] |
| `models:/name/Stage` latest | Pinned `models:/name/<version>` | D-02 locked | Reproducible serving; restarts for swaps |

**Deprecated/outdated:**
- `on_event` startup handlers: replaced by lifespan — do not use.
- Tracer latest-version heuristic: broken at 9 versions; `run_id` linkage is the resolution method [VERIFIED: src/evaluation/evaluate.py:55-65].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `psycopg2-binary`/`streamlit`/`python-multipart` latest PyPI versions install cleanly on Python 3.11 Windows + `python:3.11-slim` | Standard Stack | Low — all are pure wheels for this stack; human-verify checkpoint gates it |
| A2 | Streamlit thin-client shape (`st.form` + `requests/httpx.post`, `st.file_uploader` + multipart `files=`) with `API_URL` env defaulting to localhost | Architecture | Low — UI is thin; any equivalent client shape works |
| A3 | Compose MLflow service can front the existing file-store `mlruns/` (volume mount) or a Postgres backend; exact wiring is planner discretion | Pitfall 3 | Medium — wrong choice breaks `models:/` loads in-container; mitigate by testing `docker compose up` + `/model_info` in-plan |
| A4 | No `ge/le` range checks on numerics (types + vocabularies only) satisfies D-06 strictness | Patterns | Low — 422 coverage comes from type/vocab failures; ranges would false-reject real rows per verified raw extremes |

## Open Questions (RESOLVED — adopted by 03-02/03-03/03-04 PLAN.md)

1. **DB-unavailable local-dev behavior** — RESOLVED: fail-closed 503 (03-02/03-03 tasks + tests).
   - What we know: D-03 mandates Postgres via Compose, no SQLite fallback; `DATABASE_URL` gates logging.
   - What's unclear: When `DATABASE_URL` is unset (local `pytest`/dev run), should `/predict` 503 or serve-without-logging?
   - Recommendation: Planner picks one (suggest: fail-closed 503 with clear message — matches GX fail-closed instinct); tests cover the chosen branch with mocked session.

2. **MLflow-in-compose store backend** — RESOLVED: mlruns volume-mount (03-04 task 1, rationale recorded).
   - What we know: Registry state lives in host `mlruns/` (gitignored [VERIFIED: .gitignore]); official MLflow compose uses Postgres backend store [CITED: https://github.com/mlflow/mlflow/tree/master/docker-compose].
   - What's unclear: Volume-mount `mlruns/` into the tracking service vs. migrating runs to a Postgres-backed server.
   - Recommendation: Prefer volume-mount for Phase 3 (zero migration, promotion stays against the same store); revisit in Phase 5 if drift reads need SQL access to runs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv (project) | Everything | ✓ | 3.11.0 (verified) | — |
| fastapi/pydantic/uvicorn/mlflow/SQLAlchemy/httpx/pytest | API + tests | ✓ | 0.141.1 / 2.13.5 / 0.53.0 / 3.16.1 / 2.0.54 / 0.28.1 / 9.1.1 (verified) | — |
| Docker + Compose | FR-5.1 | ✓ | v29.6.2 + v5.3.1 (verified) | — |
| Postgres | FR-5.2 | ✗ (by design — comes via Compose) | — | None (D-03 forbids fallback) |
| psycopg2-binary / streamlit / python-multipart | DB driver / UI / upload | ✗ | — | None — `pip install` in Wave 0 |
| MLflow registry `corvus-ckd` | D-01, serving | ✓ | v9 Staging, v1–v8 Archived, Production empty (verified live) | — |
| `api/`, `docker/`, `frontend/` dirs | New code | ✓ (exist, empty — verified) | — | — |

**Missing dependencies with no fallback:** Postgres outside Compose (by design); the three pip packages (Wave 0 install).
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (verified installed) |
| Config file | none — default discovery (matches existing `tests/`) |
| Quick run command | `.\venv\python.exe -m pytest tests/test_api.py -x -q` |
| Full suite command | `.\venv\python.exe -m pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FR-4.1 | `/predict` 200 + Claim 4 fields; `/batch_predict` CSV; `/health`; `/model_info` | unit (TestClient, with-block) | `pytest tests/test_api.py -x -q` | ❌ Wave 0 |
| FR-4.2 | Missing field → 422; bad Literal → 422; null numeric accepted | unit | `pytest tests/test_api.py -x -q` | ❌ Wave 0 |
| FR-4.3 | Response + logged row carry pinned `model_version` | unit (mocked session) | `pytest tests/test_api.py -x -q` | ❌ Wave 0 |
| FR-4.4 | Startup pins version from config/env (D-02 override noted) | unit (assert `app.state.model_version`) | `pytest tests/test_api.py -x -q` | ❌ Wave 0 |
| FR-5.1 | Compose file valid + `api` healthy (websearch-verified `docker compose config`) | smoke (manual/docker) | `docker compose -f docker/docker-compose.yml config` | ❌ Wave 0 |
| FR-5.2 | Full-record row written incl. version (mocked session asserts row shape) | unit (mocked session) | `pytest tests/test_api.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.\venv\python.exe -m pytest tests/test_api.py -x -q`
- **Per wave merge:** `.\venv\python.exe -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api.py` — covers FR-4.1→FR-4.4, FR-5.2 (TestClient with-block + synthetic 24-field fixture shaped like `test_raw.csv` row minus lineage/target; never real `mlruns/` or real Postgres — extend `tmp_mlflow_store` + mock SQLAlchemy session)
- [ ] `tests/conftest.py` — add `synthetic_ckd_request` dict fixture (24 fields, one None numeric, valid Literal categoricals)
- [ ] Framework install: `.\venv\python.exe -m pip install psycopg2-binary "streamlit>=1.32" python-multipart` + requirements.txt additions
- [ ] `docker/docker-compose.yml config` smoke validation (no test file — command-run gate)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in scope (local demo service) |
| V3 Session Management | No | Stateless API; no sessions |
| V4 Access Control | No | No multi-user model |
| V5 Input Validation | **Yes** | Pydantic v2 schema (types + Literals); CSV column allowlist; all-or-nothing batch 422 |
| V6 Cryptography | No | No secrets in scope (Compose dev credentials only; `.env` gitignored [VERIFIED: .gitignore]) |

### Known Threat Patterns for FastAPI + Postgres stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSV formula injection (batch upload opened in Excel) | Tampering | Server never renders CSV; Streamlit displays via `st.dataframe` (text cells) — no formula evaluation path |
| Oversized batch DoS (GB CSV upload) | Denial of service | Cap `UploadFile` read size / row count (planner sets limit, e.g. reject >10k rows with 413) [ASSUMED limit value] |
| SQL injection via field values | Injection | ORM-bound parameters only; never f-string SQL (enforced by using SQLAlchemy exclusively) |
| Secret leak via compose env | Information disclosure | Dev-only credentials; `.env` gitignored; never log `DATABASE_URL` |

## Sources

### Primary (HIGH confidence)
- In-repo verification this session: `config/config.yaml` (24 cols, mlflow section), `src/preprocessing/preprocess.py` (lineage cols, column lists), `src/training/train.py` (artifact paths, cloudpickle), `src/evaluation/evaluate.py` (stage transitions, run_id linkage), `tests/conftest.py` (isolation pattern), live registry query (v9 Staging / v1–v8 Archived / Production empty), raw-CSV vocabulary + range audit (400 rows), venv `pip list` versions, `docker --version` / `docker compose version`.

### Secondary (MEDIUM confidence)
- [CITED: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/events.md] — lifespan pattern, on_event deprecation
- [CITED: https://fastapi.tiangolo.com/advanced/testing-events] — TestClient with-block for lifespan
- [CITED: https://docs.pydantic.dev/latest] — v2 BaseModel validation
- [CITED: https://docs.sqlalchemy.org/en/20/orm/session_basics.html] — per-request Session context
- [CITED: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html] — psycopg2 default dialect, `postgresql+psycopg2://` URL
- [CITED: https://www.mlflow.org/docs/latest/model-registry.html] — `models:/<name>/<version>` URI, stage transitions
- [CITED: https://github.com/mlflow/mlflow/tree/master/docker-compose] — official Postgres-backed compose shape
- [CITED: https://github.com/mlflow/mlflow/blob/master/examples/mlflow_artifacts/docker-compose.yml] — healthcheck + service wiring idioms

### Tertiary (LOW confidence)
- Community FastAPI+Postgres compose guides (healthcheck + `service_healthy` idiom, cross-confirmed across 3+ sources) — needs in-plan `docker compose up` proof.
- Streamlit thin-client shape (training knowledge, [ASSUMED]).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - installed versions verified via pip list; to-install trio are canonical packages gated by human-verify.
- Architecture: MEDIUM - lifespan/pin/log/compose patterns cited from official docs; compose MLflow backend choice left to planner (Open Question 2).
- Pitfalls: HIGH - five of seven pitfalls derive from in-repo verified facts (artifact paths, lineage cols, raw ranges, file-store gate, test shape).

**Research date:** 2026-09-23
**Valid until:** 2026-10-23 (stable domain; FastAPI/MLflow/SQLAlchemy APIs move slowly)
