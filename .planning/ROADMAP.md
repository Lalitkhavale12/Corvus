# Roadmap — Corvus MLOps Pipeline

> Milestone: M1 (Initial Build)
> Status: Active
> Last updated: 2026-09-19

## Phase Overview

| Phase | Name | Status | Requirements | Dependencies |
|---|---|---|---|---|
| **1** | Data Pipeline | ✅ Complete | FR-1.1 → FR-1.7 | None |
| **2** | Model Training + Experiment Tracking | ⬜ Not Started | FR-2.1 → FR-2.5, FR-3.1 → FR-3.3 | Phase 1 |
| **3** | Prediction API + Containerization | ⬜ Not Started | FR-4.1 → FR-4.4, FR-5.1 → FR-5.2 | Phase 2 |
| **4** | CI/CD + Monitoring | ⬜ Not Started | FR-6.1, FR-7.1 → FR-7.2 | Phase 3 |
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

### Remaining

- [x] EDA notebook (`notebooks/01_eda_ckd.ipynb`) — distributions, correlations, missing-value heatmap
- [x] Great Expectations data validation schema (`data/validation/ckd_suite.json` + `validate.py`, GX 1.x)
- [x] Additional test coverage (ingestion tests, `save_outputs()` integration test — 13/13 green)

---

## Phase 2: Model Training + Experiment Tracking

**Status**: ✅ Implementation Complete (plans 02-01 tracer + 02-02 expansion done 2026-09-21; 9 runs, winner mlp-relu v9 Staging)
**Delivers**: Trained models logged to MLflow, best model registered
**Patent impact**: Claim 2 completion (pipeline + model in same MLflow run)
**Depends on**: Phase 1 outputs (`data/processed/`, `preprocessing_pipeline.joblib`)

### Tasks

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

**Status**: ⬜ Not Started
**Delivers**: FastAPI service, Docker Compose stack, PostgreSQL prediction logging
**Patent impact**: Claim 4 (model version per prediction)
**Depends on**: Phase 2 (registered model in MLflow)

**Plans:** 4 plans
**Wave 1**

- [ ] 03-01-PLAN.md — Promotion v9 to Production plus deps plus config plus Wave 0 API stubs (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 03-02-PLAN.md — Tracer: schemas plus loader plus /predict plus /health plus /model_info pinned version live (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 03-03-PLAN.md — /batch_predict all-or-nothing plus full-record Postgres logging (wave 3)
- [ ] 03-04-PLAN.md — Dockerfile plus Compose stack plus Streamlit frontend (wave 3)

### Tasks

- [ ] Create `api/app.py` — FastAPI application
- [ ] Create `api/schemas.py` — Pydantic models with `model_version` field (**Claim 4**)
- [ ] Implement endpoints: `/predict`, `/batch_predict`, `/health`, `/model_info`
- [ ] Resolve production model version from MLflow Registry per request
- [ ] Create prediction logging to PostgreSQL
- [ ] Create `docker/Dockerfile` for FastAPI service
- [ ] Create `docker/docker-compose.yml` — FastAPI + MLflow + PostgreSQL
- [ ] Create `frontend/app.py` — Streamlit UI for predictions
- [ ] Write API tests

---

## Phase 4: CI/CD + Monitoring

**Status**: ⬜ Not Started
**Delivers**: GitHub Actions workflow, Prometheus metrics, Grafana dashboard
**Depends on**: Phase 3 (Docker image to build/push)

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
