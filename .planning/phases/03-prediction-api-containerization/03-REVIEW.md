---
phase: 03-prediction-api-containerization
reviewed: 2026-09-23T08:30:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - api/app.py
  - api/schemas.py
  - api/model_loader.py
  - api/db.py
  - scripts/promote_production.py
  - docker/Dockerfile
  - docker/docker-compose.yml
  - frontend/app.py
  - tests/test_api.py
  - tests/conftest.py
  - config/config.yaml
findings:
  critical: 0
  warning: 9
  info: 9
  total: 18
status: issues-found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-23T08:30:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues-found

## Summary

Reviewed the full Phase 3 serving surface (FastAPI app, schemas, registry loader,
Postgres log layer, promotion script, container manifests, Streamlit client, API
tests, config) against the locked decisions D-01..D-08. No Critical (RCE / injection /
auth-bypass / data-loss) findings: all writes are ORM-bound, the batch filename is
never touched, tracebacks are suppressed, and per-request fail-closed gates (422/503)
are correctly ordered (validate → infer → log). The 9 Warnings below are real but
contained by the local-demo threat posture: the highest-leverage fixes are the
post-buffer size gate (WR-01), non-finite float acceptance (WR-02), and engine-per-call
leak (WR-03). Info items are robustness/ergonomics gaps worth fixing before Phase 5
reads this log for drift.

## Warnings

### WR-01: Batch upload is fully buffered into RAM before the size gate fires

**File:** `api/app.py:146-148`
**Issue:** `raw = file.file.read()` slurps the entire upload into memory, and only
*afterwards* does `len(raw) > MAX_BATCH_BYTES` return 413. A multi-hundred-MB/GB
upload exhausts worker memory before the guard is ever evaluated, defeating the
stated intent of the T-03-07 comment ("reject before parsing eats memory"). The
row-count guard (line 154) has the same post-hoc shape. A single request can OOM-kill
the one-worker uvicorn process, and the compose stack sets no `restart:` policy, so
the API stays down.
**Fix:**
```python
# Check the declared size BEFORE buffering the body.
max_bytes = MAX_BATCH_BYTES
declared = file.size  # Starlette populates Content-Length when present
if declared is not None and declared > max_bytes:
    raise HTTPException(status_code=413, detail="batch upload exceeds size limit")
chunks, total = [], 0
while chunk := file.file.read(1024 * 1024):
    total += len(chunk)
    if total > max_bytes:
        raise HTTPException(status_code=413, detail="batch upload exceeds size limit")
    chunks.append(chunk)
raw = b"".join(chunks)
```

### WR-02: Non-finite floats (NaN / Infinity) pass validation on both endpoints

**File:** `api/schemas.py:30-43`
**Issue:** All 14 numerics are bare `float | None`. Pydantic v2 accepts `NaN`, `Inf`,
`-Inf` by default (`allow_inf_nan=True`), and there is no `Field` constraint or
`ConfigDict`. Consequences: (a) `/predict` JSON with `{"age": NaN}` passes the 422
gate — `SimpleImputer` will not repair `inf`, `StandardScaler` propagates it to `nan`
features, and the service either 500s or returns/logs a garbage prediction,
poisoning the Claim-4 Postgres log that Phase 5 drift reads; (b) `/batch_predict`
CSV cells containing `inf` survive `pd.read_csv` as float inf and pass `CKDRequest`
the same way (NaN cells are safe — they become `None` — but inf is not); (c) the
Streamlit `_parse_numeric` (`frontend/app.py:39-44`) happily forwards `"nan"`/`"inf"`
strings. No test pins this (all fixtures use finite `1.0`).
**Fix:**
```python
from pydantic import BaseModel, Field
class CKDRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=False)
    age: float | None = Field(default=None, allow_inf_nan=False)
    # ... repeat for all 14 numerics ...
```
plus a server-side test posting `{"age": float("inf")}` expecting 422, and a
`math.isfinite` guard in frontend `_parse_numeric`.

### WR-03: `get_engine()` mints a new pooled engine per call and never disposes it

