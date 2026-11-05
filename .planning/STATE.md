---
gsd_state_version: "1.0"
status: active
stopped_at: M1 code complete (P1/P2/P3/P4/P7/P8); P5 Airflow service + P6 polish remain
last_updated: "2026-11-05"
state_head: 6fc2dc9
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 15
  completed_plans: 13
  percent: 85
current_phase_name: Drift Automation + Polish (final M1 gaps)
---
# Project State — Corvus

> Auto-maintained by GSD workflow

## Current Position

- **Milestone**: M1 (Initial Build) — ~85% (6 of 8 phases code-complete)
- **Active Phase**: Phase 5 — Drift + Auto-Retraining (code complete, Airflow not yet a Compose service) and Phase 6 — Visualization + Polish
- **Next Phase**: close M1 — Airflow service in Compose, E2E/integration pass, README + architecture diagram
- **Blocked**: screening-vs-diagnostic copy sign-off; Alembic `0004` go/no-go; ~12 commits unpushed so CI has not actually run

## Phase Status

| Phase | Status | Last Updated |
|---|---|---|
| 1 — Data Pipeline | ✅ Complete | 2026-09-19 |
| 2 — Model Training | ✅ Complete | 2026-09-21 |
| 3 — API + Containers | ✅ Complete | 2026-09-23 |
| 7 — NHANES Native Retrain | ✅ Complete (v15 served) | 2026-11-05 |
| 8 — Web Platform + Authentication | ✅ Code complete (8-01…8-05 built; 8-02…8-05 plans uncommitted; no browser E2E) | 2026-11-05 |
| 4 — CI/CD + Monitoring | ✅ Complete (CI gate, `/metrics`, Prometheus + Grafana in Compose; image build/push deliberately omitted) | 2026-11-05 |
| 5 — Drift + Retraining | 🟡 ~80% (5 triggers, drift, champion/challenger, DAG written; Airflow not a Compose service, DAG never run live) | 2026-11-05 |
| 6 — Visualization + Polish | 🟡 ~70% (`src/visualization` + 9 tests, docs pass; E2E, architecture diagram, README still stale) | 2026-11-05 |

## Current Work

### Serving state (verified 2026-11-05, HEAD `6fc2dc9`)

- ✅ Model **v15** is the served version (`config/config.yaml:71` `v2_pinned_version: "15"`); `/v2/predict` live prob had been 0.8724 at threshold 0.1026
- ✅ v15 holdout: ROC-AUC **0.8214**, precision **0.3239**, recall **0.8378** — high-recall/low-precision, so the product is framed as a **screening aid, not a diagnosis**
- ✅ Full suite at HEAD: **148 passed, 1 skipped** (`python -m pytest tests -q`, ~167 s)
- ⚠️ Docker demo is stale: `docker/docker-compose.yml:51` pins `MODEL_VERSION_V2: "11"` and `docker/.mlruns.container` only holds versions 1–9. Re-sync via `docker/sync_mlruns_container.py` and pin 15 before any container demo
- ⚠️ Origin is ~12 commits behind `main`; CI (`.github/workflows/ci.yml`) has not run remotely yet

### Docs/polish pass (this session)

- ✅ `STATE.md` + `ROADMAP.md` refreshed against the real tree (this file)
- ✅ `docs/dataset_requirements.md` class-balance floor amended 20% → 10%
- ✅ Website copy: stale "Model v11" removed, screening disclaimer added to shared shell

## Completed Work

### Phase 7 plan 07-03 (v2 native serving, COMPLETE 2026-10-15)

