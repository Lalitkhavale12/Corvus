---
gsd_state_version: "1.0"
status: unknown
stopped_at: Phase 3 context gathered
last_updated: "2026-09-23T06:17:56.076Z"
state_head: b8b69e64e58724a1991cff368394d9f753a83363
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 9
  completed_plans: 5
  percent: 0
current_phase_name: Prediction API + Containerization
---

# Project State — Corvus

> Auto-maintained by GSD workflow

## Current Position

- **Milestone**: M1 (Initial Build)
- **Active Phase**: Phase 2 — Model Training + Experiment Tracking (plans 02-01 tracer + 02-02 expansion complete 2026-09-21)
- **Next Phase**: Phase 2 verify-work, then Phase 3 — API + Containers
- **Blocked**: Nothing

## Phase Status

| Phase | Status | Last Updated |
|---|---|---|
| 1 — Data Pipeline | ✅ Complete | 2026-09-19 |
| 2 — Model Training | ✅ Implementation Complete (02-01 tracer + 02-02 expansion done) | 2026-09-21 |
| 3 — API + Containers | ⬜ Not Started | — |
| 4 — CI/CD + Monitoring | ⬜ Not Started | — |
| 5 — Drift + Retraining | ⬜ Not Started | — |
| 6 — Visualization + Polish | ⬜ Not Started | — |

## Completed Work

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

**Last session:** 2026-09-23T05:45:50.410Z
**Stopped at:** Phase 3 context gathered
**Resume file:** .planning/phases/03-prediction-api-containerization/03-CONTEXT.md
