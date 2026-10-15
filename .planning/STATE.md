---
gsd_state_version: "1.0"
status: unknown
stopped_at: Completed 07-01-PLAN.md
last_updated: "2026-10-15T08:05:03Z"
state_head: e94acff
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 12
  completed_plans: 10
  percent: 0
current_phase_name: NHANES Native Retrain
---

# Project State — Corvus

> Auto-maintained by GSD workflow

## Current Position

- **Milestone**: M1 (Initial Build)
- **Active Phase**: Phase 7 — NHANES Native Retrain (07-01 complete; 07-02 tasks 1-2 complete 2026-10-15, BLOCKING-HUMAN promotion gate OPEN for challenger v11)
- **Next Phase**: Human gate decision on 07-02 task 3 (APPROVE v11 → promote + pin for 07-03; REJECT → v9 stays) then 07-03 v2 serving
- **Blocked**: 07-02 task 3 + 07-03 v2 pin await the human promotion decision — by design (D-04)

## Phase Status

| Phase | Status | Last Updated |
|---|---|---|
| 1 — Data Pipeline | ✅ Complete | 2026-09-19 |
| 2 — Model Training | ✅ Implementation Complete (02-01 tracer + 02-02 expansion done) | 2026-09-21 |
| 3 — API + Containers | ✅ Complete (03-01, 03-02, 03-03, 03-04 done 2026-09-23) | 2026-09-23 |
| 4 — CI/CD + Monitoring | ⬜ Not Started | — |
| 7 — NHANES Native Retrain | 🔄 In Progress (07-01 complete; 07-02 gate open for v11) | 2026-10-15 |
| 5 — Drift + Retraining | ⬜ Not Started | — |
| 6 — Visualization + Polish | ⬜ Not Started | — |

## Completed Work

### Phase 7 plan 07-02 (9-config sweep + paired comparison, tasks 1-2 complete 2026-10-15; task 3 GATE OPEN)

- ✅ 9-config `NATIVE_ESTIMATORS` (6 classical Phase-2 verbatim + MLP sigmoid/tanh/relu via ACTIVATIONS, all seed 42) with dev-only `run_cv_native` (fresh pipeline per fold), `bootstrap_auc_ci` (B=2000, default_rng 42), `sweep_native` + strict-max `select_by_cv`
- ✅ Live sweep: gradient-boosting wins (CV-mean 0.8203 ± 0.0135; DT trails 0.6310), refit on full dev, single holdout scoring (roc_auc 0.8265, CI [0.7910, 0.8572]), Claim-2 run 5954f069 + `holdout_predictions.csv` artifact, registered as corvus-ckd v11
- ✅ Eval-only `harmonize_v9` (9 shared numerics + unit notes, frozen-pipeline categorical modes, v9 read-only at pinned 9, never fit) + `evaluate_nhanes` (paired bootstrap diff CI, strict-greater rule, Production-guarded staging)
- ✅ Live paired comparison on identical locked holdout rows/labels: challenger 0.8265 vs v9-harmonized 0.5479 (documented handicap), diff CI [0.2239, 0.3349], qualifies=True
- ✅ Registry: v9 Production untouched, v10 (tracer) → Archived, v11 → Staging; `promote_challenger.py --version` created, --help verified, NEVER executed
- ✅ 9 new tests (exact-set/seeds, CV + bootstrap determinism, no-UCI-AUC scan, paired same-rows/labels, strict-max, harmonized frame, Production guard, api isolation); full suite 59 passed, 0 failed
- ✅ Decisions: winner picked on dev CV before any holdout peek; holdout-predictions artifact makes single-scoring + same-rows proof jointly satisfiable; commits on main per sequential instruction + 07-01 precedent
- ✅ Requirements FR-2.4, FR-2.5, FR-3.1, FR-3.2 delivered (FR-2.1–2.3 carried); FR-3.3 awaits the gate
- ⏳ GATE OPEN: APPROVE (run promote_challenger --version 11, record pin for 07-03) or REJECT (v9 stays, v11 held in Staging)

### Phase 7 plan 07-01 (tracer native retrain, complete 2026-10-15)

