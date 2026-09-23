---
phase: 03-prediction-api-containerization
plan: 04
subsystem: infra
tags: [docker, compose, postgres, mlflow, streamlit, httpx, claim-4]

# Dependency graph
requires:
  - phase: 02-model-training-experiment-tracking
    provides: corvus-ckd registry v1-v9 with v9 winner (mlp-relu) in Production
  - phase: 03-prediction-api-containerization plan 02
    provides: lifespan-pinned v9 serving, /predict + /batch_predict + /health + /model_info
  - phase: 03-prediction-api-containerization plan 03
    provides: hardened batch guards, D-04 full-record single-commit logging
provides:
  - python:3.11-slim API image with health-gated Compose stack (db + api + mlflow)
  - container-readable mlruns sync (Windows-absolute URIs rebased to /mlruns, host pristine)
  - thin Streamlit client over /predict + /batch_predict
  - live proof: /health + /model_info + /predict all version 9, Postgres row logged
affects: [phase-4 compose reuse, phase-5 drift reads]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 2700
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns: [container-synced file-store copy with rebased location prefix, mlflow allowed-hosts for compose DNS, .dockerignore-trimmed build context]

key-files:
  created: [docker/Dockerfile, docker/docker-compose.yml, docker/sync_mlruns_container.py, frontend/app.py, .dockerignore]
  modified: []

key-decisions:
  - "Serve containers from a synced mlruns copy with /mlruns-rebased URIs (host mlruns never mutated, v9 identity intact)"
  - "mlflow --allowed-hosts mlflow:* (exact Host match fails on the compose DNS name; localhost defaults already cover host-side)"
  - "api mounts the synced copy at /mlruns so models:/ + runs:/ resolve to Linux-valid paths"
  - ".dockerignore trims venv/mlruns/data from the build context (GBs otherwise)"

patterns-established:
  - "Regenerate-then-up: .\\venv\\python.exe docker/sync_mlruns_container.py before compose up after any training/promotion"
  - "Sync script fails closed: non-zero exit if any host prefix survives in the copy"
  - "Streamlit stays a thin client: API_URL env, httpx POST only, server owns all 422s"

requirements-completed: [FR-5.1, FR-5.2, FR-4.1]

# Coverage metadata (#1602) — drives DETERMINISTIC UAT routing in verify-work.
coverage:
  - id: D1
    description: "docker compose config renders db + api + mlflow with health-gated startup and correct service URLs (FR-5.1)"
    requirement: "FR-5.1"
    verification:
      - kind: other
        ref: "docker compose -f docker/docker-compose.yml config -> exit 0, no 'error'; DATABASE_URL @db:5432, MLFLOW_TRACKING_URI http://mlflow:5000, pg_isready healthcheck"
        status: pass
    human_judgment: false
  - id: D2
    description: "Compose Postgres carries prediction logging over DATABASE_URL with no SQLite (FR-5.2, D-03)"
    requirement: "FR-5.2"
    verification:
      - kind: other
        ref: "live stack: SELECT from predictions -> prediction=1, model_version=9, created_at stamped (1 row)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Streamlit UI predicts from a 24-field form and a CSV upload against the API (FR-4.1)"
    requirement: "FR-4.1"
    verification:
      - kind: other
        ref: "py_compile frontend/app.py exit 0; posts to /predict + /batch_predict; displays model_version; zero sklearn/mlflow/sqlalchemy imports (grep 0 hits)"
        status: pass
    human_judgment: false
  - id: D4
    description: "API image builds and live /health + /model_info + /predict prove version 9 serving, stack torn down"
    requirement: "FR-5.1"
    verification:
      - kind: other
        ref: "docker compose build api exit 0; live /health 200 v9, /model_info 200 v9 run 10ac3e5e, /predict 200 v9; compose down leaves zero containers"
        status: pass
    human_judgment: false
  - id: D5
    description: "Manual browser check of streamlit run frontend/app.py against the live stack"
    requirement: "FR-4.1"
    verification: []
    human_judgment: true
    rationale: "Manual-only verification per 03-VALIDATION.md — needs a human with a browser against a live stack; automation covers compile + both API paths + suite green"

# Metrics
duration: 46min
completed: 2026-09-23
status: complete
plan_head_before: 8ec716bb18fcc1c5f69a4f3256ed0b29e2bbd8c5
commits: 3
---

# Phase 03 Plan 04: Containerization + Streamlit Frontend Summary

**Health-gated Compose stack (FastAPI + MLflow + Postgres) serving pinned corvus-ckd v9 end to end with a live Postgres log row, plus a thin Streamlit client — 45-test suite green, stack torn down**

## Performance

- **Duration:** ~46 min
- **Started:** 2026-09-23T07:20:49Z
- **Completed:** 2026-09-23T08:06:28Z
- **Tasks:** 3
- **Files modified:** 5 (4 created, 1 created-then-edited)

## Accomplishments

