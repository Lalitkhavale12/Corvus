# Corvus — Project Context

> Initialized: 2026-09-19
> Type: Academic (TY EDI — Third Year Engineering Design & Innovation)
> Developer: Solo

## Vision

An end-to-end MLOps pipeline for automated training, deployment, and monitoring of disease prediction models — **Chronic Kidney Disease (CKD)** as the pilot use case. The project demonstrates the complete machine learning lifecycle: data preparation → model training → experiment tracking → model selection → deployment → monitoring → automated retraining — in a structured and reproducible manner.

## Problem Statement

Machine learning models degrade over time as real-world data distributions shift. Most academic ML projects stop at model training and evaluation, ignoring the operational reality that deployed models need continuous monitoring, drift detection, and retraining. Corvus addresses this gap by implementing a full MLOps pipeline that manages the complete lifecycle.

## Core Objectives

1. **Data Pipeline** — Ingest, validate, and preprocess clinical data with leak-safe splitting and a single serializable preprocessing artifact (Patent Claim 2)
2. **Model Training & Tracking** — Train multiple models (LR, RF, XGBoost, LightGBM, MLP), log experiments to MLflow, compare metrics (accuracy, precision, recall, F1, ROC-AUC)
3. **Model Registry & Deployment** — Register best model, serve predictions via API, track model version per prediction (Patent Claim 4)
4. **Monitoring & Drift Detection** — Monitor prediction performance, detect data drift, trigger alerts
5. **Automated Retraining** — Retrain when drift detected, evaluate challenger vs. champion, promote if better (Patent Claim 5)

## Domain Context

- **Dataset**: UCI CKD dataset (id 336) — 400 rows, 24 features, binary classification (ckd/notckd)
- **Drift simulation**: UCI CKD dataset (id 857) — 200 rows, independent Bangladeshi cohort
- **Clinical features**: Blood pressure, serum creatinine, hemoglobin, albumin, blood sugar, etc.
- **Challenge**: Small dataset (400 rows), heavy missingness (up to 38% per column), mixed numeric/categorical types

## Patent Claims (Hard Requirements)

| Claim | Requirement | Impact |
|---|---|---|
| **Claim 2** | Fitted preprocessing pipeline stored as MLflow artifact in same run as model | Pipeline architecture + MLflow logging |
| **Claim 4** | Log deployed model version per prediction | API schema + prediction logging |
| **Claim 5** | 5 Airflow trigger types + champion/challenger promotion + archived retention | Airflow DAGs + MLflow Registry stages |
| **Component 102** | Standalone data visualization module | Separate `src/visualization/` module |
| **Claims 1, 3** | Full text not yet shared | Pending review |

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Data processing | Pandas, NumPy |
| Preprocessing | scikit-learn Pipeline + ColumnTransformer |
| Models | Logistic Regression, Random Forest, XGBoost, LightGBM, MLP |
| Experiment tracking | MLflow |
| Model registry | MLflow Registry |
| API | FastAPI |
| Frontend | Streamlit |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |
| Drift detection | Evidently AI |
| Retraining | Apache Airflow |
| Database | PostgreSQL |
| Logging | Loguru |
| Testing | pytest |

## Constraints

- **Solo developer** — no code review from teammates, must self-validate
- **Tight timeline** — faster than the documented 4-6 weeks
- **Small dataset** — 400 rows limits model complexity and drift detection sensitivity
- **Patent compliance** — Claims 2, 4, 5 and Component 102 are hard requirements
- **Academic deliverable** — must be demonstrable and documentable

## Key Decisions Made

| Decision | Rationale |
|---|---|
| Kubernetes cut → Docker Compose | Demonstrates orchestration without weeks of learning curve |
| React → Streamlit | Single Python file vs. separate frontend build |
| 4-stage CI/CD → single GitHub Actions workflow | Still demonstrates CI/CD |
| UCI-857 as drift simulation source | Independent cohort, confirmed valid |
| Synthetic datasets rejected | Leaky labels, circular labeling, or rule-generated targets |
| Abu Dhabi EHR deferred | Survival analysis is a different modeling paradigm — stretch goal |
