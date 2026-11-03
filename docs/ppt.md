# CORVUS — Technical Project Dossier (for PPT generation)

> Source material for a 12–14 slide engineering evaluation presentation.
> Fact-checked against code, data, configs, tests, and the live MLflow store on 2026-09-23.
> Statuses: COMPLETED / IMPLEMENTED-UAT-PENDING / PARTIALLY-IMPLEMENTED / PLANNED / NOT-STARTED / FUTURE-STRETCH.
> Anything unverifiable is marked NOT AVAILABLE IN CONTEXT — never invented.

---

## SECTION 1 — PROJECT IDENTITY

- **Project name:** Corvus
- **Full title:** Corvus — end-to-end MLOps platform for automated training, deployment, and monitoring of disease prediction models, Chronic Kidney Disease (CKD) as pilot use case.
- **Short description:** Config-driven ML lifecycle (ingest → validate → preprocess → train → track → register → serve → log) built around the UCI CKD dataset.
- **Elevator pitch:** Most student ML stops at a notebook; Corvus carries a disease-prediction model from raw clinical CSV to a versioned, containerized prediction service with full experiment traceability.
- **Problem:** Deployed ML models degrade as data drifts, yet academic projects stop at training and ignore monitoring, versioning, and retraining.
- **Main objective:** Demonstrate the complete ML lifecycle with reproducible, testable artifacts at every stage.
- **Research/engineering question:** NOT AVAILABLE IN CONTEXT (no formal RQ documented; engineering question in practice: how to run a small-data clinical classifier through a production-grade MLOps loop).
- **Target users / intended use:** Academic evaluation (TY EDI engineering project); intended as a demonstrable platform, not a clinical tool.
- **Project category:** Academic MLOps engineering project.
- **Main technologies:** Python 3.11, pandas, scikit-learn, XGBoost, LightGBM, MLflow (tracking + Registry), FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL 16, Streamlit, Docker + Docker Compose, Great Expectations 1.x, Loguru, pytest.
- **Why more than a notebook:** Leak-safe split-before-fit pipeline as a serialized artifact; validation gates that fail closed; 9 tracked experiments with co-logged pipeline+model; versioned registry with human promotion gates; served API with per-prediction version logging; containerized stack; 45-test suite; row-level data lineage.
- **Core engineering value:** Every claim is executable and verified — nothing is asserted without a test, a run, or a log.

### Explain CORVUS in 30 seconds
Corvus takes 400 rows of real kidney-disease data through validation, leak-safe preprocessing, nine tracked ML experiments, and a model registry — then serves the winner as a versioned web API in Docker, logging every prediction. MLOps, end to end, on a real clinical dataset.

### Explain CORVUS in 1 minute
Machine-learning models rot as data drifts, but coursework usually stops at training. Corvus implements the full lifecycle for Chronic Kidney Disease prediction: Great-Expectations-validated ingestion, a split-before-fit sklearn pipeline saved as one artifact, nine MLflow-tracked model configs with the pipeline co-logged beside each model, strict ROC-AUC selection into a Staging→Production registry, a FastAPI service that stamps every answer with its model version into PostgreSQL, all composed in Docker with a Streamlit UI — covered by 45 passing tests.

### Explain CORVUS technically to an examiner
Single Python package (`src/`), config-driven from `config/config.yaml`. Phase 1: quirk-normalizing ingestion, GX gate (fail-closed), stratified 279/40/81 split before any fitting, one fitted `ColumnTransformer` Pipeline (median/mode imputation, StandardScaler, OneHotEncoder with `handle_unknown="ignore"`), 24 output features, joblib artifact plus raw/transformed CSVs with lineage columns. Phase 2: nine seeded configs (six classical + three single-layer MLPs) trained from raw splits through train-only pipeline re-fits, five test metrics each in MLflow experiment `corvus-ckd`, strict-max ROC-AUC winner (`mlp-relu`) versioned v1–v9 with Staging/Archived lifecycle. Phase 3: FastAPI (startup-pinned v9 since promoted to Production), Pydantic-strict 24-field schemas, all-or-nothing CSV batches, full-record Postgres logging, health-gated Compose (API + MLflow + Postgres 16), thin Streamlit frontend. Verification: 45/45 pytest, 14/14 + 6/6 + 14/14 plan must-haves, code review with zero criticals, MLflow UI + container smoke proven live.

---

## SECTION 2 — PROJECT MOTIVATION

- **Why CKD:** Real, small, messy clinical data (400 rows, heavy missingness, mixed types) — forces honest handling of missingness, leakage, and small-n evaluation instead of toy-clean accuracy.
- **Notebook-only limits:** No validation (bad drops silently pass), leakage-prone preprocessing (fit-before-split), untracked hyperparameters, unversioned models, no serving story, no prediction audit trail.
- **Corvus answers:** GX validation gates; split-before-fit single Pipeline artifact; MLflow params/metrics/artifacts per run; Registry versions + stages + human promotion; FastAPI with per-prediction `model_version`; Postgres prediction log as future drift fuel.
- **MLOps relevance:** Demonstrates the operational half academia skips: reproducibility (seeds + config + artifacts), traceability (lineage columns, run-linked registry versions), deployment (containers), and the monitoring/retraining on-ramp (logged predictions feed Phases 4–5).

## PROBLEM → GAP → CORVUS SOLUTION
- **PROBLEM:** Clinical ML degrades as data drifts; models need monitoring and retraining, not just training.
- **GAP:** Coursework stops at `model.fit()` — no validation, versioning, serving, logging, or lifecycle.
- **SOLUTION:** Corvus — a six-phase MLOps platform (3 of 6 phases built) carrying CKD prediction from raw CSV to a versioned containerized service, every step tested and tracked. Do NOT claim clinical impact: no clinical validation exists (see Section 26).

---

## SECTION 3 — COMPLETE PROJECT SCOPE

