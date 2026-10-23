# Roadmap — Corvus MLOps Pipeline

> Milestone: M1 (Initial Build)
> Status: Active
> Last updated: 2026-10-23

## Phase Overview

| Phase | Name | Status | Requirements | Dependencies |
|---|---|---|---|---|
| **1** | Data Pipeline | ✅ Complete | FR-1.1 → FR-1.7 | None |
| **2** | Model Training + Experiment Tracking | ✅ Complete | FR-2.1 → FR-2.5, FR-3.1 → FR-3.3 | Phase 1 |
| **3** | Prediction API + Containerization | ✅ Complete | FR-4.1 → FR-4.4, FR-5.1 → FR-5.2 | Phase 2 |
| **7** | NHANES Native Retrain | ✅ Complete | FR-2.1 → FR-4.3 | Phase 3 |
| **8** | Web Platform + Authentication | 🔄 In Progress | FR-9.1 → FR-9.6, FR-10.1 → FR-10.3 | Phase 3 |
| **4** | CI/CD + Monitoring | ⬜ Not Started | FR-6.1, FR-7.1 → FR-7.2 | Phase 8 |
| **5** | Drift Detection + Auto-Retraining | ⬜ Not Started | FR-8.1 → FR-8.3, FR-9.1 → FR-9.4 | Phase 4 |
| **6** | Visualization + Polish | ⬜ Not Started | FR-10.1 → FR-10.2, NFR-1 → NFR-5 | Phase 1 (can parallel) |

---

## Phase 1: Data Pipeline

**Status**: ✅ Complete (verified 2026-09-19, 13/13 tests green, 14/14 must-haves)
**Delivers**: `data/processed/{train,val,test}.csv` + `preprocessing_pipeline.joblib`
**Patent impact**: Claim 2 (pipeline artifact exists)

### Completed

- [x] Raw data ingestion with UCI CKD quirk handling (`src/ingestion/load_data.py`)
- [x] Data quality summary to `reports/` (`summarize()`)
- [x] Leak-safe preprocessing: split-first, fit on train only (`src/preprocessing/preprocess.py`)
- [x] Single sklearn Pipeline artifact (ColumnTransformer: imputer + scaler + OneHotEncoder)
- [x] Config-driven paths, splits, strategies (`config/config.yaml`)
- [x] Centralized logging (Loguru → stderr + file)
- [x] 4 pytest tests passing (clean, split disjointness, Pipeline type, no NaN)
- [x] EDA notebook (`notebooks/01_eda_ckd.ipynb`) — distributions, correlations, missing-value heatmap
- [x] Great Expectations data validation schema (`data/validation/ckd_suite.json` + `validate.py`, GX 1.x)
- [x] Additional test coverage (ingestion tests, `save_outputs()` integration test — 13/13 green)

---

## Phase 2: Model Training + Experiment Tracking

**Status**: ✅ Implementation Complete (plans 02-01 tracer + 02-02 expansion done 2026-09-21; 9 runs, winner mlp-relu v9 Staging)
**Delivers**: Trained models logged to MLflow, best model registered
**Patent impact**: Claim 2 completion (pipeline + model in same MLflow run)
**Depends on**: Phase 1 outputs (`data/processed/`, `preprocessing_pipeline.joblib`)

### Completed

- [x] Plan 02-01 tracer: LR end-to-end (`src/training/train.py`), strict ROC-AUC ranking + Staging (`src/evaluation/evaluate.py`), Wave 0 fixtures
- [x] Plan 02-02 expansion: `src/training/train.py` — LR, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM (seeded, one rationale each)
- [x] Plan 02-02 expansion: `src/training/train_mlp.py` — MLP with Sigmoid, Tanh, ReLU as separate runs
- [x] `src/evaluation/evaluate.py` — accuracy, precision, recall, F1, ROC-AUC per model; run_id-linked winner resolution
- [x] MLflow tracking (`mlflow.tracking_uri` from config, resolved against PROJECT_ROOT)
- [x] `preprocessing_pipeline.joblib` + model as artifacts in same MLflow run (**Claim 2**, all 9 runs)
- [x] Compared all 9 models, best by strict-max ROC-AUC (winner: mlp-relu)
- [x] Best model registered to MLflow Model Registry (v9 Staging, v1–v8 Archived, Production untouched)
- [ ] Create `src/feature_engineering/features.py` if feature selection adds value
- [x] Training, evaluation, and registry tests (26 green)

