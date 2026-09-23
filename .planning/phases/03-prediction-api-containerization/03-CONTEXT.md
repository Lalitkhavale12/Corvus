# Phase 3: Prediction API + Containerization - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

## Phase Boundary

Serve `corvus-ckd` as a versioned FastAPI service (predict / batch_predict / health / model_info), log every prediction with its model version to PostgreSQL (Claim 4), compose API + MLflow + Postgres via Docker Compose, and ship a Streamlit UI. Training MUST NOT be re-run here — the phase starts from the Phase 2 registry state.

## Implementation Decisions

### Production promotion
- **D-01:** Promote `corvus-ckd` v9 (mlp-relu) from Staging to Production as Phase 3's first act (the human gate from Phase 2 pays off here).
- **D-02:** The API pins the serving model version at startup (config/env), not per-request resolution. Simpler and faster; model swaps require restarts — accepted trade-off, recorded here.

### Prediction-log store
- **D-03:** PostgreSQL running in Docker Compose (available: Docker v29.6.2 + Compose v5.3.1 on this machine). API logs there when `DATABASE_URL` points at it. No SQLite fallback — one backend, fully tested.
- **D-04:** Full record per prediction: request fields + prediction + probability + `model_version` + timestamp. This is the fuel Phases 4–5 monitoring and drift need.

### Input schema breadth
- **D-05:** `/predict` requires all 24 clinical fields; missing values flow through the fitted pipeline's imputers. Serve-time distribution matches training — no skew by construction.
- **D-06:** Strict validation, reject fast: bad values get a clear 422 before any inference (same fail-closed instinct as the GX gate).

### Batch input shape
- **D-07:** `/batch_predict` accepts a CSV upload with the 24 columns; server parses and predicts per row.
- **D-08:** All-or-nothing: one bad row rejects the whole batch with the offending row number. No partial-success states.

### the agent's Discretion
None — the user decided every area directly. Planner has flexibility only on code organization (module split under `api/`, compose file layout), table schema naming, and test design.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements + roadmap
- `.planning/REQUIREMENTS.md` FR-4.1 → FR-4.4, FR-5.1 → FR-5.2 — API/registry/container requirements and acceptance tests
- `.planning/ROADMAP.md` Phase 3 section — tasks, deliverables, Claim 4 note

### Phase 1–2 contracts (must not be broken)
- `src/preprocessing/preprocess.py` — `LINEAGE_ROW_COL` / `LINEAGE_ID_COL` are metadata, excluded from features; pipeline expects the 24 raw columns
- `config/config.yaml` — `data.numeric_cols` / `data.categorical_cols` (the 24-field schema source), `split.*`, `mlflow.*`; new `api.*` / `db.*` sections will extend it
- MLflow Registry `corvus-ckd`: v9 Staging → Production (D-01); v1–v8 Archived; Production empty until promotion
- `data/processed/test_raw.csv` — realistic request fixtures for API tests (never synthesize a second schema)

## Existing Code Insights

### Reusable Assets
- `src/utils/config.py:load_config()` — caller-owned deepcopy; extend `config.yaml`, never a second config mechanism
- `src/utils/logger.py:get_logger()` — module-level `log = get_logger()`
- `src/validation/validate.py:run_raw_validation()` — fail-closed gate pattern (`success=False`, `main() -> int`) for request validation flow
- `src/evaluation/evaluate.py` — MlflowClient usage patterns (search_runs, stage transitions) to mirror for version resolution
- `tests/` synthetic-fixture + `tmp_path` isolation pattern; never touch real `mlruns/` or real Postgres in tests

### Established Patterns
- `def main()` + `if __name__ == "__main__"` entry points, invoked as `python -m ...`
- Fail closed on bad input (422 here, `SystemExit` in pipeline gates)
- Immutable inputs, warning-not-crash on unexpected extras

### Integration Points
- `api/app.py` loads the Production pipeline + model at startup (pinned version), validates 24-field requests, predicts, logs full record to Postgres, returns prediction + probability + `model_version`
- `docker/docker-compose.yml` wires FastAPI + MLflow + PostgreSQL; `docker/Dockerfile` builds the API image
- `frontend/app.py` (Streamlit) posts to `/predict` and `/batch_predict`
- Phase 4 will scrape API metrics; Phase 5 will read the Postgres log for drift — schema choices here are downstream load-bearing

## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

## Deferred Ideas

None — discussion stayed within phase scope

---

*Phase: 3-Prediction API + Containerization*
*Context gathered: 2026-09-21*