**File:** `api/db.py:81-89`
**Issue:** Every call constructs `create_engine(url)` with the default `QueuePool`.
`lifespan` calls it once (bound engine lives on, fine), but `create_tables` calls it
again inside its retry loop — up to 3 engines on the retry path, all but none
disposed. Each abandoned engine keeps an idle pooled connection to Postgres open
until GC. Separately, no `pool_pre_ping=True` means the first request after a
Postgres bounce fails with a stale-connection `DisconnectionError` (500) even though
the DB is back, and no `connect_timeout` bounds a hung TCP connect inside the
"3 retries" loop.
**Fix:**
```python
def get_engine():
    url = get_database_url()
    if not url:
        return None
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})

def create_tables(retries: int = 3) -> bool:
    engine = get_engine()   # create ONCE
    if engine is None:
        log.warning("DATABASE_URL unset — prediction log unavailable (/predict will 503)")
        return False
    try:
        for attempt in range(1, retries + 1):
            try:
                Base.metadata.create_all(bind=engine)
                return True
            except Exception as exc:
                last_exc = exc
                log.warning(f"create_tables attempt {attempt}/{retries} failed: {type(exc).__name__}")
                time.sleep(1)
        raise RuntimeError(...)
    finally:
        engine.dispose()  # lifespan keeps its own bound engine; this one is scratch
```

### WR-04: Timestamps are naive local time — ordering hazard for Phase 5 drift reads

**File:** `api/app.py:111`, `api/db.py:61-68`
**Issue:** Rows are stamped with `datetime.datetime.now()` (naive, API-container wall
clock) while the column fallback is `server_default=func.now()` (Postgres transaction
time). Mixed clock domains on the same column: if the containers ever run in
different timezones, `created_at` ordering — the exact signal Phase 5 drift detection
sorts on — silently skews. Naive datetimes also raise `TypeError` the moment any
downstream consumer compares them against an aware timestamp.
**Fix:**
```python
created_at=datetime.datetime.now(datetime.timezone.utc),
# and
default=lambda: datetime.datetime.now(datetime.timezone.utc),
```
(or prefer `server_default=func.now()` alone and stop client-stamping, accepting that
mocked captures assert on `None` — the current dual scheme exists only to satisfy the
mocked test).

### WR-05: Postgres superuser password hardcoded in the committed compose file

**File:** `docker/docker-compose.yml:28-31`, `docker/docker-compose.yml:47`
**Issue:** `POSTGRES_PASSWORD: corvus` and the `corvus:corvus` pairs inside
`DATABASE_URL` are committed to VCS in plaintext. The header comment claims "real
secrets never commit — .env stays gitignored", but there is no `.env` indirection at
all — the secret *is* in the file, so secret scanners (gitleaks) will flag this repo
forever. Containment (why Warning, not Critical): the `db` service maps **no host
ports**, so the credential is reachable only inside the compose network, and T-03-12
records human acceptance for the local demo.
**Fix:** Keep `corvus/corvus` as documented demo defaults but move them behind
indirection before any shared/hosted use:
```yaml
environment:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}
```
```yaml
environment:
  DATABASE_URL: postgresql+psycopg2://${POSTGRES_USER:-corvus}:${POSTGRES_PASSWORD:?}@db:5432/${POSTGRES_DB:-corvus}
```
with `.env` gitignored (verify — no `.env.example` exists today).

### WR-06: API image is unpinned and bloated — supply-chain hygiene

**File:** `docker/Dockerfile:1-7`
**Issue:** (a) `FROM python:3.11-slim` floats — no digest, so rebuilds silently drift
base CVEs and interpreter behavior; (b) the image `pip install`s the *entire*
`requirements.txt`, which per 03-01 includes `streamlit`, `httpx`, test tooling, and
training deps the API never imports — larger attack surface and slower, fatter
deploys. Nothing in the image verifies what it installed.
**Fix:**
```dockerfile
FROM python:3.11-slim@sha256:<pinned-digest>
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
```
(split a minimal `requirements-api.txt`: fastapi, uvicorn, pydantic, pandas,
scikit-learn, mlflow, sqlalchemy, psycopg2-binary, python-multipart — no streamlit,
no pytest), and re-pin the digest on a schedule.

### WR-07: Container runs as root and the API has no healthcheck

**File:** `docker/Dockerfile:3-19`, `docker/docker-compose.yml:40-55`
**Issue:** No `USER` directive — uvicorn, MLflow artifact download, and `joblib.load`
all execute as root; combined with the root-owned read-write `/mlruns` bind mount, a
container compromise has maximum latitude. Separately, the `api` service defines no
`healthcheck`, so Phase 4 consumers cannot gate on API readiness (`depends_on:
service_healthy` only exists for `db`), and `mlflow`'s startup ordering against the
API is unguarded.
**Fix:**
```dockerfile
RUN useradd -m -u 10001 corvus && chown -R corvus /app
USER corvus
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```
(slim has no `curl`; use the stdlib probe), plus a matching `healthcheck:` stanza on
the compose `api` service.