- ✅ `CKDRequestNative` (16 nullable numerics + 5 NHANES-coded int-Literal categoricals verified against the locked CSV) + `NativeBatchItem`; v1 `CKDRequest` untouched
- ✅ `resolve_v2_version` (MODEL_VERSION_V2 else api.v2_pinned_version) + `load_v2_artifacts` with native width assert; Rule 1 fix — reads `preprocessing_pipeline_nhanes.joblib` (07-01 distinct filename), proven live: v11 GB run 5954f069 loads, width 30 == n_features_in_, real NHANES rows score
- ✅ `/v2/predict` + `/v2/batch_predict` + `/v2/model_info` with `_require_v2` 503 fail-closed naming api.v2_pinned_version; `PredictionLogV2` on `predictions_v2`; v1 handlers + `predictions` table untouched (test_api.py 19 passed unchanged)
- ✅ 15-test `tests/test_api_v2.py` (strictness, fail-closed, guards, isolation scan, v1 regression, artifact-path drift pin); full suite 74 passed, 0 failed
- ✅ Decisions: config pin stays "" (keeps test hermeticity; cutover is deploy-time MODEL_VERSION_V2=11); commits on main per sequential instruction
- ✅ Requirements FR-4.1, FR-4.2, FR-4.3 delivered (v2 serving expansion)

### Phase 7 plan 07-02 (9-config sweep + paired comparison + APPROVED promotion, COMPLETE 2026-10-15)

- ✅ 9-config `NATIVE_ESTIMATORS` (6 classical Phase-2 verbatim + MLP sigmoid/tanh/relu via ACTIVATIONS, all seed 42) with dev-only `run_cv_native` (fresh pipeline per fold), `bootstrap_auc_ci` (B=2000, default_rng 42), `sweep_native` + strict-max `select_by_cv`
- ✅ Live sweep: gradient-boosting wins (CV-mean 0.8203 ± 0.0135; DT trails 0.6310), refit on full dev, single holdout scoring (roc_auc 0.8265, CI [0.7910, 0.8572]), Claim-2 run 5954f069 + `holdout_predictions.csv` artifact, registered as corvus-ckd v11
- ✅ Eval-only `harmonize_v9` (9 shared numerics + unit notes, frozen-pipeline categorical modes, v9 read-only at pinned 9, never fit) + `evaluate_nhanes` (paired bootstrap diff CI, strict-greater rule, Production-guarded staging)
- ✅ Live paired comparison on identical locked holdout rows/labels: challenger 0.8265 vs v9-harmonized 0.5479 (documented handicap), diff CI [0.2239, 0.3349], qualifies=True
- ✅ Registry: v9 Production untouched, v10 (tracer) → Archived, v11 → Staging; `promote_challenger.py --version` created, --help verified, NEVER executed
- ✅ 9 new tests (exact-set/seeds, CV + bootstrap determinism, no-UCI-AUC scan, paired same-rows/labels, strict-max, harmonized frame, Production guard, api isolation); full suite 59 passed, 0 failed
- ✅ Decisions: winner picked on dev CV before any holdout peek; holdout-predictions artifact makes single-scoring + same-rows proof jointly satisfiable; commits on main per sequential instruction + 07-01 precedent
- ✅ Requirements FR-2.4, FR-2.5, FR-3.1, FR-3.2, FR-3.3 delivered (FR-2.1–2.3 carried)
- ✅ GATE APPROVED + EXECUTED 2026-10-15: PROMOTED corvus-ckd version=11 stage=Production; post-state v11 Production (run 5954f069) / v9 Archived (run 10ac3e5e, artifacts intact, never deleted) / all 11 versions present; full suite 59 passed post-promotion; **api.v2_pinned_version="11" for 07-03**

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

## Phase 8: Web Platform + Authentication (Code Complete)

### Sub-Phases

| Plan | Name | Status |
|---|---|---|
| 8-01 | Backend Auth Foundation (SQLAlchemy, JWT, register/login) | ✅ Built (`/auth/register`, `/auth/login`, `/auth/me`, `src/auth/`) |
| 8-02 | User Profiles & Role-Based Access | ✅ Built (`/auth/profile`, `/doctors/patients`, `test_profiles.py`) |
| 8-03 | Authenticated Predictions & History | ✅ Built (`require_user` on `/predict` + `/v2/predict`, `/auth/predictions`) |
| 8-04 | React Frontend Website | ✅ Built (10 pages under `website/src/pages/`) |
| 8-05 | Docker Compose + Local Deployment | ✅ Built (`frontend` service + `Dockerfile.frontend`) |

## Decisions Log

