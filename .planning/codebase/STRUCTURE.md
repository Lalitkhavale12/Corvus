# Project Structure — Corvus

> Last mapped: 2026-09-19

## Directory Tree

```
Corvus/
├── .gitignore                          (302 B)  Git ignore rules
├── CORVUS_FINAL_GUIDE.md               (11.9 KB) Master dev guide + patent tracker
├── README.md                           (2.0 KB)  Project overview + setup
├── dataset_analysis.md                 (5.0 KB)  Analysis of 11 uploaded dataset files
├── requirements.txt                    (733 B)   Python dependencies (all phases)
│
├── config/
│   └── config.yaml                     (758 B)   Pipeline configuration (paths, splits, strategies)
│
├── data/
│   ├── raw/                            (gitignored) Immutable source data
│   ├── processed/                      (gitignored) Pipeline outputs (CSVs + joblib)
│   └── validation/                     (empty)      Great Expectations (Phase 2)
│
├── src/
│   ├── __init__.py                     Package root
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── load_data.py                (3.3 KB)  Raw data loading + sanitization + summary
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   └── preprocess.py               (8.6 KB)  Leak-safe split + sklearn Pipeline + outputs
│   ├── feature_engineering/
│   │   └── __init__.py                 (placeholder)
│   ├── training/
│   │   └── __init__.py                 (placeholder)
│   ├── evaluation/
│   │   └── __init__.py                 (placeholder)
│   ├── prediction/
│   │   └── __init__.py                 (placeholder)
│   ├── monitoring/
│   │   └── __init__.py                 (placeholder)
│   ├── deployment/
│   │   └── __init__.py                 (placeholder)
│   └── utils/
│       ├── __init__.py
│       ├── config.py                   (770 B)   YAML loader + path resolver + LRU cache
│       └── logger.py                   (776 B)   Loguru setup (stderr + rotating file)
│
├── tests/
│   ├── __init__.py
│   └── test_preprocessing.py           (2.9 KB)  4 tests: clean, split disjointness, Pipeline type, no NaN
│
├── models/
│   └── .gitkeep                        (empty)    MLflow Registry artifacts (Phase 3)
│
├── mlruns/                             (gitignored) MLflow tracking data (Phase 2)
├── airflow/                            (empty)      DAGs for retraining (Phase 9)
├── docker/                             (empty)      Dockerfiles + compose (Phase 5)
├── api/                                (empty)      FastAPI service (Phase 4)
├── frontend/                           (empty)      Streamlit UI (Phase 4)
├── notebooks/                          (empty)      EDA notebooks (Phase 1 remaining)
├── logs/                               (gitignored) Loguru output (corvus.log)
├── reports/                            (gitignored) Data quality summaries
└── venv/                               (gitignored) Python virtual environment
```

## File Statistics

| Category | Files with Code | Total Lines | Total Bytes |
|---|---|---|---|
| Source (`src/`) | 3 active + 7 `__init__.py` stubs | ~362 | ~13.4 KB |
| Tests (`tests/`) | 1 | 72 | 2.9 KB |
| Config | 1 | 30 | 758 B |
| Documentation | 3 | ~332 | ~18.9 KB |
| **Total meaningful** | **8** | **~796** | **~36.0 KB** |

## Active vs. Placeholder Breakdown

### Active Code (Phase 1 — Built & Tested)

| File | Lines | Key Exports |
|---|---|---|
| `src/ingestion/load_data.py` | 93 | `load_raw_data()`, `summarize()`, `main()` |
| `src/preprocessing/preprocess.py` | 220 | `clean_raw()`, `split_raw()`, `build_pipeline()`, `fit_transform_split()`, `save_outputs()`, `main()` |
| `src/utils/config.py` | 21 | `load_config()`, `PROJECT_ROOT`, `CONFIG_PATH` |
| `src/utils/logger.py` | 28 | `get_logger()` |
| `tests/test_preprocessing.py` | 72 | 4 pytest test functions + 1 fixture |

### Placeholder Modules (Empty `__init__.py` Only)

- `src/feature_engineering/` → Phase 2
- `src/training/` → Phase 2
- `src/evaluation/` → Phase 2
- `src/prediction/` → Phase 4
- `src/monitoring/` → Phase 7–8 (to split into `metrics.py` + `drift.py`)
- `src/deployment/` → Phase 4–5

### Empty Directories (No Files Yet)

- `api/` → Phase 4 (FastAPI)
- `frontend/` → Phase 4 (Streamlit)
- `docker/` → Phase 5
- `airflow/` → Phase 9
- `notebooks/` → Phase 1 (EDA)

### Not Yet Created (Identified Gaps)

- `src/visualization/` → Component 102 (patent requirement, tracked in guide)
- `.github/workflows/` → Phase 6 (CI/CD)
- `api/schemas/` → Phase 4 (Claim 4)