---

## Phase 3: Prediction API + Containerization

**Status**: ✅ Complete (03-01, 03-02, 03-03, 03-04 complete 2026-09-23)
**Delivers**: FastAPI service, Docker Compose stack, PostgreSQL prediction logging
**Patent impact**: Claim 4 (model version per prediction)
**Depends on**: Phase 2 (registered model in MLflow)

### Completed

- [x] 03-01-PLAN.md — Promotion v9 to Production plus deps plus config plus Wave 0 API stubs (wave 1, complete 2026-09-23: v9 Production, 26 passed, 8 stubs red)
- [x] 03-02-PLAN.md — Tracer: schemas plus loader plus /predict plus /health plus /model_info pinned version live (wave 2, complete 2026-09-23: versioned serving + fail-closed DB + 38 green)
- [x] 03-03-PLAN.md — /batch_predict all-or-nothing plus full-record Postgres logging (wave 3, complete 2026-09-23: 413 guards + warn-ignore extras + typed response + 45 green)
- [x] 03-04-PLAN.md — Dockerfile plus Compose stack plus Streamlit frontend (wave 3, complete 2026-09-23: image builds, live v9 on health/model_info/predict, Postgres row logged, 45 green, stack down)

- [x] Create `api/app.py` — FastAPI application (lifespan pin + 4 routes)
- [x] Create `api/schemas.py` — Pydantic models with `model_version` field (**Claim 4**)
- [x] Implement endpoints: `/predict`, `/batch_predict`, `/health`, `/model_info`
- [x] Resolve production model version from MLflow Registry per request (D-02 deviation: pinned at startup, swaps need restarts)
- [x] Create prediction logging to PostgreSQL (full-record rows + single-commit batches, mocked-session tests, 03-03)
- [x] Create `docker/Dockerfile` for FastAPI service
- [x] Create `docker/docker-compose.yml` — FastAPI + MLflow + PostgreSQL
- [x] Create `frontend/app.py` — Streamlit UI for predictions (to be replaced by React website)
- [x] Write API tests

---

## Phase 7: NHANES Native Retrain

**Status**: ✅ Complete (07-01 + 07-02 + 07-03 done 2026-10-15: v11 Production, /v2 serving-path live with fail-closed default, v1 untouched, suite 74 passed)
**Delivers**: NHANES-native pipeline + 9 configs trained on 5,343 derived rows, CV + CIs, challenger vs v9 champion, winner promoted, API serving new schema
**Patent impact**: None new (exercises Claim 2 + Claim 4 on a second cohort)
**Depends on**: Phase 3 (registry + serving loop); data track (`data/nhanes/nhanes_ckd_derived.csv`, `NHANES_PROTOCOL.md`)

### Completed

- [x] 07-01-PLAN.md — Tracer: native pipeline plus quarantine gate plus LR Claim-2 run plus Wave 0 training tests (wave 1, complete 2026-10-15: LR holdout roc_auc=0.8246, challenger v10, suite 50 passed)
- [x] 07-02-PLAN.md — 9-config CV expansion plus paired harmonized comparison plus Staging plus human promotion gate (wave 2, COMPLETE 2026-10-15: GB winner holdout 0.8265, paired qualifies=True, gate APPROVED → v11 Production / v9 Archived intact, pin "11" for 07-03, suite 59 passed post-promotion)
- [x] 07-03-PLAN.md — Native schemas plus v2 loader slot plus /v2 routes plus v2 log table plus v2 tests (wave 2, COMPLETE 2026-10-15: /v2 serves version-stamped native predictions with isolated logging, unconfigured 503 fail-closed, Rule 1 native-artifact-path fix proven live against v11, suite 74 passed; cutover is deploy-time MODEL_VERSION_V2=11)