### A. COMPLETED
| Feature | What it does | Why it exists | Technology | Status | Evidence |
|---|---|---|---|---|---|
| Quirk-tolerant ingestion | Loads UCI CSV, normalizes `?`/whitespace/dtypes, writes quality summary | Real clinical files are dirty | pandas, `src/ingestion/load_data.py` | COMPLETED | `reports/data_quality_summary.csv`, 4 ingestion tests |
| GX validation gate | 9-expectation suite + row bounds + duplicate check, fail-closed | Stop bad drops before they poison training | Great Expectations 1.x, `src/validation/validate.py` | COMPLETED | `data/validation/ckd_suite.json`, 6 validation tests, `RAW VALIDATION PASSED` |
| Leak-safe split + Pipeline | 279/40/81 stratified split first; one fitted Pipeline artifact | Close train-test leakage; Claim 2 object | sklearn `train_test_split`, `Pipeline`, `ColumnTransformer` | COMPLETED | `preprocessing_pipeline.joblib`, disjointness + imputer-median tests |
| 9-config training | 6 classical + 3 MLP configs, seeded, from raw splits | Fair comparison; pick winner on evidence | sklearn/XGBoost/LightGBM/MLP | COMPLETED | 9 MLflow runs, `src/training/` |
| MLflow tracking + Registry | Params/metrics/artifacts per run; v1–v9; Staging→Production→Archived | Reproducibility + Claim 2 + lifecycle | MLflow 3.16.1 file store | COMPLETED | Live store: 9 runs, v9 Production |
| Versioned API | 4 endpoints, pinned v9, `model_version` per response, strict 422s | Serve the model; Claim 4 | FastAPI, Pydantic v2 | COMPLETED | `api/`, 19 API tests, live 200s |
| Postgres prediction log | Full record per prediction incl. version + timestamp | Audit trail; drift fuel | SQLAlchemy, Postgres 16 | COMPLETED | `predictions` table row observed live |
| Container stack | Health-gated Compose: API + MLflow + Postgres | One-command deployment | Docker 29.x, Compose v5.3.1 | COMPLETED | Live smoke: build→up→predict→row→down clean |
| Streamlit UI | Form + CSV upload over the API | Human-usable demo surface | Streamlit | COMPLETED (code) | `frontend/app.py` |
| Test suite | 45 tests, synthetic fixtures, tmp isolation | Prove every claim | pytest 8.x | COMPLETED | 45/45 green |

### B. IMPLEMENTED / UAT PENDING
| Feature | Status | Evidence |
|---|---|---|
| Streamlit browser check (form + CSV + 422s) | IMPLEMENTED / UAT PENDING | `03-UAT.md` test 2 pending; code complete |
| Phase 2 MLflow-UI eyeball check (9 runs + artifacts) | IMPLEMENTED / UAT PENDING | `02-UAT.md` test 1 unconfirmed; store verified programmatically instead |

### C. PARTIALLY IMPLEMENTED
(none — phases are tracer-complete by design; no half-features remain)

### D. PLANNED / NOT STARTED
CI/CD (GitHub Actions), Prometheus + Grafana monitoring, Evidently drift (UCI-336 vs UCI-857), Airflow retraining + champion/challenger (Claim 5), `src/visualization/` (Component 102).

### E. FUTURE / STRETCH
Image-based CNN classifier (needs dataset re-selection; ultrasound/histology candidates rejected as unfit); Abu Dhabi EHR survival analysis (different paradigm — Cox/time-to-event).

---

## SECTION 4 — DATASETS

### Primary dataset (VERIFIED from `data/raw/kidney_disease.csv` on 2026-09-23)
- **Name/source:** UCI Chronic Kidney Disease, identifier **UCI-336** (`kidney_disease.csv`)
- **Rows:** 400 × **26 columns** (24 features + `classification` + `id`)
- **Classes:** 250 ckd / 150 notckd (two rows carry a stray `ckd\t` label, normalized at ingest)
- **Features:** 14 numeric (age, bp, sg, al, su, bgr, bu, sc, sod, pot, hemo, pcv, wc, rc) + 10 categorical (rbc, pc, pcc, ba, htn, dm, cad, appet, pe, ane)
- **Target:** `classification` → binary-encoded (ckd=1) at clean time
- **Missingness:** worst column 38% missing post-normalization; `?` markers + empty fields both present
- **Provenance:** named nephrologist/hospital/institution per UCI documentation (ESTABLISHED IN DISCUSSION; exact names NOT AVAILABLE IN CONTEXT)
- **Why selected:** only candidate with documented real-world provenance and no leakage/circularity defects.

### Alternatives (from `dataset_analysis.md`, ESTABLISHED IN DISCUSSION)
| Dataset | Type | Size | Real/Synthetic | Purpose | Problem/Concern | Decision | Status |
|---|---|---|---|---|---|---|---|
| UCI-336 (`kidney_disease.csv`) | Tabular clinical | 400 rows | Real | Primary training | Small n; heavy missingness | Selected | In use |
| UCI-857 (`ckd-dataset-v2.csv`) | Tabular clinical | 200 rows | Real (Bangladeshi cohort) | Forensically disqualified 2026-10-10: numerics pre-binned into ranges; all ten 0/1 indicators perfectly label-separated (P(ckd\|1)=1.0 — target-derived, not measured); no clean external-validation mapping exists | REJECTED for training AND validation | NOT USED |
| Abu Dhabi EHR | Survival/time-to-event | 491 patients | Real | Considered | `EventCKD35`+`TimeToEventMonths` needs Cox paradigm, not classification | Deferred stretch | FUTURE |
| 200K risk-progression CSV | Tabular, 82 cols | 200,000 rows | Synthetic | Considered | Label rule-generated from eGFR threshold (85.3 vs 50.0 split at 60.0) — leaky | Rejected | NOT USED |
| 20K severity CSV | Tabular, 43 cols | 20,000 rows | Synthetic | Considered | Zero missingness across rare labs; suspiciously exact class splits | Rejected | NOT USED |
| `updated_ckd_dataset_with_stages.csv` | 4,000 rows | Mixed derived | `ckd_pred` = another model's predictions (circular), `cluster` = clustering output | Rejected | NOT USED |
| Kaggle "KDIGO 2026" (`CKD_Dataset_Enhanced.csv` + `raw_CKD_dataset.csv`) | 25,800 rows, 67/36 cols | Generated (zero nulls in 67 clinical cols) | Forensically vetted 2026-09-23: Target deterministic in (GFR_Category × Albuminuria_Category) — 7 combos, 0 mixed; card stats contradicted file (claimed balanced 17–22%, actual 75% Healthy); both files shared identical targets | Rejected, files deleted from `data/raw/` | NOT USED |
| ARFF mirrors / `kidney_disease_test.csv` / `CKD_Preprocessed.csv` | Same 400 rows | Real | Redundant (subset, pre-cleaned) | Rejected as inputs | NOT USED |

## DATASET DECISION TABLE
Primary UCI-336 (real, provenanced) → big-cohort NHANES derivation SELECTED 2026-10-10 (5,343 adults, 17.3% positive, quarantine-held, audit-passed) → everything synthetic or circular rejected for demonstrable validity defects, not taste.

---

## SECTION 5 — DATA PIPELINE

