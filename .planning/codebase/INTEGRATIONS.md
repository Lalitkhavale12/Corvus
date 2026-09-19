# Integrations — Corvus

> Last mapped: 2026-09-19

## Internal Module Integration Map

```
config/config.yaml
       │
       ▼
src/utils/config.py ──────────────────────────────────────┐
       │  load_config() — cached, resolves paths          │
       │  PROJECT_ROOT — used everywhere                  │
       ▼                                                  ▼
src/utils/logger.py                              src/ingestion/load_data.py
  get_logger() — loguru                            load_raw_data() → pd.DataFrame
  logs to stderr + logs/corvus.log                 summarize() → reports/data_quality_summary.csv
       │                                                  │
       │                                                  ▼
       │                                         src/preprocessing/preprocess.py
       │                                           clean_raw() → leak-safe cleaning
       │                                           split_raw() → train/val/test split
       │                                           build_pipeline() → unfitted sklearn Pipeline
       │                                           fit_transform_split() → fit on train only
       │                                           save_outputs() → CSVs + pipeline.joblib
       │                                                  │
       ▼                                                  ▼
  logs/corvus.log                                data/processed/
                                                   ├── train.csv
                                                   ├── val.csv
                                                   ├── test.csv
                                                   └── preprocessing_pipeline.joblib
```

## Data Flow (Phase 1 — Only Active Flow)

```
data/raw/kidney_disease.csv
    │
    ▼  python -m src.ingestion.load_data
    │  (load, sanitize "?" → NaN, strip whitespace, summarize)
    │
    ▼  reports/data_quality_summary.csv
    │
    ▼  python -m src.preprocessing.preprocess
    │  (clean_raw → split_raw → build_pipeline → fit_transform_split → save_outputs)
    │
    ▼  data/processed/{train,val,test}.csv + preprocessing_pipeline.joblib
```

## External Service Integrations (Planned, Not Yet Wired)

| Service | Integration Point | Phase | Notes |
|---|---|---|---|
| **MLflow** | `mlflow.tracking_uri` = `mlruns/` (config.yaml) | 2–3 | Local file-backed tracking server. Training code will log pipeline + model as artifacts in same run (Claim 2). |
| **PostgreSQL** | Not configured yet | 5 | Prediction logging with model_version per prediction (Claim 4). |
| **Prometheus** | Not configured yet | 7 | `src/monitoring/metrics.py` — latency, request count, error rate. |
| **Grafana** | Not configured yet | 7 | Dashboard consuming Prometheus metrics. |
| **Evidently AI** | Not configured yet | 8 | `src/monitoring/drift.py` — UCI-336 baseline vs. UCI-857 incoming batch. |
| **Apache Airflow** | Not configured yet | 9 | `airflow/dags/` — 5 trigger types + champion/challenger promotion (Claim 5). |
| **GitHub Actions** | No `.github/workflows/` yet | 6 | CI: test → build → push image. |

## Configuration Integration

All modules integrate through a single configuration chain:

1. **`config/config.yaml`** — YAML file, single source of truth
2. **`src/utils/config.py`** — `load_config()` with `@lru_cache(maxsize=1)` — loads once, resolves relative paths against `PROJECT_ROOT`
3. **Consumers** — `load_data.py`, `preprocess.py`, `logger.py` all call `load_config()` to get paths, column names, split ratios, preprocessing strategies

## Key Integration Patterns

1. **Module invocation**: Modules are run as `python -m src.<module>.<file>` — relies on `if __name__ == "__main__": main()` entry points.
2. **Cross-module imports**: `preprocess.py` imports `load_raw_data` from `ingestion.load_data` — modules are coupled through function-level imports, not class instances or DI.
3. **Artifact passing**: Phase 1 output (`preprocessing_pipeline.joblib`) is designed to be loaded by Phase 2 training code and logged to MLflow — file-system based handoff, no service bus.
4. **No API contracts yet**: `api/` and `frontend/` directories exist but are empty. FastAPI schemas (Claim 4) will be the first inter-service contract.