- [x] Native config keys in config.yaml (16+5 allow-list, 11 quarantine names, 0.2/42 split, 5-fold, 2000 bootstrap; existing keys byte-identical)
- [x] `src/preprocessing/preprocess_nhanes.py`: QUARANTINE_11, DERIVED_LABEL_DISCLOSURE, allow-list column lists, gate-before-split, unfitted native pipeline, locked 80/20 split
- [x] `src/training/train_nhanes.py`: 9-config NATIVE_ESTIMATORS with dev-only run_cv_native, bootstrap_auc_ci, sweep_native + strict-max select_by_cv
- [x] `src/evaluation/evaluate_nhanes.py`: paired bootstrap diff CI, strict-greater rule, Production-guarded staging
- [x] `src/training/harmonize_v9.py`: eval-only harmonization adapter, unreachable from serving code
- [x] `api/schemas.py`: CKDRequestNative (16 nullable numerics + 5 NHANES-coded int-Literal categoricals) + NativeBatchItem
- [x] `api/app.py`: /v2/predict, /v2/batch_predict, /v2/model_info with _require_v2 503 fail-closed; PredictionLogV2 on predictions_v2
- [x] v1 routes untouched: /predict, /batch_predict, /health, /model_info serving v9
- [x] Docker Compose: MODEL_VERSION_V2=11 pinned for api service; synced mlruns container copy
- [x] Streamlit frontend remapped to /v2 endpoints with NHANES-native form fields (committed 51dd12b)
- [x] Full suite: 74 passed, 0 failed

---

## Phase 8: Web Platform + Authentication (NEW)

**Status**: 🔄 In Progress
**Delivers**: Multi-user React website with email/password auth, patient/doctor roles, authenticated predictions, prediction history
**Patent impact**: Claim 4 (model version per prediction, now user-linked)
**Depends on**: Phase 3 (FastAPI backend, MLflow registry, Docker Compose)

### Plans

#### Wave 1: Backend Auth Foundation

- [x] **8-01-PLAN.md** — SQLAlchemy + Alembic setup, User model, password hashing, JWT tokens, register/login endpoints, protected route dependencies

#### Wave 2: User Profiles & Role-Based Access

- [ ] **8-02-PLAN.md** — Patient and doctor profile models, profile creation endpoints, patient-doctor mapping, role-based dependencies (get_current_patient, get_current_doctor)

#### Wave 3: Authenticated Predictions & History

- [ ] **8-03-PLAN.md** — Protect /v2/predict and /v2/batch_predict with JWT, link predictions to user profiles, prediction history endpoints, patient dashboard data

#### Wave 4: React Frontend Website

- [ ] **8-04-PLAN.md** — React + Vite + Tailwind frontend, login/register pages, patient dashboard, doctor dashboard, prediction form, history pages, protected routes

#### Wave 5: Docker Compose + Local Deployment

- [ ] **8-05-PLAN.md** — Frontend service in Docker Compose, CORS configuration, environment variables (SECRET_KEY, DATABASE_URL), local run verification

---

## Phase 4: CI/CD + Monitoring

**Status**: ⬜ Not Started
**Delivers**: GitHub Actions workflow, Prometheus metrics, Grafana dashboard
**Depends on**: Phase 8 (Docker image to build/push)

### Tasks

- [ ] Create `.github/workflows/ci.yml` — test → build → push image
- [ ] Create `src/monitoring/metrics.py` — Prometheus instrumentation (latency, request count, error rate)
- [ ] Create Grafana dashboard JSON/provisioning
- [ ] Add Prometheus + Grafana to Docker Compose
- [ ] Write monitoring tests

---

## Phase 5: Drift Detection + Auto-Retraining

**Status**: ⬜ Not Started
**Delivers**: Evidently AI drift reports, Airflow DAGs, champion/challenger promotion
**Patent impact**: Claim 5 (5 trigger types + promotion + archived retention)
**Depends on**: Phase 4 (monitoring infrastructure)

### Tasks

- [ ] Create `src/monitoring/drift.py` — Evidently AI report (UCI-336 baseline vs. UCI-857 batch)
- [ ] Create `airflow/dags/` — 5 trigger-type DAGs (**Claim 5**)
- [ ] Implement conditional retrain → re-register → redeploy
- [ ] Implement champion/challenger model comparison + promotion
- [ ] Verify MLflow Registry Staging/Production/Archived stages for retention
- [ ] Add Airflow to Docker Compose
- [ ] Write drift detection and retraining tests

---

## Phase 6: Visualization + Polish

**Status**: ⬜ Not Started
**Delivers**: Standalone visualization module, integration tests, documentation
**Patent impact**: Component 102 (data visualization module)
**Can run in parallel with**: Phase 2+ (only depends on Phase 1 data)

### Tasks

- [ ] Create `src/visualization/` module (**Component 102**)
- [ ] End-to-end integration testing
- [ ] Documentation pass, architecture diagram, demo script
- [ ] Final README update