RAW DATA (`data/raw/kidney_disease.csv`, immutable, never modified)
↓ INGESTION (`load_raw_data`: `?`→NA regex, strip whitespace/tabs on cells + columns, `pd.to_numeric` coercion downstream)
↓ CLEANING (`clean_raw`: drop `id` from features but carry as lineage, normalize target text, drop unlabeled rows, binary-encode via `positive_label`, warn-and-drop unclassified columns)
↓ VALIDATION (GX suite: column-set match, label domain, target not-null, row count 300–500, 5 non-null-proportion floors; plus config row bounds + exact-duplicate check; fail-closed `success=False`, pipeline aborts)
↓ SPLITTING (`split_raw`: id+target excluded from X, single stratified split — see Section 6)
↓ PREPROCESSING (Pipeline fit on train only; transform all; `_to_dataframe` with fallback warning)
↓ TRANSFORMED DATA (`train/val/test.csv` = 24 features + target + lineage; `*_raw.csv` = cleaned-untransformed + target + lineage; `preprocessing_pipeline.joblib`)
↓ MODEL TRAINING (Phase 2 reads `*_raw.csv` only — never transformed CSVs)

Per-step WHAT→WHY→TECH→STATUS: ingestion (sanitize dirty clinical CSVs → pandas → COMPLETED); validation (stop bad drops early → GX → COMPLETED); lineage (`__source_row` index + `__source_id` id value on every output row → clinical traceability → COMPLETED); persisted outputs (CSVs + joblib → audit + training inputs → COMPLETED).

---

## SECTION 6 — DATA SPLITTING & LEAKAGE PREVENTION

- **Sizes (VERIFIED):** train 279 / val 40 / test 81 (= 400; no rows lost — all labels present)
- **Stratification (VERIFIED):** ≈62.5% positive in all three splits (train 174/105, val 25/15, test 51/30)
- **Order:** split raw cleaned frame FIRST; pipeline `.fit()` sees `X_train` only (code comment marks the fix line); val/test only ever `.transform()`ed.
- **Proof:** index-disjointness test + imputer-`statistics_` == train-medians-exactly test (both green).

> **Split before fit.** Fitting imputers/scalers/encoders on the full dataset lets test-set statistics (means, medians, category vocabularies) leak into training-time preprocessing, inflating scores. The original code did this; review caught it; the fix (split first, fit train-only) is asserted by tests, not just documented.

---

## SECTION 7 — PREPROCESSING

- **Numeric (14):** `SimpleImputer(median)` → `StandardScaler` (median chosen for skewed labs; scaler required by LR/MLP).
- **Categorical (10):** `SimpleImputer(most_frequent)` → `OneHotEncoder(handle_unknown="ignore", drop="first")` (drop-first favors linear models; recorded trade-off for tree reads).
- **Structure:** `ColumnTransformer` inside one `Pipeline` → single `.joblib` artifact.
- **Output (VERIFIED):** 24 transformed features, 0 nulls; feature names logged (`num__*`, `cat__*`).
- **Inference reuse:** API loads the winner run's co-logged pipeline; startup probe asserts pipeline width == estimator `n_features_in_`, raising loudly on skew.

## Claim 2
“Fitted preprocessing pipeline stored as an MLflow artifact in the same run as the model.” COMPLETED: every one of the 9 runs logs `preprocessing/preprocessing_pipeline.joblib` + cloudpickle model in a single run; the serving loader downloads the pipeline from the winner's `run_id`. Together-at-train, together-at-serve: reproducibility, consistency, no leakage, no skew.

---

## SECTION 8 — FEATURES

| Feature | Type | Meaning | Preprocessing | Status |
|---|---|---|---|---|
| age, bp, sg, al, su, bgr, bu, sc, sod, pot, hemo, pcv, wc, rc | numeric | Clinical labs/vitals (exact medical semantics NOT AVAILABLE IN CONTEXT — use field names only) | median-impute + scale | In use |
| rbc, pc, pcc, ba, htn, dm, cad, appet, pe, ane | categorical | Clinical indicators (vocabularies in `api/schemas.py` Literals, verified exhaustive over raw) | mode-impute + one-hot | In use |
| classification | target | ckd/notckd → 1/0 | binary encode | In use |
| id | identifier | row id | dropped from features, kept as `__source_id` lineage | Lineage only |

Raw 24 → final 24 transformed (14 scaled + 10 one-hot-minus-first-level = VERIFIED 24 columns). Leakage-excluded: target, `id`, lineage columns (dropped via imported constants in train.py, API, and batch path).

---

## SECTION 9 — MACHINE LEARNING MODELS

All 9 trained from `*_raw.csv` through train-only pipeline re-fits, library defaults + `random_state=42`, no grid search (documented: grids fit noise at n=279). Metrics are test-split, ROC-AUC from probabilities.

| # | Model | Config (VERIFIED from code + store) | Why included | Test ROC-AUC | Status |
|---|---|---|---|---|---|
| 1 | Logistic Regression | `LogisticRegression(random_state=42)` | Linear baseline | 1.000 (acc 0.988) | Trained |
| 2 | Decision Tree | `DecisionTreeClassifier(random_state=42)` | Split-quality baseline | 0.980 (acc 0.975) | Trained |
| 3 | Random Forest | `RandomForestClassifier(random_state=42)` | Bagging vs single tree | 1.000 (acc 1.000) | Trained |
| 4 | Gradient Boosting | `GradientBoostingClassifier(random_state=42)` | Boosting foil to bagging | 1.000 | Trained |
| 5 | XGBoost | `XGBClassifier(random_state=42)` | Sparsity-aware splits for gappy columns | 1.000 | Trained |
| 6 | LightGBM | `LGBMClassifier(random_state=42, verbosity=-1)` | Second boosting family | 1.000 | Trained |
| 7 | MLP-ReLU | `MLPClassifier((50,), relu, max_iter=500, seed 42)` | Nonlinear DL probe | 1.000 (acc 1.000) | Trained — WINNER |
| 8 | MLP-Tanh | as above, tanh | Activation comparison | 1.000 (acc 1.000) | Trained |
| 9 | MLP-Sigmoid | as above, `logistic` | Activation comparison | 1.000 (acc 0.988) | Trained |

Nine configurations confirmed (code `ESTIMATORS` + `ACTIVATIONS` + 9 MLflow runs). Multiple models evaluated because winner must be chosen on evidence, and the comparison itself is the academic deliverable.

---

## SECTION 10 — EXPERIMENTATION

- **Experiment:** `corvus-ckd` (VERIFIED live). **Runs:** 9. **Seeds:** 42 family throughout. **Metrics/run:** accuracy, precision, recall, F1, ROC-AUC. **Methodology:** single stratified test split (81 rows); metrics computed on it; winner = strict max ROC-AUC, no tie-break (locked D-03).

