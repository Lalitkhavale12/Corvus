# Corvus — Project Context

> Initialized: 2026-09-19
> Type: Academic (TY EDI — Third Year Engineering Design & Innovation)
> Developer: Solo

## Vision

An end-to-end MLOps pipeline for automated training, deployment, and monitoring of disease prediction models — **Chronic Kidney Disease (CKD)** as the pilot use case. Corvus is a **multi-user web platform** where patients and doctors can register, log in, and use ML models to check CKD risk. The platform demonstrates the complete machine learning lifecycle: data preparation → model training → experiment tracking → model selection → deployment → **authenticated prediction serving** → monitoring → automated retraining.

## Problem Statement

Machine learning models degrade over time as real-world data distributions shift. Most academic ML projects stop at model training and evaluation, ignoring the operational reality that deployed models need continuous monitoring, drift detection, retraining, **and secure, multi-user access**. Corvus addresses this gap by implementing a full MLOps pipeline with a web-based frontend that manages the complete lifecycle — from data preparation to authenticated, versioned prediction serving.

## Core Objectives

1. **Data Pipeline** — Ingest, validate, and preprocess clinical data with leak-safe splitting and a single serializable preprocessing artifact (Patent Claim 2)
2. **Model Training & Tracking** — Train multiple models (LR, RF, XGBoost, LightGBM, MLP), log experiments to MLflow, compare metrics (accuracy, precision, recall, F1, ROC-AUC)
3. **Model Registry & Deployment** — Register best model, serve predictions via API, track model version per prediction (Patent Claim 4)
4. **Web Platform & Authentication** — Multi-user website with email/password registration and login for patients and doctors; role-based access to predictions and history
5. **Monitoring & Drift Detection** — Monitor prediction performance, detect data drift, trigger alerts
6. **Automated Retraining** — Retrain when drift detected, evaluate challenger vs. champion, promote if better (Patent Claim 5)

## Domain Context

- **Dataset (v1 / v9 model)**: UCI CKD dataset (id 336) — 400 rows, 24 features, binary classification (ckd/notckd)
- **Dataset (v2 / v11 model)**: NHANES Native — 5,343 derived rows, 21 features (16 numeric + 5 categorical), binary classification
- **Drift simulation**: UCI CKD dataset (id 857) — 200 rows, independent Bangladeshi cohort
- **Clinical features**: Blood pressure, serum creatinine, hemoglobin, albumin, blood sugar, etc.
- **Challenge**: Small dataset (400 rows for v9), heavy missingness (up to 38% per column), mixed numeric/categorical types

## Patent Claims (Hard Requirements)

| Claim | Requirement | Impact |
|---|---|---|
| **Claim 2** | Fitted preprocessing pipeline stored as MLflow artifact in same run as model | Pipeline architecture + MLflow logging |
| **Claim 4** | Log deployed model version per prediction | API schema + prediction logging + user-linked history |
| **Claim 5** | 5 Airflow trigger types + champion/challenger promotion + archived retention | Airflow DAGs + MLflow Registry stages |
| **Component 102** | Standalone data visualization module | Separate `src/visualization/` module |
| **Claims 1, 3** | Full text not yet shared | Pending review |

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| API framework | FastAPI |
| API validation | Pydantic |
| HTTP server | Uvicorn |
| ORM + migrations | SQLAlchemy + Alembic |
| Password hashing | passlib[bcrypt] |
| JWT auth | python-jose + PyJWT |
| Models/scoring | scikit-learn |
| Experiment tracking | MLflow |
| Model registry | MLflow Registry |
| Database | PostgreSQL |
| DB driver | psycopg2-binary / SQLAlchemy |
| Logging | Loguru |
| Config | YAML (`config/config.yaml`) |
| Testing | pytest |

### Frontend (New Website)
| Layer | Technology |
|---|---|
| UI Framework | React 18 + Vite |
| Styling | Tailwind CSS |
| Routing | React Router DOM |
| HTTP Client | Axios |
| Forms | React Hook Form + Zod |
| Icons | Lucide React |
| State | React Context + useState |

### Infrastructure
| Layer | Technology |
|---|---|
| Containerization | Docker |
| Orchestration | Docker Compose |
| Services | FastAPI (api), React (frontend), MLflow, PostgreSQL |

## Constraints

- **Solo developer** — no code review from teammates, must self-validate
- **Tight timeline** — faster than the documented 4-6 weeks
- **Small dataset** — 400 rows limits model complexity and drift detection sensitivity
- **Patent compliance** — Claims 2, 4, 5 and Component 102 are hard requirements
- **Academic deliverable** — must be demonstrable and documentable
- **Local-first deployment** — Docker Compose on local machine; cloud later
- **Auth scope** — Email/password only for MVP; Google OAuth deferred
- **Doctor registration** — Self-registration, no admin approval gate for MVP

## Key Decisions Made

| Decision | Rationale |
|---|---|
| Kubernetes cut → Docker Compose | Demonstrates orchestration without weeks of learning curve |
| Streamlit → React + Vite | Multi-user website requires a proper frontend framework |
| 4-stage CI/CD → single GitHub Actions workflow | Still demonstrates CI/CD |
| UCI-857 as drift simulation source | Independent cohort, confirmed valid |
| Synthetic datasets rejected | Leaky labels, circular labeling, or rule-generated targets |
| Abu Dhabi EHR deferred | Survival analysis is a different modeling paradigm — stretch goal |
| Email/password only (no OAuth for MVP) | Simpler implementation; OAuth deferred to later |
| Doctor self-registration (no admin gate) | Faster onboarding; access control can be added later |