- ✅ Native config keys in config.yaml (16+5 allow-list, 11 quarantine names, 0.2/42 split, 5-fold, 2000 bootstrap; existing keys byte-identical) + `mlflow.nhanes_experiment_name` + `api.v2_pinned_version=""`
- ✅ `src/preprocessing/preprocess_nhanes.py`: QUARANTINE_11, DERIVED_LABEL_DISCLOSURE (D-08), allow-list column lists, gate-before-split, unfitted native pipeline, locked 80/20 split
- ✅ `src/training/train_nhanes.py`: LR-only NATIVE_ESTIMATORS (seed 42), run_experiment_native (gate → locked split → dev-only fit → Claim-2 run schema=nhanes-native)
- ✅ Live tracer: holdout roc_auc=0.8246 (accuracy 0.85, recall 0.28), challenger corvus-ckd v10 registered in stage None; v9 stays Production
- ✅ 5 Wave 0 tests (quarantine abort, pipeline shape, tmp-store Claim-2, holdout disjoint, seeded LR); full suite 50 passed, 0 failed
- ✅ Decisions: gate checks the projected training frame (raw CSV carries label-source cols by design); native pipeline artifact filename distinct from v1; v10 left in stage None for the 07-02 comparison + human gate
- ✅ Requirements FR-2.1, FR-2.2, FR-2.3 opened here

### Phase 3 plan 03-04 (containerization + frontend, complete 2026-09-23)

- ✅ Dockerfile (python:3.11-slim, cached requirements, api/src/config, uvicorn 0.0.0.0:8000) builds exit 0; .dockerignore keeps venv/mlruns/data out of context
- ✅ Compose db + api + mlflow renders exit 0 (pg_isready health gate, DATABASE_URL @db:5432, MLFLOW_TRACKING_URI http://mlflow:5000)
- ✅ Live smoke: /health 200 v9, /model_info 200 v9 run 10ac3e5e pinned-at-startup, /predict 200 v9 (rc=None imputer path); Postgres predictions row proves FR-5.2 live; stack down to zero containers
- ✅ Streamlit thin client (24-field form + CSV upload, API_URL env, zero model logic); py_compile clean, 45-test suite green
- ✅ Decisions: container-synced mlruns copy with /mlruns-rebased URIs (host pristine, v9 identity intact); mlflow --allowed-hosts mlflow:*; api mounts the copy at /mlruns
- ✅ Requirements FR-5.1, FR-5.2, FR-4.1 delivered — Phase 3 COMPLETE

### Phase 3 plan 03-03 (batch expansion, complete 2026-09-23)

- ✅ Hardened POST /batch_predict: MAX_BATCH_BYTES 5000000 + MAX_BATCH_ROWS 10000 with 413 before full parse, lineage/target dropped via imported constants, missing-column 422, extras warn-ignored (T-03-08), all-or-nothing with first-offender row number, single commit
- ✅ BatchPredictionItem/BatchPredictionResponse schemas (row, prediction, probability, count, model_version 9)
- ✅ D-04 full record: per-row created_at stamp + column default; every logged row holds 24 fields + outcome + version + timestamp
- ✅ 7 new tests (valid batch, row-3 zero-write rejection, missing column, 413 oversize, extras ignored, full-record shape, batch 503); API file 19 passed, full suite 45 passed, 0 failed
- ✅ db.py review clean: no raw SQL, retry only around create_tables, DATABASE_URL value never logged
- ✅ Requirements FR-4.1, FR-4.2, FR-4.3, FR-5.2 delivered
- ✅ Decisions: warn-ignore over 422 for extras; per-row created_at stamp; single shared commit call site (not 2 per-route)

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
| D7 | Quarantine gate on projected training frame | 2026-10-15 | Raw derived CSV carries the 11 label-source cols by design; gate the 16+5 projection before split (07-01 deviation) |
| D8 | Challenger v10 in stage None, v9 untouched | 2026-10-15 | Registration only in tracer; stages wait for 07-02 comparison + D-04 human gate |
| D9 | Gradient-boosting wins native sweep on dev CV before any holdout peek | 2026-10-15 | CV-mean 0.8203 strict-max; single holdout scoring 0.8265; 07-02 live run |
| D10 | Holdout-predictions artifact as the evaluation handoff | 2026-10-15 | Logged row_id/y_true/y_proba lets evaluation prove same-rows/same-labels with zero native refitting (07-02 deviation) |
| D11 | v11 Staging, v10 Archived, v9 Production; promotion script unrun | 2026-10-15 | Gate-pending registry posture; no Production transition without explicit approval (D-04) |

## Open Questions

1. Claims 1 and 3 — full text not yet shared, cannot assess compliance
2. Abu Dhabi EHR file — defer to stretch goal or integrate into core?

## Context for Next Session

Start with `/gsd-plan-phase 2` to begin model training (Phase 1 is complete and verified).

## Session

**Last session:** 2026-10-15T08:05:03Z
**Stopped at:** 07-02 tasks 1-2 complete (sweep + comparison live, v11 Staging); BLOCKING-HUMAN gate open on task 3
**Resume file:** .planning/phases/07-nhanes-native-retrain/07-02-SUMMARY.md