| Model / Config | ROC-AUC | Other Metrics | Status |
|---|---|---|---|
| mlp-relu | 1.000 | acc 1.000, prec/rec/F1 1.000 | Winner (v9) |
| mlp-tanh | 1.000 | acc 1.000 all | Trained |
| lightgbm | 1.000 | acc 1.000 all | Trained |
| xgboost | 1.000 | acc 1.000 all | Trained |
| gradient-boosting | 1.000 | acc 1.000 all | Trained |
| random-forest | 1.000 | acc 1.000 all | Trained |
| logistic-regression | 1.000 | acc 0.988, rec 0.980, F1 0.990 | Trained |
| mlp-sigmoid | 1.000 | acc 0.988, rec 0.980, F1 0.990 | Trained |
| decision-tree | 0.980 | acc 0.975, rec 0.961, F1 0.980 | Trained |

### Winning model: MLP-ReLU — version 9 — criterion: strict-max test ROC-AUC.
Candid note (VERIFIED numbers): 7 configs tie at 1.0; ReLU wins by run order, not separation — the 81-row test set cannot distinguish the top models. Tree ensembles are effective co-champions; all versions persist so the champion can change with drift evidence.

---

## SECTION 11 — MLFLOW

- **Why MLflow:** params+metrics+artifacts+registry in one system; `models:/name/version` URIs let serving resolve models without file paths.
- **Experiment `corvus-ckd`:** 9 runs; ~60 params/run; 5 metrics/run; artifacts per run: `preprocessing/` pipeline + `model/` (cloudpickle-pinned; 3.x skops default explicitly overridden).
- **Registry `corvus-ckd` (VERIFIED live 2026-09-23):** v1–v8 Archived, v9 Production (promoted as Phase 3's first act; was Staging after Phase 2).
- **Backend:** file store `mlruns/` + `MLFLOW_ALLOW_FILE_STORE=true` (3.x maintenance gate); container uses a URI-rebased synced copy (`docker/sync_mlruns_container.py`, 48 files); SQLite/Postgres migration deferred to Phase 5.

## CLAIM 2 — VERIFIED LIVE
TRAINING → MLFLOW RUN (params + 5 metrics + pipeline + model) → REGISTRY (v1–v9) → STAGING (v9, Phase 2) → PRODUCTION (v9, Phase 3). Every run independently satisfies “pipeline and model in the same run.”

---

## SECTION 12 — MODEL SELECTION & LIFECYCLE

- **Candidates:** 9 configs. **Winner:** mlp-relu. **Version:** 9 (`run_id 10ac3e5e`, VERIFIED from store). **Criterion:** automated strict-max ROC-AUC (`evaluate.py:select_winner` = `max` by `roc_auc`, no tie-break — `src/evaluation/evaluate.py:49-51`).
- **Lifecycle (VERIFIED live):** every run registered a version (D-06/D-07); winner → Staging (Phase 2 `evaluate.py:apply_registry_stages`), superseded → Archived; v9 Staging → Production by explicit human-promoted script (`scripts/promote_production.py`, Phase 3 first act). Production was empty until that promotion — never auto-deployed.
- **AUTOMATED SELECTION vs HUMAN PROMOTION:** selection (max ROC-AUC) is code; Staging→Production is a human decision executed via script. Do NOT imply automatic production deployment.

---

## SECTION 13 — FASTAPI

Service: `Corvus CKD Prediction API` (`api/app.py`, VERIFIED by read). Lifespan pins version once from config/env, loads estimator + co-logged pipeline, asserts pipeline width == `n_features_in_`, binds Postgres session.

| Method | Route | Input | Output | Purpose | Validation | Error Behavior | Status |
|---|---|---|---|---|---|---|---|
| POST | `/predict` | `CKDRequest` (24 fields, JSON) | `PredictionResponse` | Single prediction | Pydantic, 422 | 503 no-DB; 500 no-traceback | Live 200 v9 |
| POST | `/batch_predict` | CSV upload (`UploadFile`) | `BatchPredictionResponse` | Batch scoring | All rows validate first; 422 with 1-indexed row number | 413 over 5 MB / 10k rows; 422 bad CSV | Live, tested |
| GET | `/health` | none | `HealthResponse` | Readiness + version | — | — | Live `ok` v9 |
| GET | `/model_info` | none | `ModelInfoResponse` | Model identity | — | — | Live v9 |

Strict schemas: numerics `float | None` (blanks → imputers, D-05); categoricals `Literal` vocabularies verified against raw (D-06); NO `ge`/`le` ranges (raw extremes bp 180 / sc 76 would false-reject). Startup pin documented as FR-4.4 deviation (D-02) in code docstring.

---

## SECTION 14 — PREDICTION VERSIONING

**Claim 4 (as implemented):** every prediction response and every prediction-log row carries the serving `model_version`, resolved from the MLflow Registry (pinned at startup from the Production stage).
**Chain:** Prediction → `model_version: "9"` → Registry `corvus-ckd` v9 → `run_id 10ac3e5e` → exact pipeline + estimator + params + metrics. Any historical prediction re-resolves to its exact model. **Benefit:** auditability (which model said what), safe rollback, drift attribution per version.

---

## SECTION 15 — POSTGRESQL

- **Technology:** PostgreSQL 16 (Compose service `db`, health-gated). **Table:** `predictions` (`api/db.py:28-68`, VERIFIED).
- **Schema (VERIFIED):** `id` PK autoincrement; 14 nullable Floats (age…rc); 10 `String(16)` categoricals; `prediction` Integer; `probability` Float; `model_version` String(32); `created_at` DateTime (server default + client default).
- **Behavior:** one row per prediction, single commit per request/batch (all-or-nothing); `DATABASE_URL` env wins, config fallback, empty default; unset → engine `None` → `/predict` 503 naming `DATABASE_URL` (D-03, no SQLite); unreachable configured store raises after 3 retries; URL value never logged.
- **Why logs matter:** traceability (what was asked/answered/by which version), auditing, debugging, monitoring input (Phase 4), drift fuel (Phase 5).

---

## SECTION 16 — FRONTEND

- **Tech/purpose:** Streamlit (`frontend/app.py`, VERIFIED by read) — thin demo client: grouped 24-field form (Vitals / Blood labs / History, units hinted), CSV batch tab, demo-patient presets (real test rows A/B), verdict cards (⚠️/✅ + probability bar + version), batch summary metrics + results-CSV download, sidebar with live `/health` + `/model_info`.
- **Flow:** form → `POST /predict`; CSV → `POST /batch_predict`; displays server responses; 422/413/500 surfaced verbatim; disconnect names `API_URL`.
- **Separation:** zero model logic; blanks sent as null for server imputers; categorical dropdowns mirror vocabularies as convenience only — server owns all validation.
- **Screenshots:** SCREENSHOT EXISTENCE NOT AVAILABLE IN CONTEXT (no screenshot files in repo; UI verified via live HTTP 200 smoke).

---

## SECTION 17 — DOCKER / DEPLOYMENT

- **Services (VERIFIED `docker/docker-compose.yml`):** `api` (build `docker/Dockerfile` → `python:3.11-slim`, `uvicorn api.app:app :8000`, ports `8000:8000`); `mlflow` (same image, tracking server `:5000`, ports `5000:5000`); `db` (`postgres:16`, `pgdata` volume, `pg_isready` healthcheck).
- **Wiring:** Compose network `docker_default`; `api.depends_on db:healthy`; `DATABASE_URL=postgresql+psycopg2://corvus:corvus@db:5432/corvus` (dev creds, accepted); `MLFLOW_TRACKING_URI=http://mlflow:5000`; mlruns via URI-rebased synced copy (`docker/sync_mlruns_container.py`, 48 files — fixes Windows-absolute artifact URIs unreadable in Linux containers); tracking-server `--allowed-hosts "mlflow:*,localhost:*,127.0.0.1:*"` (fixed live Host-header rejection).
- **Flow:** USER → Streamlit (host :8501) → FastAPI (:8000) → MODEL (v9) → DATABASE (log). Infra: TRAINING → MLFLOW file store → REGISTRY; API ↔ Postgres; MLflow + API share the synced store.
- **Exact commands (VERIFIED used):** `.\venv\python.exe docker/sync_mlruns_container.py` then `docker compose -f docker/docker-compose.yml up -d --build`; daily: `up -d` (no build); stop: `down` (volume survives; `-v` wipes — never casual).

---

## SECTION 18 — TESTING

Suite: pytest 8.x, `tests/`, synthetic fixtures + `tmp_path` isolation (never real data/`mlruns`/Postgres). Counts VERIFIED by collection 2026-09-23:

| File | Count | What it proves |
|---|---|---|
| `test_api.py` | 19 | Endpoints, 422s, version stamping, batch semantics, DB-unavailable branch |
| `test_ingestion.py` | 4 | `?`/whitespace quirks, summary shape, config override |
| `test_preprocessing.py` | 5 | Target cleaning, disjoint splits, Pipeline type, train-median imputation, config column origin |
| `test_registry.py` | 5 | Versioning, Staging/Archived transitions |
| `test_save_outputs.py` | 1 | Isolated round-trip, lineage cols, raw artifacts, real-dir untouched |
| `test_training.py` | 5 | Config construction, lineage exclusion (24 features), Claim-2 run artifacts |
| `test_validation.py` | 6 | Gate accept + 5 rejections (label, target, tiny, oversize, duplicates) |
| **Total** | **45/45 green** | Full lifecycle from quirks to serving |

Number lineage (never combine): **16/16** = Phase 1 suite after hardening (13 + column/oversize/duplicate tests); **26/26** = after Phase 2 (+10 training/registry); **45/45** = after Phase 3 (+19 API); **14/14** = Phase 1 verifier must-haves; **6/6** = Phase 2; **14/14** = Phase 3. Reviews: 0 criticals in Phase 2 (11 warn/6 info) and Phase 3 (9 warn/9 info) — advisory, open.

---

## SECTION 19 — FORMAL PROJECT CLAIMS

| Claim | Exact wording (from PROJECT.md / REQUIREMENTS.md) | Evidence | Implementation | Significance | Status |
|---|---|---|---|---|---|
| Claim 2 | Fitted preprocessing pipeline stored as MLflow artifact in same run as model | 9 runs each carry `preprocessing/` + `model/`; loader resolves pipeline from winner `run_id` | `train.py:141-153`, `model_loader.py:89-92` | Reproducibility; no train-serve skew | COMPLETED (verified live) |
| Claim 4 | Log deployed model version per prediction | Every response + every `predictions` row carries `model_version` | `app.py:130-134`, `db.py:60` | Auditability; rollback; drift attribution | COMPLETED (proven live v9) |
| Claim 5 | 5 Airflow trigger types + champion/challenger promotion + archived retention | Registry Staging/Production/Archived mechanics exist; no DAGs | None yet | Self-healing loop | PLANNED (Phase 5) |
| Component 102 | Standalone data visualization module | `notebooks/` exploration only; no `src/visualization/` | None yet | Shippable EDA component | PLANNED (Phase 6) |
| Claim 1 | NOT AVAILABLE IN CONTEXT (full text never shared) | — | — | — | UNKNOWN |
| Claim 3 | NOT AVAILABLE IN CONTEXT (full text never shared) | — | — | — | UNKNOWN |

---

## SECTION 20 — PROJECT PHASE HISTORY

| Phase | Date | Objective | Implementation | Results | Tests | Status | Remaining Work |
|---|---|---|---|---|---|---|---|
| 1 — Data Pipeline | 2026-09-19, hardened 09-21 | Leak-safe ingest→validate→split→pipeline | Quirk ingestion, GX gate, 279/40/81 split, single Pipeline, lineage | 24 feats, 0 nulls, stratified | 16/16, 14/14 must-haves | COMPLETED | None |
| 2 — Training + Tracking | 2026-09-21 | 9 configs, MLflow, registry | train/train_mlp/evaluate, 9 runs, v9 Staging | 7× ROC-AUC 1.0, winner mlp-relu | 26/26, 6/6 | IMPLEMENTED / UAT PENDING (MLflow-UI eyeball) | 1 human check |
| 3 — API + Containers | 2026-09-21→23 | Versioned service + Postgres + Compose + UI | api/, Postgres log, Compose, Streamlit, v9→Production | Live 200s v9, DB row, clean down | 45/45, 14/14 | IMPLEMENTED / UAT PENDING (browser check) | 1 human check |
| 4 — CI/CD + Monitoring | DATE NOT AVAILABLE | Actions pipeline; Prometheus + Grafana | None | — | — | PLANNED | All |
| 5 — Drift + Retraining | DATE NOT AVAILABLE | Evidently + Airflow + Claim 5 | None | — | — | PLANNED | All |
| 6 — Visualization + Polish | DATE NOT AVAILABLE | Component 102 + integration + demo | None | — | — | PLANNED | All |

Data track (new, precedes 4–6 per user decision): vet big cohort → harmonize → re-run loop → external validation on UCI-857 → promote new champion. No verified candidate yet (4 rejections logged).

---

## SECTION 21 — DRIFT DETECTION & RETRAINING — **PLANNED** (no implementation evidence)

UCI-336 (train) → PRODUCTION MODEL (v9) → PRODUCTION DATA (Postgres log) → DRIFT DETECTION (Evidently: live vs 336 baseline; UCI-857 as simulated incoming batch) → ALERT past threshold → AIRFLOW (5 trigger types) → RETRAIN → CHALLENGER vs CHAMPION → PROMOTE iff better (Claim 5) → ARCHIVE superseded. **Entire flow PLANNED — present as roadmap, never as built.**

---

## SECTION 22 — CI/CD & MONITORING — **PLANNED** (no implementation evidence)

GitHub Actions (test → build → push), Prometheus (latency, request count, error rate), Grafana dashboard: all PLANNED (Phase 4/6-7). No `.github/`, no `metrics.py`, no dashboard JSON exists. **IMPLEMENTED today:** per-commit local pytest discipline + Loguru file logs + MLflow tracking. Do not present monitoring as deployed.

---

## SECTION 23 — COMPLETE ARCHITECTURE

USER (browser: form + CSV) → STREAMLIT (:8501, host; zero model logic) → FASTAPI (:8000, lifespan-pinned v9, Pydantic 422 gate) → MODEL (Pipeline + MLP-ReLU, width-probed) → versioned JSON + DATABASE (Postgres `predictions`, full record). Infra: TRAINING (offline Phases 1–2) → MLFLOW file store → REGISTRY (v9 Production); API ↔ Postgres via `DATABASE_URL`; MLflow + API share URI-rebased synced store; Compose health-gates `db` before `api`. Future: Prometheus scrape, Evidently reads of Postgres log, Airflow retrain loop.
Per connection — Streamlit→API: HTTP POST, serving; API→Model: in-process transform+predict; API→DB: SQLAlchemy INSERT per prediction; Training→MLflow: runs + artifacts + versions; MLflow→API: `models:/corvus-ckd/9` + pipeline download at startup.

---

## SECTION 24 — ENGINEERING PRACTICES (all VERIFIED in code)

| Practice | Implementation | Evidence | Benefit | Status |
|---|---|---|---|---|
| Fail-closed validation | GX gate aborts pipeline; 422 before inference; 503 no-DB | `validate.py`, `app.py:72-78` | Bad data never flows downstream | Active |
| Leak-safe ML | Split before fit; train-only fitting asserted by tests | `preprocess.py`, median-equality test | Honest metrics | Active |
| Config-driven | Single YAML; deepcopy per caller; no second config mechanism | `config.yaml`, `config.py` | Dataset swaps = config edits | Active |
| Reproducible seeds | 42 family; defaults + documented rationales, no grids at n=279 | `train.py:49-62` | Repeatable runs | Active |
| Data lineage | `__source_row` + `__source_id` on every output row | `preprocess.py`, tests | Row-level traceability | Active |
| Versioned serving | Startup pin; width probe; version on every response/row | `model_loader.py`, `app.py` | No skew; auditability | Active |
| Safe errors | 500s without tracebacks; secrets never logged | `app.py:207-212`, `db.py:81-89` | No info leakage | Active |
| Atomic batches | All-or-nothing CSV; single commit; 5 MB/10k-row caps | `app.py:137-189` | No partial states; anti-DoS | Active |
| Test isolation | Synthetic fixtures; tmp tracking/DB; real dirs snapshotted | `tests/`, `conftest.py` | Tests never touch prod state | Active |

No auth, no rate limiting, no TLS, no security certification — do NOT claim them (localhost demo; recorded gap).

---

## SECTION 25 — IMPORTANT TECHNICAL DECISIONS

- **Why UCI-336?** Only provenanced real cohort without label defects → alternatives rejected on evidence, not taste. STATUS: locked.
- **Why UCI-857 reserved?** Independent cohort = only honest external validation available → spending it on training destroys the generalization proof. STATUS: locked.
- **Why split before fit?** Full-fit leaks test statistics into preprocessing → caught in review, fixed, test-asserted. STATUS: enforced.
- **Why one sklearn Pipeline?** Single serializable artifact = Claim 2 object + identical train/serve transforms. STATUS: built.
- **Why 9 models?** Evidence-based selection + the comparison is itself the deliverable; defaults-only at n=279 (grids fit noise). STATUS: built.
- **Why ROC-AUC?** Threshold-free ranking for a clinical screen; strict-max, no tie-break, recorded. STATUS: locked.
- **Why MLflow?** Params+metrics+artifacts+registry in one queryable system; `models:/` URIs decouple serving from files. STATUS: built.
- **Why FastAPI?** Typed async Python API matching the ML stack; Pydantic 422s; TestClient-testable. STATUS: built.
- **Why PostgreSQL?** Relational audit log + SQL-readable drift fuel; one backend, no SQLite split. STATUS: built.
- **Why Compose?** Full system in one command; health-gated startup. Kubernetes cut as disproportionate. STATUS: built.
- **Why Streamlit?** Single-file demo UI; zero model logic; full Next.js care platform parked as M2. STATUS: built (prototype-grade by design).
- **Why not synthetics?** 200K leaky label, 20K synthetic fingerprints, 4K circular `ckd_pred`, 25.8K rule-deterministic Target — each rejected on forensic evidence. STATUS: locked, files deleted.

---

## SECTION 26 — LIMITATIONS (all supported — state these plainly)

- 279 training rows; 81-row test set cannot separate top models (7× ROC-AUC 1.0 tie).
- Single-center cohorts; no external validation performed yet (UCI-857 reserved, unused).
- No clinical validation, no clinician review, no regulatory standing.
- No CI/CD, monitoring, drift, or retraining — roadmap, not reality.
- File-store tracking (maintenance-gated upstream); no auth/rate-limit/TLS.
- Two UAT eyeball checks open (MLflow UI, Streamlit browser).
- 17 advisories across two code reviews unaddressed (0 critical).

> CORVUS SHOULD NOT BE PRESENTED AS A CLINICALLY DEPLOYED DIAGNOSTIC SYSTEM — no clinical validation or deployment evidence exists. It is an engineering demonstration of the MLOps lifecycle on real clinical data.

---

## SECTION 27 — FUTURE SCOPE

**Immediate:** close 2 UAT checks; CV + confidence intervals in `evaluate.py`; Phase 4 CI/CD + monitoring.
**Medium-term:** Phase 5 drift + Airflow retraining (Claim 5); Phase 6 Component 102 + integration + demo polish; NHANES-with-leakage-protocol as Phase 6 stretch; data-track retrain on a vetted big cohort (none verified yet).
**Long-term / stretch:** M2 Next.js care platform (doctor/patient roles, histories, review); image-based CNN (needs dataset re-selection); Abu Dhabi survival analysis (different paradigm). All FUTURE unless built.

---

## SECTION 28 — PPT FIGURES & SCREENSHOTS

| # | Slide purpose | Visual needed | Shows | Why | Source | Availability |
|---|---|---|---|---|---|---|
| 1 | EDA credibility | Missingness heatmap + bar | 38% worst-column gaps, quirk reality | Proves real messy data | `reports/figures/missingness_heatmap.png`, `missingness_bar.png` | VERIFIED present |
| 2 | EDA signal | Hemo KDE by class + RBC counts + correlation heatmap | Class separation + feature relations | Evidence of learnable signal | `reports/figures/` (3 files) | VERIFIED present |
| 3 | Pipeline | Split-before-fit flow diagram | Raw→split→fit-train-only→transform-all | The leakage story in one image | Draw from Section 5/6 text | Must be drawn |
| 4 | Architecture | System diagram (Section 23) | User→UI→API→Model→DB + infra | Whole system at a glance | Draw from Section 23 | Must be drawn |
| 5 | Results | MLflow experiment screenshot | 9 runs × metrics + artifacts | Tracking is real, not claimed | http://localhost:5000 | Capture live |
| 6 | Registry | Models tab screenshot | v9 Production, v1–v8 Archived | Lifecycle + human gate | http://localhost:5000 | Capture live |
| 7 | API | `/predict` JSON response | prediction + probability + version 9 | Claim 4 visible | curl/Streamlit | Capture live |
| 8 | UI | Streamlit form + verdict card | Demo surface | Human-usable product | Browser :8501 | Capture live |
| 9 | DB | Postgres row SELECT | Timestamped versioned row | Audit trail exists | `psql` output | Capture live |
| 10 | Tests | pytest green tail | 45 passed | Quality gate proof | Terminal screenshot | Capture live |
| 11 | Roadmap | MLOps loop diagram | Built (1–3) vs planned (4–6) vs M2 | Honest scope boundary | Draw from Sections 20/27 | Must be drawn |

No screenshots exist as files — all "capture live" items need a running stack + browser at deck-building time.

---

## SECTION 29 — EXAMINER / VIVA QUESTIONS

**Basic:** What is Corvus? → MLOps lifecycle platform for CKD prediction, 400-row UCI pilot, 3 of 6 phases built. What works today? → Pipeline, 9 tracked models, versioned API + Postgres + Docker, 45 tests.
**Dataset:** Why UCI-336? → Only provenanced real cohort without label defects; 250/150 split, 24 features, 38% worst missingness. Why not the bigger ones? → 200K leaky eGFR label; 20K synthetic fingerprints; 4K circular `ckd_pred`; 25.8K rule-deterministic Target (7 combos, 0 mixed) — each rejected on forensic evidence, files deleted.
**Leakage:** What is data leakage? → Test information influencing training (statistics, vocabularies, labels). Why split before preprocessing? → Otherwise imputer/scaler/encoder absorb test stats; original code did this, review caught it, median-equality test now enforces the fix.
**ML:** Why 9 models? → Evidence-based selection; comparison is the deliverable. Why MLP-ReLU? → Strict-max ROC-AUC per locked rule; honest footnote: 7-way tie at 1.0, wins by run order, trees are co-champions. Why ROC-AUC? → Threshold-free clinical ranking. Why defaults only? → Grids fit noise at n=279.
**MLflow/Registry:** Why MLflow? → Params+metrics+artifacts+registry queryable in one system; `models:/` URIs decouple serving from files. Claim 2? → Pipeline + model co-logged in all 9 runs; serving loader resolves pipeline from winner run_id. Claim 4? → `model_version` on every response + DB row, resolved from Registry Production. Why versioning? → Auditability, rollback, drift attribution; v9 Production via human gate, never auto-deployed.
**API/DB/Docker:** Why FastAPI? → Typed Python API, Pydantic 422s, TestClient-tested. DB down? → 503 fail-closed naming DATABASE_URL, never silent serving. Batch bad row? → Whole batch 422 with 1-indexed row number. Why Postgres? → Relational audit log + SQL drift fuel; one backend per D-03. Why Docker? → One-command full system; K8s cut as disproportionate.
**MLOps/future:** Production model selected how? → Automated strict-max + human Staging→Production promotion. Drift how? → PLANNED: Evidently live-vs-336 + UCI-857 simulated batch → Airflow retrain → challenger iff better (Claim 5). Why UCI-857? → Independent cohort; spending it on training destroys the generalization proof.
**Limitations:** State them first: n=279, no external/clinical validation, no CI/monitoring/drift yet, 2 UAT checks open. Never claim clinical deployment.

---

## SECTION 30 — TEAM CONTRIBUTION

> **TEAM CONTRIBUTIONS NOT AVAILABLE IN CONTEXT** — `.planning/PROJECT.md` records "Developer: Solo". No per-person contribution records exist.

> **SUGGESTED PRESENTATION DIVISION — NOT HISTORICAL CONTRIBUTION** (4 members × actual modules):
> 1. Data engineering — ingestion, validation, leak-safe preprocessing, lineage (`src/ingestion`, `src/preprocessing`, `src/validation`).
> 2. Modeling & tracking — 9 configs, metrics, MLflow runs, registry lifecycle (`src/training`, `src/evaluation`, MLflow UI + Models tab).
> 3. Serving & deployment — API, Postgres logging, Docker stack, Streamlit demo (`api/`, `docker/`, `frontend/`, live demo).
> 4. Quality & roadmap — test suite, verification, Claims 1–5 status, limitations, drift/retraining + M2 future (tests, UAT, roadmap slides).

---

## SECTION 31 — FINAL 12–14 SLIDE STORYLINE

| Slide | Title | Purpose | Key Facts | Visual | Presenter |
|---|---|---|---|---|---|
| 1 | Corvus: CKD MLOps Platform | Identity + pitch | One-line pitch; 3/6 phases built | Title + stack badges | (per-team) |
| 2 | Problem & Motivation | Why MLOps, not notebooks | Model rot; notebook gaps → lifecycle answer | Problem→Gap→Solution | — |
| 3 | Dataset & Selection | Provenance + rejections | 400 rows 250/150; 4 alternatives rejected on evidence | Missingness plot + decision table | — |
| 4 | Validation & Leak-Safe Preprocessing | Trustworthy inputs | GX gate; split-before-fit; 279/40/81; 24 feats | Pipeline flow diagram | — |
| 5 | Architecture | Whole system | User→UI→API→Model→DB + infra (Sec 23) | Architecture diagram | — |
| 6 | Models (9 configs) | Comparison design | 6 classical + 3 MLP; defaults+seeds rationale | Config table | — |
| 7 | Results | Honest metrics | 7× ROC-AUC 1.0 + tiebreak footnote | MLflow screenshot + table | — |
| 8 | MLflow & Registry | Claim 2 + lifecycle | Co-logged runs; v9 Production via human gate | Models-tab screenshot | — |
| 9 | API + Claim 4 | Versioned serving | 4 endpoints; version on every answer | `/predict` JSON screenshot | — |
| 10 | Postgres + Docker | Audit + deploy | Full-record rows; one-command stack | DB row + compose up | — |
| 11 | Testing & Verification | Quality proof | 45/45; 14+6+14 must-haves; 0 criticals | pytest green screenshot | — |
| 12 | Roadmap & Future | Honest boundary | Built vs planned vs M2; data-track next | MLOps loop diagram | — |
| 13 | Limitations | Credibility | Small-n, no clinical validity, open UAT | Plain list | — |
| 14 | Conclusion | Close | Engine built; product path clear | 5 core sentences | — |

---

## SECTION 32 — FIVE CORE PROJECT SENTENCES

1. Corvus trains on 400 real UCI CKD rows (250 CKD / 150 healthy, 24 features) after documented rejection of four larger-but-invalid alternatives.
2. A split-before-fit sklearn Pipeline (279/40/81, median-imputed, 24 outputs) guarantees no test leakage, enforced by tests.
3. Nine seeded configs were tracked in MLflow and strict-max ROC-AUC selected MLP-ReLU, registry v9, with tree ensembles as effective co-champions.
4. Pipeline and model are co-logged in every run (Claim 2) and every prediction carries its registry version into PostgreSQL (Claim 4).
5. A health-gated Docker Compose stack serves the versioned API with a Streamlit UI, covered by 45 passing tests.

---

## SECTION 33 — PROJECT FACT SHEET

| Category | Verified Fact |
|---|---|
| Project | Corvus — CKD MLOps platform, academic (TY EDI), solo dev |
| Domain | Chronic Kidney Disease binary classification |
| Primary Dataset | UCI-336 `kidney_disease.csv` |
| Dataset Size | 400 rows × 26 cols; 250 ckd / 150 notckd |
| Target | `classification` → 1/0 |
| Features | 14 numeric + 10 categorical |
| Split | 279 / 40 / 81, stratified ≈62.5% |
| Preprocessing | Single Pipeline: median/mode impute, scaler, one-hot(ignore, drop-first); 24 out, 0 nulls |
| Models | LR, DT, RF, GB, XGB, LGBM + MLP×3 (50,), max_iter 500, seeds 42 |
| Winning Model | MLP-ReLU, registry v9, `run_id 10ac3e5e` |
| Best Metric | Test ROC-AUC 1.000 (7-way tie; strict-max rule) |
| Experiment | `corvus-ckd`, 9 runs, 5 metrics + pipeline + model each |
| MLflow | 3.16.1 file store + opt-in flag; container synced copy |
| Registry | v1–v8 Archived, v9 Production (human-promoted) |
| API | FastAPI: predict / batch_predict / health / model_info; startup-pinned v9; strict 422; 413 caps |
| Database | Postgres 16 `predictions`: 24 fields + outcome + version + timestamp |
| Frontend | Streamlit: grouped form, presets, verdict cards, batch + CSV download |
| Deployment | Compose (api :8000, mlflow :5000, db :5432); python:3.11-slim |
| Tests | 45/45 (19+4+5+5+1+5+6); must-haves 14+6+14; reviews 0 critical |
| Current Status | Phases 1–3 built; 2 UAT eyeball checks open; 4–6 + data track planned |
| Main Future Work | Vetted big-cohort retrain → CI/CD + monitoring → drift/retraining → polish → M2 care platform |

---

## SECTION 34 — FINAL CONSISTENCY AUDIT

- **Dataset:** 400 / 250 / 150 / 24+target+id consistent across code, store, docs. UCI-857: 200 / 128 / 72 consistent.
- **Preprocessing:** split-first narrative consistent; 24 features consistent (config 14+10, transformed 24, loader 24, schema 24).
- **Models:** 9 configs consistent (code dicts, 9 runs, metrics table); winner mlp-relu v9 consistent; metrics match store queries.
- **MLflow:** 9 runs, v1–v9, v9 Production consistent across store, API, UAT.
- **API:** 4 endpoints, version behavior, batch semantics consistent with `app.py` read.
- **Database:** schema fields consistent with `db.py` read.
- **Testing:** 19+4+5+5+1+5+6 = 45; lineage 16→26→45; must-haves 14/6/14 — no double counting.
- **Phases:** 1 COMPLETED, 2–3 IMPLEMENTED/UAT-PENDING, 4–6 PLANNED — roadmap/STATE/dossier agree.
- **Future:** drift/retraining/M2 never presented as built in this file.

## UNRESOLVED PROJECT FACTS
- Claims 1 & 3 texts (never shared — excluded from all claim tables).
- UCI-336 clinician/institution names (provenance asserted, names not in context).
- Exact Phase 4–6 dates (not scheduled).

---

## SECTION 35 — PPT-SAFE FACTS VS UNSAFE CLAIMS

## PPT-SAFE FACTS
Everything in Sections 4–18 with VERIFIED/ESTABLISHED marking: row counts, splits, configs, metrics, versions, endpoints, schema, test counts, forensic rejections, review counts.

## DO NOT CLAIM WITHOUT ADDITIONAL EVIDENCE
Clinical deployment or diagnostic use; real-world accuracy beyond the 81-row test set; production-scale reliability; automatic retraining or monitoring (PLANNED); automated promotion (human-gated); security certifications, auth, or encryption; external validation performed (reserved, not run); generalization beyond UCI cohorts; Streamlit as production frontend (prototype by design); any capability of Claims 1/3.

---

## SECTION 36 — FINAL EXECUTIVE SUMMARY

1. **What is CORVUS?** A six-phase MLOps platform (3 built) taking CKD prediction from raw clinical CSV to a versioned containerized service.
2. **What problem?** Academic ML stops at training; deployed models need validation, versioning, serving, logging, monitoring, retraining.
3. **Actually implemented?** Leak-safe pipeline; 9 tracked configs; registry lifecycle to Production; versioned API + Postgres logging + Compose + Streamlit UI.
4. **Evidence?** 45/45 tests; 34/34 plan must-haves; live MLflow store (9 runs, v9 Production); live container smoke (200s, DB row, clean down); 0-critical reviews.
5. **Why engineering, not a notebook?** Gates that fail closed, artifacts over assertions, versions over files, audit logs over printouts — every claim executable.
6. **Unfinished?** 2 UAT eyeball checks; CI/CD, monitoring, drift, retraining, visualization; vetted big-cohort retrain; M2 care platform.
7. **Evolution?** Data-track retrain on a provenanced cohort → observe it (Phase 4) → self-heal it (Phase 5) → polish (Phase 6) → serve patients and doctors (M2).