### WR-08: Frontend catches only `ConnectError` — timeouts crash the UI

**File:** `frontend/app.py:66-69`, `frontend/app.py:86-93`
**Issue:** Both POST sites wrap `httpx.post` (with `timeout=30` / `timeout=120`) in
`except httpx.ConnectError`. `httpx.TimeoutException`, `ReadError`,
`RemoteProtocolError` (API 500-mid-stream, container restart, slow 10k-row batch)
are siblings, not subclasses, of `ConnectError` — they propagate uncaught and
Streamlit renders a raw traceback instead of the friendly "is the stack up?" error.
Easily triggered: point the UI at a cold stack or submit a large batch.
**Fix:**
```python
except httpx.HTTPError:
    st.error(f"Cannot reach the API at {API_URL} — is the stack up?")
```
(`HTTPError` is the base of `ConnectError` + `TimeoutException` + friends.)

### WR-09: Promotion path resolves a different tracking URI than the serving path

**File:** `scripts/promote_production.py:37-40`
**Issue:** The script computes
`os.environ.get("MLFLOW_TRACKING_URI", str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))`,
ignoring `cfg["api"]["tracking_uri"]`, while `model_loader.resolve_tracking_uri`
prefers env → `api.tracking_uri` → `mlflow.tracking_uri`. Today both default to local
`mlruns` so they agree, but the moment anyone sets `api.tracking_uri` (e.g. the
compose `http://mlflow:5000`), promotion writes to one store and serving reads from
another — a silent version-skew footgun. Secondary nits in the same file: empty-string
`MLFLOW_TRACKING_URI=""` is honored as `""` instead of falling back (use `or`, not
`get` with default), and there is no pre-flight that v9 exists / is not already
Production.
**Fix:** import and reuse the single source of truth:
```python
from api.model_loader import resolve_tracking_uri
tracking_uri = resolve_tracking_uri(cfg)
```
(or duplicate its precedence chain with a comment), plus `PROMOTE_VERSION` as a CLI
arg with a `get_model_version` pre-flight.

## Info

### IN-01: Uploaded temp file handle is never closed

**File:** `api/app.py:146`
**Issue:** `file.file.read()` is never followed by `file.file.close()`. Starlette
spools uploads >1MB to real temp files; in a long-lived worker, unclosed spool files
accumulate until GC. Add `try/finally: file.file.close()` (sync route, so the sync
close — not `await file.close()`).

### IN-02: `/predict` extras are silently dropped; `/batch_predict` extras warn

