# Technology Stack — Corvus

> Last mapped: 2026-09-19

## Language & Runtime

| Item | Version Constraint | Notes |
|---|---|---|
| Python | 3.11+ (inferred from `list[str]` type hints in source) | venv-managed, no pyproject.toml — uses `requirements.txt` |

## Core Dependencies (Installed — Phase 1)

| Package | Version | Purpose | Used In |
|---|---|---|---|
| **pandas** | ≥ 2.0 | DataFrames for ingestion, cleaning, splitting, output CSVs | `load_data.py`, `preprocess.py`, tests |
| **numpy** | ≥ 1.24 | Numeric operations (transitive via pandas/sklearn) | Implicit |
| **scikit-learn** | ≥ 1.3 | `Pipeline`, `ColumnTransformer`, imputers, scalers, encoders, `train_test_split` | `preprocess.py` (core of Phase 1) |
| **joblib** | ≥ 1.3 | Serialize fitted `Pipeline` object to `.joblib` | `preprocess.py` (`save_outputs`) |
| **PyYAML** | ≥ 6.0 | Load `config/config.yaml` | `src/utils/config.py` |
| **loguru** | ≥ 0.7 | Structured logging to stderr + rotating file | `src/utils/logger.py` |
| **matplotlib** | ≥ 3.7 | EDA visualization (planned, not yet used in code) | — |
| **seaborn** | ≥ 0.12 | EDA visualization (planned, not yet used in code) | — |
| **pytest** | ≥ 8.0 | Test runner | `tests/` |

## Planned Dependencies (In requirements.txt, Not Yet Used in Code)

| Package | Version | Target Phase | Purpose |
|---|---|---|---|
| **xgboost** | ≥ 2.0 | Phase 2 | Gradient boosting model |
| **lightgbm** | ≥ 4.0 | Phase 2 | Gradient boosting model |
| **mlflow** | ≥ 2.10 | Phase 2–3 | Experiment tracking + model registry |
| **great-expectations** | ≥ 0.18 | Phase 1–2 | Data validation schemas |
| **fastapi** | ≥ 0.110 | Phase 4 | Prediction API |
| **uvicorn** | ≥ 0.27 | Phase 4 | ASGI server for FastAPI |
| **pydantic** | ≥ 2.6 | Phase 4 | Request/response validation |

## Commented-Out / Future Dependencies

| Package | Target Phase | Purpose |
|---|---|---|
| evidently | Phase 8 | Drift detection |
| apache-airflow | Phase 9 | Retraining orchestration |
| prometheus-client | Phase 7 | Metrics export |
| streamlit | Phase 4/9 | Simple frontend |

## Infrastructure

| Layer | Technology | Status |
|---|---|---|
| Containerization | Docker + Docker Compose | Phase 5 (scaffolded: `docker/` dir exists, empty) |
| Database | PostgreSQL | Phase 5 (prediction logging) |
| CI/CD | GitHub Actions | Phase 6 (not yet created) |
| Monitoring | Prometheus + Grafana | Phase 7 |
| Orchestration | Apache Airflow | Phase 9 |
| Heavy orchestration | ~~Kubernetes~~ | **Cut** — Docker Compose deemed sufficient |

## Build & Package Management

- **No `pyproject.toml`, `setup.py`, or `setup.cfg`** — the project is not packaged as a distributable library.
- **`requirements.txt`** is the sole dependency manifest.
- **Virtual environment**: `venv/` directory (gitignored).
- **No lockfile** (`requirements.txt` uses `>=` lower bounds, no pinned versions).

## Key Observations

1. **Python 3.11+ required** — source code uses `str | None` union syntax and `list[str]` generic hints (PEP 604/585), which require 3.10+. The `--cp311` wheels in install output confirm 3.11.
2. **No dependency locking** — reproducibility risk. Consider `pip freeze > requirements-lock.txt` or switching to `uv`/`pip-tools`.
3. **Installed but unused packages** — matplotlib, seaborn, xgboost, lightgbm, mlflow, great-expectations, fastapi, uvicorn, pydantic are all installed but have zero imports in current source. This is intentional (pre-installed for upcoming phases).
