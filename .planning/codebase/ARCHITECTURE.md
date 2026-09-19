# Architecture — Corvus

> Last mapped: 2026-09-19

## System Overview

Corvus is an **end-to-end MLOps platform** for automated training, deployment, and monitoring of disease prediction models. The pilot use case is **Chronic Kidney Disease (CKD)** classification using the UCI CKD dataset (400 rows, 24 features).

The architecture follows a **phased, config-driven pipeline pattern** — each phase produces a testable artifact before the next begins.

## Architectural Style

**Monolithic Python package with pipeline orchestration** — not microservices. All source code lives under `src/` as a flat package with submodules per concern. Modules are invoked as scripts (`python -m src.module.file`) rather than through a CLI framework or task runner.

Future phases add external services (MLflow, PostgreSQL, Prometheus, Airflow) but the core remains a single Python codebase.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    config/config.yaml                     │
│              (single source of truth for all paths,      │
│               splits, strategies, MLflow URI)            │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   src/utils/config.py     src/utils/logger.py
   (load_config + cache)   (loguru → stderr + file)
          │                       │
          └───────────┬───────────┘
                      │
    ┌─────────────────┼─────────────────────┐
    ▼                 ▼                     ▼
 PHASE 1           PHASE 2–3            PHASE 4+
 (Active)          (Next)               (Future)
    │                 │                     │
    ▼                 ▼                     ▼
┌─────────┐    ┌───────────┐    ┌─────────────────────┐
│Ingestion│    │ Training  │    │ FastAPI + Monitoring │
│  + Pre- │    │ + MLflow  │    │ + Airflow + Docker  │
│ process │    │ + Registry│    │                     │
└────┬────┘    └───────────┘    └─────────────────────┘
     │
     ▼
 data/processed/
 ├── train.csv
 ├── val.csv
 ├── test.csv
 └── preprocessing_pipeline.joblib
```

## Module Responsibilities

| Module | Responsibility | Status |
|---|---|---|
| `src/ingestion/` | Load raw CSV, sanitize UCI quirks ("?" → NaN, whitespace), produce quality summary | ✅ Built |
| `src/preprocessing/` | Leak-safe split → fit sklearn Pipeline on train only → transform all splits → save | ✅ Built |
| `src/utils/` | Config loading (YAML + path resolution + caching), centralized Loguru logger | ✅ Built |
| `src/feature_engineering/` | Feature creation/selection | ⬜ Placeholder (`__init__.py` only) |
| `src/training/` | Model training, MLflow logging, pipeline artifact co-logging (Claim 2) | ⬜ Placeholder |
| `src/evaluation/` | Metrics computation (accuracy, precision, recall, F1, ROC-AUC) | ⬜ Placeholder |
| `src/prediction/` | Inference with model version logging per prediction (Claim 4) | ⬜ Placeholder |
| `src/monitoring/` | To split into `metrics.py` (Prometheus) + `drift.py` (Evidently) | ⬜ Placeholder |
| `src/deployment/` | Deployment automation | ⬜ Placeholder |

## Data Architecture

```
data/
├── raw/              # Immutable source data (gitignored)
│   └── kidney_disease.csv (UCI-336, 400 rows)
├── processed/        # Pipeline outputs (gitignored)
│   ├── train.csv     # 70% stratified split
│   ├── val.csv       # 10% stratified split
│   ├── test.csv      # 20% stratified split
│   └── preprocessing_pipeline.joblib
└── validation/       # Great Expectations (Phase 2)
```

**Key design decisions:**
- Raw data is **never modified** — all transformations produce new files in `processed/`
- Split happens **before** any fitting — eliminates data leakage
- Preprocessing is a **single serializable sklearn Pipeline** — satisfies Patent Claim 2
- Train/val/test ratios configurable via `config.yaml` (`split.test_size`, `split.val_size`)

## Configuration Architecture

Single YAML file (`config/config.yaml`) with sections:
- `data` — paths, target column, positive label, id column
- `split` — test/val sizes, random state, stratification toggle
- `preprocessing` — imputation strategies, scaling toggle, encoding method
- `logging` — level, log directory
- `mlflow` — tracking URI, experiment name

Loaded once via `@lru_cache` in `config.py`, paths resolved relative to `PROJECT_ROOT` (2 levels up from `config.py`).

## Patent Claim Compliance (Architectural Impact)

| Claim | Architectural Requirement | Current State |
|---|---|---|
| **Claim 2** | Preprocessing pipeline as single MLflow artifact alongside model | Pipeline object ✅, MLflow logging deferred to Phase 2 |
| **Claim 4** | Model version tracked per prediction | Requires `model_version` in API schema + MLflow Registry lookup |
| **Claim 5** | 5 Airflow trigger types + champion/challenger promotion | Requires `airflow/dags/` + MLflow Registry stages |
| **Component 102** | Standalone data visualization module | Requires `src/visualization/` (not yet created) |