**File:** `api/app.py:124-134` vs `api/app.py:165-168`, `api/schemas.py:27`
**Issue:** `CKDRequest` uses Pydantic's default `extra="ignore"`, so a single predict
carrying `classification` (the label!) or `id` is silently discarded with no audit
trail, while the batch path `log.warning`s unexpected columns per T-03-08. Same
trust boundary, two behaviors. Declare it explicitly and align them:
`model_config = ConfigDict(extra="ignore")` on the schema plus a debug/warning log of
dropped keys in `predict`, or set `extra="forbid"` if strictness is preferred
(note: `forbid` would 422 today's silent-accept clients — a contract change).

### IN-03: `/health` and `/model_info` assume lifespan ran

**File:** `api/app.py:192-206`
**Issue:** Both handlers dereference `app.state.model_version` / `app.state.run_id`
unconditionally. Any serving path that skips lifespan (unit import without
`TestClient` context, `--lifespan off`, lifespan crash-loop recovery) turns readiness
probes into `AttributeError` → 500. Prefer
`getattr(app.state, "model_version", "unready")` with a 503 when unready, so
orchestrators get a meaningful signal instead of a 500.

### IN-04: Batch CSV edge cases — BOM, duplicate headers, empty file

**File:** `api/app.py:149-179`
**Issue:** (a) `raw.decode("utf-8")` keeps a UTF-8 BOM, so Excel-exported CSVs 422
with a confusing `missing columns: ['\ufeffage']` — decode with `"utf-8-sig"`;
(b) duplicate header names (e.g. two `age` columns) slip past the set-based
missing/unexpected checks and surface as a 500 from the pipeline instead of a 422 —
reject `frame.columns.duplicated().any()` fast; (c) a header-only CSV returns
**200 with `count: 0`** and an empty commit — harmless but arguably a 422
("batch is empty"). None is data-loss; all three lack pinning tests.

### IN-05: Promotion script ergonomics — hardcoded v9, no pre-flight, no traceback

**File:** `scripts/promote_production.py:31-53`
**Issue:** One-shot by design (per summary), but as committed: version is a module
constant with no `--version` override (re-running post-v10 silently re-promotes stale
v9); no check that v9 is currently Staging (could promote an Archived version
blindly); `except Exception` prints `PROMOTION ERROR: {exc}` with no traceback,
slowing diagnosis. Acceptable for the D-01 first act; add `argparse --version`,
a `get_model_version` stage assertion, and `traceback.print_exc()` before reuse.

### IN-06: `mlflow` service has a spurious DB dependency and shares the API image

**File:** `docker/docker-compose.yml:57-68`
**Issue:** `mlflow` fronts a `file:///mlruns` backend yet `depends_on: db:
service_healthy`, coupling its startup to a store it never touches (misleading
topology, slower boot). It also builds the full API Dockerfile only to override
`command:` — works, but ships API-only bytes to run the tracking server. Documented
`--allowed-hosts "mlflow:*"` widening is fine for local demo (no bare `*`, compose
network only); consider pinning `mlflow:5000` exactly in Phase 4 as the summary
itself suggests.

### IN-07: Dead logger in schemas module

**File:** `api/schemas.py:22-24`
**Issue:** `log = get_logger()` is never used in the module (no branch logs).
Remove it — every other module logs with purpose; a dead module-level logger
invites drive-by misuse and trips lint (F841-adjacent).

### IN-08: Frontend URL and 422 rendering nits

**File:** `frontend/app.py:18`, `frontend/app.py:79`, `frontend/app.py:102`
**Issue:** (a) `API_URL` is concatenated raw — a trailing-slash env value yields
`http://x//predict` (Starlette may 404/redirect-strip the body on 307); normalize
with `API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")`;
(b) FastAPI 422 bodies carry `detail` as a **list** of error dicts, so
`resp.json().get('detail')` renders a raw list repr — format it
(`"; ".join(e.get("msg", "") for e in detail)`) for a readable clinical UI.

### IN-09: Frontend loads the whole CSV into memory with no client-side guard

**File:** `frontend/app.py:85-91`
**Issue:** `uploaded.getvalue()` buffers the entire file client-side and POSTs it
unchecked; a 1 GB pick crashes the local Streamlit process before the server's 5 MB
cap is ever reached. Self-inflicted (local UI only, hence Info), but a two-line
`len(data) > 5_000_000 → st.error` pre-check gives instant feedback instead of a
freeze.

## Threat Model Note

**HTTP input surface.** `/predict` (JSON) and `/batch_predict` (multipart CSV) both
terminate at Pydantic validation before inference — good fail-closed shape, no raw
SQL (all writes ORM-bound, grep-clean per 03-03), filename never touches the
filesystem (no traversal), tracebacks suppressed. Residual gaps: post-buffer size
enforcement (WR-01), non-finite floats (WR-02), BOM/duplicate-header edges (IN-04),
no auth/rate-limit (accepted local-demo posture per T-03-15 — must be revisited
before any network exposure; at minimum add an API token + `slowapi` throttling on
the batch route).

**Postgres credentials handling.** Placeholder `corvus/corvus` committed in
`docker-compose.yml` (WR-05); `DATABASE_URL` (password-bearing) flows via container
env (visible to `docker inspect` / host-local users). Contained today: `db` exposes
no host ports and the value is never logged server-side. Path to safe: `${VAR:?}`
indirection + gitignored `.env` + distinct prod password + least-privilege DB role
(current role owns the schema and can `create_all` — fine for demo, not for shared).

**Docker image hygiene.** Floating `python:3.11-slim` + full-requirements install +
root runtime + no `HEALTHCHECK` (WR-06, WR-07). No secret is baked into the image
(`COPY` covers only `api/`, `src/`, `config/` — verified clean), and `.dockerignore`
keeps `venv/`/`mlruns/`/`data/` out of the context. Pin the digest, split
`requirements-api.txt`, drop privileges.

**joblib trust boundary.** `api/model_loader.py:92` `joblib.load(pipe_path)` unpickles
bytes from the MLflow file store at startup — a latent RCE primitive *if* the store
is ever writable by anyone outside the trainer's trust domain (bind-mounted
`docker/.mlruns.container/` is host-writable; any poisoned `preprocessing_pipeline.joblib`
executes on `compose up`). Same-trust solo demo today (hence Warning, not Critical):
harden by restricting store-dir permissions, checksum-pinning the pipeline artifact
(record sha256 at promotion, verify before load), and never serving artifacts from a
world-writable or remotely-synced store without verification.

---

_Reviewed: 2026-09-23T08:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