| # | Decision | Date | Rationale |
|---|---|---|---|
| D1 | UCI-336 as primary dataset | 2026-09-19 | Real clinical data with documented provenance |
| D2 | UCI-857 for drift simulation | 2026-09-19 | Independent cohort, confirmed valid |
| D3 | Kubernetes cut | 2026-09-19 | Docker Compose sufficient for academic demo |
| D4 | Streamlit → React + Vite | 2026-10-23 | Multi-user website requires proper frontend framework |
| D5 | Synthetic datasets rejected | 2026-09-19 | Leaky labels, circular labeling |
| D6 | Abu Dhabi EHR deferred | 2026-09-19 | Different modeling paradigm (survival analysis) |
| D7 | Quarantine gate on projected training frame | 2026-10-15 | Raw derived CSV carries the 11 label-source cols by design; gate the 16+5 projection before split (07-01 deviation) |
| D8 | Challenger v10 in stage None, v9 untouched | 2026-10-15 | Registration only in tracer; stages wait for 07-02 comparison + D-04 human gate |
| D9 | Gradient-boosting wins native sweep on dev CV before any holdout peek | 2026-10-15 | CV-mean 0.8203 strict-max; single holdout scoring 0.8265; 07-02 live run |
| D10 | Holdout-predictions artifact as the evaluation handoff | 2026-10-15 | Logged row_id/y_true/y_proba lets evaluation prove same-rows/same-labels with zero native refitting (07-02 deviation) |
| D11 | v11 Staging, v10 Archived, v9 Production; promotion script unrun | 2026-10-15 | Gate-pending registry posture; no Production transition without explicit approval (D-04) |
| D12 | APPROVE v11 executed: v11 Production, v9 Archived intact, api.v2_pinned_version="11" for 07-03 | 2026-10-15 | Explicit human approval crossed the D-04 boundary; archive_existing_versions transitioned v9 (never deleted); hard-cutover pin handed to serving |
| D13 | Config pin stays empty-string; cutover is deploy-time MODEL_VERSION_V2=11 | 2026-10-15 | Setting "11" in config.yaml would break test_api.py hermeticity (lifespan hits real registry); live v11 load probe proves the flip safe whenever deployed (07-03 decision) |
| D14 | V2 loader reads preprocessing_pipeline_nhanes.joblib (Rule 1 fix) | 2026-10-15 | Plan-literal v1 artifact path raised MlflowException against real v11; registry listing proved the native filename; drift-pinned by unit test (07-03 deviation) |
| D15 | Email/password auth only for MVP; Google OAuth deferred | 2026-10-23 | Simpler implementation; OAuth can be added later |
| D16 | Doctor self-registration with no admin gate | 2026-10-23 | Faster onboarding; access control can be tightened later |
| D17 | React + Vite + Tailwind for frontend website | 2026-10-23 | Industry standard, fast dev, responsive design, easy to learn |

## Open Questions

1. Claims 1 and 3 — full text not yet shared, cannot assess compliance
2. Abu Dhabi EHR file — defer to stretch goal or integrate into core?
3. Screening vs diagnostic — product copy now assumes **screening** (precision 0.32 makes "diagnosis" indefensible); needs an explicit yes/no from the user
4. Alembic `0004` for `predictions`/`predictions_v2` — skipped on purpose (`api/db.py` `create_all` already owns those tables; `alembic/env.py` targets the auth `Base` only). Confirm keep-as-is or add the migration
5. Deltas below 0.02 ROC are noise — do not read a version bump as an improvement without the paired CI

## Context for Next Session

Close M1's remaining gaps, in this order:
1. Push `main` (~12 commits) so CI actually runs.
2. Re-sync `docker/.mlruns.container` (holds versions 1–9 only) and bump `MODEL_VERSION_V2` to 15.
3. Phase 5: add the Airflow service to Compose and run `corvus_drift_retrain` once end-to-end.
4. Phase 6: integration/E2E pass, architecture diagram, README rewrite (its phase checklist is two generations stale).
5. Commit the uncommitted `.planning/phases/08-*` plans and `07-PATTERNS.md` / `07-REVIEW.md`.

## Session

**Last session:** 2026-11-05
**Stopped at:** M1 code complete; docs/polish pass landed (STATE, ROADMAP, dataset doctrine, website copy)
**Resume file:** .planning/ROADMAP.md