- Dockerfile (python:3.11-slim, layer-cached requirements, api/src/config trees, MLFLOW_ALLOW_FILE_STORE, uvicorn 0.0.0.0:8000) builds to `docker-api` with exit 0
- Compose renders db (postgres:16, pg_isready healthcheck, service_healthy gating) + api (DATABASE_URL → db:5432, MLFLOW_TRACKING_URI → mlflow:5000) + mlflow (file:///mlruns backend on the synced copy)
- Live smoke against the real stack: /health 200 `model_version 9`, /model_info 200 v9 run `10ac3e5e` pinned-at-startup, /predict 200 carrying `model_version 9` (rc=None imputer path), Postgres `predictions` row written with version + timestamp — FR-5.2 proven live, not just mocked
- Streamlit app compiles, posts a 24-field form (blanks → null) to /predict and a CSV upload to /batch_predict, names API_URL on connection failure, imports no model/DB code
- Full suite green from project root: 45 passed, 0 failed; `docker compose down` leaves zero Corvus containers

## Task Commits

Each task was committed atomically:

1. **Task 1: Write Dockerfile and health-gated Compose stack** - `fbb86ce` (feat)
2. **Task 2: Ship the thin Streamlit frontend** - `e42f126` (feat)
3. **Task 3: Build the API image and smoke the stack** - `6799020` (feat)

## Files Created/Modified

- `docker/Dockerfile` - slim-3.11 API image: cached requirements install, api/src/config trees, file-store env opt-in, uvicorn CMD
- `docker/docker-compose.yml` - db/api/mlflow services, health gating, service URLs, /mlruns mounts, allowed-hosts, OQ2 + Windows-host notes
- `docker/sync_mlruns_container.py` - host→container mlruns sync: prefix rebase to /mlruns, fail-closed leftover check, host never mutated
- `frontend/app.py` - thin client: API_URL env (localhost:8000 default), 24-field form + CSV upload over httpx, model_version display, 422 surfacing
- `.dockerignore` - venv/mlruns/data/logs/models/reports/notebooks/.git/.planning kept out of the build context

## Decisions Made

- Serve containers from `docker/.mlruns.container/` (generated, untracked) instead of host `mlruns/`: identical run IDs/versions/stages/bytes, only the location prefix differs. See deviations for why mounting host mlruns directly cannot work here.
- `mlflow --allowed-hosts "mlflow:*"` (not a wildcard `*`): exact-match Host validation rejects the compose DNS name; fnmatch `mlflow:*` admits it on any port while localhost defaults still cover host-side access.
- api mounts the synced copy at `/mlruns` (not just mlflow): the loader resolves `models:/` + `runs:/` artifact URIs to local paths inside the api box, so it needs the bytes too.
- `.dockerignore` at the repo root: the build context otherwise ships venv/ + data/ + mlruns/ (GBs) to the daemon on every build.
- Kept `docker/.mlruns.container/` on disk after teardown (untracked): next `compose up` works without re-sync unless training/promotion ran — then re-run the one-line sync first.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added root .dockerignore (venv/mlruns/data excluded from build context)**
- **Found during:** Task 3 (image build prep)
- **Issue:** Build context is the project root; without ignores the daemon receives venv/ + data/ + mlruns/ + .git (GBs) on every build — impractical and slow.
- **Fix:** `.dockerignore` excluding venv, mlruns, data, logs, models, reports, notebooks, .git, .planning, caches. Dockerfile COPY lines unchanged (only needs requirements.txt + api/src/config).
- **Files modified:** .dockerignore
- **Verification:** `build api` completes; context transfer logged as 3.15kB.
- **Committed in:** 6799020 (part of task commit)

**2. [Rule 3 - Blocking] Started Docker Desktop (daemon was down)**
- **Found during:** Task 3 (first build attempt)
- **Issue:** `docker compose build` failed: daemon unreachable at dockerDesktopLinuxEngine pipe — Desktop installed (per-user path) but not running.
- **Fix:** Launched `AppData\Local\Programs\DockerDesktop\Docker Desktop.exe`, polled to Server 29.6.2. No repo change.
- **Verification:** `docker info` reports Server Version 29.6.2.
- **Committed in:** n/a (environment, no files)

**3. [Rule 3 - Blocking] mlflow --allowed-hosts for the compose DNS name**
- **Found during:** Task 3 (api boot, lifespan registry read)
- **Issue:** MLflow 3.x Host-header validation 403s `Host: mlflow:5000` (DNS-rebinding guard, exact match) — api container cannot read the registry at all.
- **Fix:** `--allowed-hosts "mlflow:*"` on the mlflow service (fnmatch on name, any port; first tried bare `mlflow`, still 403 since the header carries `:5000`). No api source change.
- **Files modified:** docker/docker-compose.yml
- **Verification:** Registry reads succeed; lifespan proceeds past `get_model_version`.
- **Committed in:** 6799020 (part of task commit)

**4. [Rule 3 - Blocking] Container-readable mlruns sync (the big one)**
- **Found during:** Task 3 (api boot, artifact download after the Host fix)
- **Issue:** The file store records ABSOLUTE Windows artifact URIs (`c:\...\mlruns/...` in run meta, model-version storage_location, logged-model artifact_location, MLmodel artifact_path). A Linux container cannot resolve these even with the directory mounted — `models:/corvus-ckd/9` and `runs:/` reads fail `No such artifact`. Verified in MLflow 3.16.1 source: `runs:/` resolves the stored URI directly (no proxy), file-store `get_model_version_download_uri` passes storage_location through (no `--serve-artifacts` rewrite), and proxying only serves http(s)/mlflow-artifacts roots. So the plan's literal "mount host ./mlruns" cannot serve on this Windows-host topology (RESEARCH A3 flagged exactly this risk).
- **Fix:** `docker/sync_mlruns_container.py` copies host mlruns/ (minus .trash, 0.8 MB) to `docker/.mlruns.container/` rebasing ONLY the location prefix to `/mlruns` (prefix variants computed at runtime — portable, nothing hardcoded); fails closed if any host prefix survives (verified: 48 files rebased, 0 leftovers). Both api and mlflow mount the copy at `/mlruns`; server backend stays `file:///mlruns`. Host mlruns/ untouched (git status confirms no modification); v9 identity intact (same version, run_id `10ac3e5e`, Production stage).
- **Files modified:** docker/sync_mlruns_container.py (new), docker/docker-compose.yml (mounts + OQ2/Windows-host notes)
- **Verification:** api lifespan logs `Serving corvus-ckd version=9 run_id=10ac3e5e... features=24`; live /health + /model_info + /predict all version 9; Postgres row logged.
- **Committed in:** 6799020 (part of task commit)

**5. [Rule 3 - Blocking] Fixed volume relative-path base (../ vs ./)**
- **Found during:** Task 3 (`compose config` review)
- **Issue:** `../.mlruns.container` resolves from the compose file's directory (docker/) to the repo ROOT — the copy lives in docker/. Rendered source proved the mismatch.
- **Fix:** `./.mlruns.container` in both services; rendered config confirms `docker\.mlruns.container` for both mounts.
- **Files modified:** docker/docker-compose.yml
- **Verification:** `compose config` shows the correct source twice, exit 0, no `error`.
- **Committed in:** 6799020 (part of task commit)

---

**Total deviations:** 5 auto-fixed (all blocking)
**Impact on plan:** All required to reach the plan's own acceptance criteria in this environment. No api/test/host-registry changes; no scope creep beyond serving wiring. Deviation 4 bends the letter of OQ2 ("mount host ./mlruns") while keeping its spirit (zero migration, same D-01 store contents) — flagged for human review in Next Phase Readiness.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: widened-host-allowlist | docker/docker-compose.yml (mlflow `--allowed-hosts "mlflow:*"`) | Accepts any port on the compose DNS name (needed: api reaches mlflow:5000). Still local-demo only (T-03-15 accept stands); no wildcard `*`, no host-network exposure. Phase 4 can pin `mlflow:5000` exactly if desired. |

## Issues Encountered

- PowerShell `$?` over a `docker compose build | Select-Object` pipeline reported False despite `Image docker-api Built`; re-ran with `$LASTEXITCODE` → 0. Cosmetic shell quirk, not a build failure.
- An early 5-minute `Invoke-WebRequest` poll loop hung silently while the api crash-looped (lifespan 403s); switched to `compose logs` + short-timeout httpx probes — read logs first, poll second.
- Full suite takes ~56s (MLflow-backed training/registry tests dominate); API surface itself boots in seconds.

## User Setup Required

None - no external service configuration required. (Docker Desktop must be running before `compose up` — one click on this machine, no keys or accounts.)

## Manual Verification Note (per 03-VALIDATION.md)

`streamlit run frontend/app.py` against a live stack is manual-only: `.\venv\python.exe docker/sync_mlruns_container.py`, `docker compose -f docker/docker-compose.yml up -d`, `.\venv\Scripts\streamlit.exe run frontend/app.py`, exercise the form + CSV upload, then `docker compose -f docker/docker-compose.yml down`.

## Next Phase Readiness

- Phase 4 can reuse this stack as-is: `sync → up → smoke → down` is fully scripted and proven; images (`docker-api`, `docker-mlflow`) are cached locally.
- Human review wanted on deviation 4: if a future topology serves from Linux-native storage (or Postgres-backed MLflow), the sync script retires — delete `docker/.mlruns.container/` and point mounts at the native store.
- Watch item: re-run the sync after ANY new training run or registry promotion before `compose up`, or containers serve stale artifacts.
- Watch item: `docker_pgdata` volume persists across `down` (by design — the demo log row survives); `docker compose down -v` wipes it.
- Watch item: compose project name is `docker` (directory-derived); `docker ps --filter name=docker-` scopes Corvus containers.

## Self-Check: PASSED

- FOUND: docker/Dockerfile, docker/docker-compose.yml, docker/sync_mlruns_container.py, frontend/app.py, .dockerignore
- FOUND: fbb86ce, e42f126, 6799020 (git log)
- Suite: 45 passed, 0 failed; compose config exit 0; build api exit 0; live v9 on all three endpoints; zero containers after down

---
*Phase: 03-prediction-api-containerization*
*Completed: 2026-09-23*
