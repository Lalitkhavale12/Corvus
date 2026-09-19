# Roadmap — Corvus MLOps Pipeline

> Milestone: M1 (Initial Build)
> Status: Active
> Last updated: 2026-09-19

## Phase Overview

| Phase | Name | Status | Requirements | Dependencies |
|---|---|---|---|---|
| **1** | Data Pipeline | 🔄 In Progress | FR-1.1 → FR-1.7 | None |
| **2** | Model Training + Experiment Tracking | ⬜ Not Started | FR-2.1 → FR-2.5, FR-3.1 → FR-3.3 | Phase 1 |
| **3** | Prediction API + Containerization | ⬜ Not Started | FR-4.1 → FR-4.4, FR-5.1 → FR-5.2 | Phase 2 |
| **4** | CI/CD + Monitoring | ⬜ Not Started | FR-6.1, FR-7.1 → FR-7.2 | Phase 3 |
| **5** | Drift Detection + Auto-Retraining | ⬜ Not Started | FR-8.1 → FR-8.3, FR-9.1 → FR-9.4 | Phase 4 |
| **6** | Visualization + Polish | ⬜ Not Started | FR-10.1 → FR-10.2, NFR-1 → NFR-5 | Phase 1 (can parallel) |

---

## Phase 1: Data Pipeline

**Status**: 🔄 In Progress (core built, EDA + Great Expectations remaining)
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
- [ ] EDA notebook (`notebooks/`) — distributions, correlations, missing-value heatmap
- [ ] Great Expectations data validation schema (`data/validation/`)
- [ ] Additional test coverage (ingestion tests, `save_outputs()` integration test)

---

## Phase 2: Model Training + Experiment Tracking

**Status**: ⬜ Not Started
**Delivers**: Trained models logged to MLflow, best model registered
**Patent impact**: Claim 2 completion (pipeline + model in same MLflow run)
**Depends on**: Phase 1 outputs (`data/processed/`, `preprocessing_pipeline.joblib`)

### Tasks
- [ ] Create `src/training/train.py` — train LR, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM
- [ ] Create `src/training/train_mlp.py` — MLP with Sigmoid, Tanh, ReLU as separate runs
- [ ] Create `src/evaluation/evaluate.py` — accuracy, precision, recall, F1, ROC-AUC per model
- [ ] Configure MLflow tracking (`mlflow.tracking_uri` from config)
- [ ] Log `preprocessing_pipeline.joblib` + model as artifacts in same MLflow run (**Claim 2**)
- [ ] Compare all models, select best by ROC-AUC
- [ ] Register best model to MLflow Model Registry (Staging → Production)
- [ ] Create `src/feature_engineering/features.py` if feature selection adds value
- [ ] Write tests for training and evaluation

---

## Phase 3: Prediction API + Containerization

**Status**: ⬜ Not Started
**Delivers**: FastAPI service, Docker Compose stack, PostgreSQL prediction logging
**Patent impact**: Claim 4 (model version per prediction)
**Depends on**: Phase 2 (registered model in MLflow)

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
