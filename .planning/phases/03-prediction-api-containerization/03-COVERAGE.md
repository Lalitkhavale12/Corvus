# Phase 3 — API Coverage Matrix

> Satisfies the `api-coverage.verify-pre` gate. Canonical table schema
> (`capability | decision | reason`), one row per capability.
> Scope note: this phase builds a first-party API (our own FastAPI service).
> No third-party SaaS APIs are integrated; external touchpoints are local
> infrastructure (PostgreSQL, MLflow file store).

| capability | decision | reason |
|---|---|---|
| POST /predict: 24-field request to prediction plus probability plus version | INTEGRATE | Built in api/app.py, tested in tests/test_api.py |
| POST /batch_predict: CSV upload, all-or-nothing with row number on 422 | INTEGRATE | Built in api/app.py, tested with -k batch |
| GET /health: liveness plus serving version | INTEGRATE | Built in api/app.py, tested with -k health |
| GET /model_info: pinned version, run id, feature list | INTEGRATE | Built in api/app.py, tested with -k model_info |
| Postgres prediction log: full record incl. model_version | INTEGRATE | api/db.py PredictionLog, provisioned by compose |
| Registry read at startup: pinned Production version and artifacts | INTEGRATE | api/model_loader.py, serving corvus-ckd v9 |
| Compose stack: API plus MLflow plus Postgres, health-gated | INTEGRATE | docker/Dockerfile and compose file, proven by smoke |
| Streamlit UI over predict and batch_predict | INTEGRATE | frontend/app.py, covered by manual UAT test 2 |

| capability | decision | reason |
|---|---|---|
| Third-party or SaaS API integrations | OPT-OUT | None exist; only local libraries and local infra |
| Tracking writes from the API (new runs or metrics) | OPT-OUT | Inference-only by design; Registry reads only |
| Auth, API keys, rate limiting | OPT-OUT | Localhost academic demo; known gap for public deploy |
| Per-request Registry re-resolution | OPT-OUT | Superseded by locked D-02 startup pin; swaps need restarts |
| SQLite or non-Postgres log backends | OPT-OUT | Locked D-03: one backend, fully tested |

## Verification

- `.\venv\python.exe -m pytest tests -q` — 45 green, covers every INTEGRATE row except the two manual UAT items
- Container smoke recorded in `03-04-SUMMARY.md`; manual items tracked in `03-UAT.md`
