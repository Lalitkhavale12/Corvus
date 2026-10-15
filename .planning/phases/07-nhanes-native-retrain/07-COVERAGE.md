# Phase 7 — API Coverage Matrix

> Satisfies the `api-coverage.verify-pre` gate. Canonical table schema
> (`capability | decision | reason`). Covers the new /v2 surface only —
> the v1 surface is matrixed in `../03-prediction-api-containerization/03-COVERAGE.md`
> and byte-identical by lock.

| capability | decision | reason |
|---|---|---|
| POST /v2/predict: native-schema request to versioned prediction | INTEGRATE | Built in api/app.py, tested in tests/test_api_v2.py |
| POST /v2/batch_predict: native CSV, all-or-nothing with row numbers | INTEGRATE | Built in api/app.py, tested in tests/test_api_v2.py |
| GET /v2/model_info: challenger identity and resolution | INTEGRATE | Built in api/app.py, tested in tests/test_api_v2.py |
| predictions_v2 table: native full record incl. model_version | INTEGRATE | Separate table, zero v1 blast radius |
| v1 routes (/predict, /batch_predict, /health, /model_info) | OPT-OUT | Frozen by lock; covered by Phase 3 matrix, unchanged |
| Tracking writes from /v2 (new runs or metrics) | OPT-OUT | Inference-only by design; Registry reads only |
| Auth, API keys, rate limiting on /v2 | OPT-OUT | Localhost demo; known gap, same as v1 |
| Shadow or canary routing between v1 and /v2 | OPT-OUT | Locked D-06 hard cutover; no splitting machinery |

## Verification

- `.\venv\python.exe -m pytest tests/test_api_v2.py -q` — green, covers every INTEGRATE row except the deployed-env manual UAT item
- Manual items tracked in `07-UAT.md`
