---
gsd_state_version: "1.0"
status: unknown
stopped_at: Phase 3 context gathered
last_updated: "2026-09-23T06:36:38Z"
state_head: b8b69e64e58724a1991cff368394d9f753a83363
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 9
  completed_plans: 6
  percent: 0
current_phase_name: Prediction API + Containerization
---

# Project State — Corvus

> Auto-maintained by GSD workflow

## Current Position

- **Milestone**: M1 (Initial Build)
- **Active Phase**: Phase 3 — Prediction API + Containerization (plans 03-01, 03-02 complete 2026-09-23)
- **Next Phase**: Phase 3 plan 03-03 (batch logging hardening + full-record Postgres logging)
- **Blocked**: Nothing

## Phase Status

| Phase | Status | Last Updated |
|---|---|---|
| 1 — Data Pipeline | ✅ Complete | 2026-09-19 |
| 2 — Model Training | ✅ Implementation Complete (02-01 tracer + 02-02 expansion done) | 2026-09-21 |
| 3 — API + Containers | 🔄 In Progress (03-01, 03-02 done 2026-09-23) | 2026-09-23 |
| 4 — CI/CD + Monitoring | ⬜ Not Started | — |
| 5 — Drift + Retraining | ⬜ Not Started | — |
| 6 — Visualization + Polish | ⬜ Not Started | — |

## Completed Work

### Phase 3 plan 03-02 (tracer slice, complete 2026-09-23)

- ✅ api package: schemas (24-field CKDRequest + versioned responses), pinned loader (models:/corvus-ckd/9 + pipeline width assert), db layer (PredictionLog + 3-attempt create_tables), FastAPI app (lifespan pin + /predict + /batch_predict + /health + /model_info)
- ✅ Live probe: load_serving_artifacts(9) against real registry → run_id 10ac3e5e, n_features_in_=24
- ✅ Fail-closed proven: 422 on bad input, 503 naming DATABASE_URL when unset, RuntimeError after 3 retries when unreachable
- ✅ 12 API tests green (mocked loader/session, no real mlruns/Postgres); full suite 38 passed, 0 failed
- ✅ Requirements FR-4.1, FR-4.2, FR-4.3, FR-4.4 delivered (FR-4.4 with recorded D-02 startup-pin deviation)
- ✅ Decisions: fail-closed 503 over silent serving; /batch_predict pulled into 03-02 so all 8 stubs go green; model_info follows plan contract (model_name/model_version/run_id/resolution); sequential commits stay on main

### Phase 3 plan 03-01 (foundation, complete 2026-09-23)

- ✅ corvus-ckd v9 Staging → Production via scripts/promote_production.py (D-01 first act, PROMOTED line + registry audit trail)
- ✅ Serving deps installed + pinned: psycopg2-binary 2.9.13, streamlit 1.64.0, python-multipart 0.0.32 (Task 1 human-approved)
- ✅ config.yaml api.* (model_name, pinned_version 9, tracking_uri) + db.* (database_url "") sections via load_config
- ✅ Wave 0 fixtures (synthetic_ckd_request, synthetic_batch_csv) + 8 red API stubs (red by design: collection error on api.app until 03-02)
- ✅ 26 pytest tests green excluding test_api.py; requirements FR-4.4, FR-4.3 foundation delivered
- ✅ Decisions: promotion script hardcodes v9 (future swaps via config pin + new run); env-over-static config fallback; sys.path bootstrap for plain-script runs

### Phase 2 plan 02-02 (9-config expansion, complete 2026-09-21)

- ✅ 6 classical configs in train.py (LR untouched, DT/RF/GB/XGB/LGBM seeded 42, LGBM verbosity=-1, one rationale each)
- ✅ train_mlp.py: 3 activation runs reusing train.py shapes (hidden (50,), max_iter 500, seeded, no early stopping)
- ✅ run_id-linked winner→version resolution (tracer latest-heuristic broke at 9 versions)
- ✅ Canonical pass: 9 runs × (5 metrics + pipeline + model), corvus-ckd v1–v9, winner mlp-relu v9 Staging, 8 Archived, 0 Production
- ✅ 26 pytest tests green; requirements FR-2.1, FR-2.5, FR-3.1, FR-3.2, FR-3.3 delivered
- ✅ Decisions: ModelVersion.run_id linkage for winner resolution, mlp reuses train helpers, reset gitignored mlruns for canonical pass

### Phase 2 plan 02-01 (tracer slice, complete 2026-09-21)

- ✅ LR trains end-to-end from train_raw.csv into one Claim 2 MLflow run (roc_auc=1.0, 5 metrics)
- ✅ evaluate.py strict-max ROC-AUC ranking; winner corvus-ckd v1 in Staging, no Production
- ✅ 24 pytest tests green; Wave 0 red-to-green
- ✅ Decisions: MLflow 3.x logged-model linkage assertions, MLFLOW_ALLOW_FILE_STORE opt-in, search_model_versions for history

### Phase 1 (complete, verified 2026-09-19)

- ✅ Raw data ingestion with UCI CKD quirk handling
- ✅ Leak-safe preprocessing (split-first, fit on train only)
- ✅ Single sklearn Pipeline artifact (Patent Claim 2 — object created)
- ✅ Config-driven pipeline (`config/config.yaml`)
- ✅ Centralized Loguru logging
- ✅ GX 1.x raw-CSV validation gate (`data/validation/ckd_suite.json` + `validate.py`, fail-fast in `preprocess.main()`)
- ✅ Read-only EDA notebook (`notebooks/01_eda_ckd.ipynb`, 11 cells, outputs cleared, 5 figures in `reports/figures/`)
- ✅ 13 pytest tests passing (4 pre-existing + 9 new: ingestion quirks, save_outputs isolation, validation gate)
- ✅ Phase verified 14/14 must-haves (`.planning/phases/phase-1/01-VERIFICATION.md`)
- ✅ Codebase mapped (`.planning/codebase/`)
- ✅ Project initialized (`.planning/`)

## Decisions Log

| # | Decision | Date | Rationale |
|---|---|---|---|
| D1 | UCI-336 as primary dataset | 2026-09-19 | Real clinical data with documented provenance |
| D2 | UCI-857 for drift simulation | 2026-09-19 | Independent cohort, confirmed valid |
| D3 | Kubernetes cut | 2026-09-19 | Docker Compose sufficient for academic demo |
| D4 | React → Streamlit | 2026-09-19 | Single Python file, no frontend build |
| D5 | Synthetic datasets rejected | 2026-09-19 | Leaky labels, circular labeling |
| D6 | Abu Dhabi EHR deferred | 2026-09-19 | Different modeling paradigm (survival analysis) |

## Open Questions

1. Claims 1 and 3 — full text not yet shared, cannot assess compliance
2. Abu Dhabi EHR file — defer to stretch goal or integrate into core?

## Context for Next Session

Start with `/gsd-plan-phase 2` to begin model training (Phase 1 is complete and verified).

## Session

**Last session:** 2026-09-23T06:59:10Z
**Stopped at:** Completed 03-02-PLAN.md
**Resume file:** None
