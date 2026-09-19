# Requirements — Corvus MLOps Pipeline

> Milestone: M1 (Initial Build)
> Status: Active
> Last updated: 2026-09-19

## Functional Requirements

### FR-1: Data Pipeline
- **FR-1.1**: Ingest raw CSV data with automatic handling of UCI CKD quirks ("?" markers, whitespace, dtype coercion)
- **FR-1.2**: Produce per-column data quality summary (dtype, missing count, missing %, unique values)
- **FR-1.3**: Clean target labels, drop rows with no label, drop ID column
- **FR-1.4**: Split data into train/val/test (70/10/20) **before** any fitting (leak-safe)
- **FR-1.5**: Build a single `sklearn.Pipeline` (imputer + scaler + encoder) fitted on training data only
- **FR-1.6**: Save pipeline artifact as `.joblib` and transformed splits as CSV
- **FR-1.7**: All paths, split ratios, strategies configurable via `config/config.yaml`

### FR-2: Model Training & Experiment Tracking
- **FR-2.1**: Train at minimum: Logistic Regression, Random Forest, XGBoost, LightGBM, MLP (with Sigmoid/Tanh/ReLU activations as separate runs)
- **FR-2.2**: Log metrics per run: accuracy, precision, recall, F1-score, ROC-AUC
- **FR-2.3**: Log `preprocessing_pipeline.joblib` + model as artifacts in the **same MLflow run** (Claim 2)
- **FR-2.4**: Compare all models; identify best by ROC-AUC
- **FR-2.5**: Register best model to MLflow Model Registry

### FR-3: Model Registry & Versioning
- **FR-3.1**: MLflow Registry with Staging / Production / Archived stages
- **FR-3.2**: Version tracking for all registered models
- **FR-3.3**: Ability to promote/demote models between stages

### FR-4: Prediction API
- **FR-4.1**: FastAPI endpoints: `/predict`, `/batch_predict`, `/health`, `/model_info`
- **FR-4.2**: Request/response validation via Pydantic schemas
- **FR-4.3**: Log `model_version` per prediction (Claim 4)
- **FR-4.4**: Resolve current production model version from MLflow Registry per request

### FR-5: Containerization
- **FR-5.1**: Dockerize FastAPI + MLflow + PostgreSQL via Docker Compose
- **FR-5.2**: Prediction logging to PostgreSQL including model version

### FR-6: CI/CD
- **FR-6.1**: GitHub Actions workflow: test → build → push image

### FR-7: Monitoring
- **FR-7.1**: Prometheus metrics: latency, request count, error rate
- **FR-7.2**: Grafana dashboard consuming Prometheus metrics

### FR-8: Drift Detection
- **FR-8.1**: Evidently AI drift report
- **FR-8.2**: UCI-336 baseline vs. UCI-857 as simulated incoming batch
- **FR-8.3**: Alert when drift exceeds threshold

### FR-9: Automated Retraining
- **FR-9.1**: 5 Airflow trigger types (Claim 5)
- **FR-9.2**: Conditional retrain → re-register → redeploy
- **FR-9.3**: Champion/challenger promotion logic
- **FR-9.4**: Archived model retention via MLflow Registry stages

### FR-10: Data Visualization
- **FR-10.1**: Standalone visualization module (Component 102)
- **FR-10.2**: Separate from EDA notebooks — a shippable component

## Non-Functional Requirements

### NFR-1: Reproducibility
- All experiments reproducible via `random_state` seeding
- Config-driven: changing dataset/parameters requires only config changes
- Fitted pipeline artifact enables identical preprocessing at inference time

### NFR-2: Patent Compliance
- Claim 2, 4, 5 and Component 102 must be demonstrably satisfied
- Architecture decisions traceable to specific claims

### NFR-3: Testability
- Each phase produces testable artifacts
- pytest-based test suite with synthetic data (no real dataset dependency)
- Tests written alongside each phase

### NFR-4: Modularity
- Each `src/` submodule has a single responsibility
- Cross-module coupling minimized (config-driven, function-level imports)
- New datasets require changes only to column lists and config

### NFR-5: Observability
- Loguru logging to stderr + rotating file
- Prometheus metrics for API
- MLflow for experiment tracking

## Acceptance Criteria

| Requirement | Acceptance Test |
|---|---|
| FR-1.4 (leak-safe split) | Train/val/test indices are mutually disjoint |
| FR-1.5 (single pipeline) | Output is an `sklearn.Pipeline` instance; `.transform()` works |
| FR-2.3 (Claim 2) | MLflow run has both pipeline and model as logged artifacts |
| FR-4.3 (Claim 4) | Each prediction response includes `model_version` field |
| FR-9.1 (Claim 5) | 5 distinct DAG trigger types exist and fire |
| FR-10.1 (Component 102) | `src/visualization/` module produces plots independent of notebooks |
