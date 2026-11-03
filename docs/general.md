# Corvus — Build Log

> Living record of what was done in each phase and what it produced.
> Update this file when a phase starts (scope + plan) and when it closes (results + evidence).

## Phase 1 — Data Pipeline ✅ Complete (2026-09-19, hardened 2026-09-21)

### What was done
- Raw CKD ingestion with UCI quirk handling (`?` → missing, whitespace/tab stripping, dtype coercion)
- GX validation gate (9-expectation suite + config row bounds + duplicate check, fail-closed)
- Leak-safe split-first preprocessing (train/val/test before any fit; pipeline fits train-only)
- Single `sklearn` Pipeline artifact (median/mode impute + scaler + one-hot, `handle_unknown="ignore"`)
- Config single source of truth (`numeric_cols`, `categorical_cols`, splits, validation, MLflow)
- `src/validation/` package; ingestion + preprocessing both gate before writing
- Lineage columns (`__source_row`, `__source_id`) on every output row; raw + transformed splits persisted
- EDA notebook (11 cells, read-only) + 5 figures in `reports/figures/`

### Results
- Train 279 / val 40 / test 81, stratified (~62.5% positive in all splits)
- 24 features, 0 nulls post-transform; pipeline reloads and transforms raw correctly
- **16/16 tests green** · 14/14 verification must-haves · Claim 2 pipeline object exists (MLflow logging lands in Phase 2)

## Phase 2 — Model Training + Experiment Tracking 🟡 Built, UAT pending (2026-09-21)

### What was done
- `src/training/train.py` — LR, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM (defaults + fixed seeds, documented rationales)
- `src/training/train_mlp.py` — MLP Sigmoid/Tanh/ReLU as 3 runs (single hidden layer, fixed budget, no early stopping)
- `src/evaluation/evaluate.py` — accuracy/precision/recall/F1/ROC-AUC per run, strict-max ROC-AUC winner, Staging transition
- Training consumes `*_raw.csv` through the pipeline (Claim 2 contract); pipeline + model logged in the same MLflow run
- Every run registered as a version; winner → Staging; superseded → Archived
- `tests/conftest.py` + `test_training.py` + `test_registry.py` (synthetic fixtures, tmp tracking dirs)

### Results
- 9 runs in experiment `corvus-ckd`; 7 configs at ROC-AUC 1.0, LogReg/MLP-3rd 1.0, DecisionTree 0.980
- Winner: `mlp-relu` v9 (v1–v8 Archived; v9 moved Staging → Production as Phase 3's first act)
- **26/26 tests green** · 6/6 verifier must-haves · review: 0 critical
- Pending: human UAT (MLflow UI 9 runs + artifacts) — `02-UAT.md`

## Phase 3 — Prediction API + Containerization 🟡 Built, UAT 1/2 (2026-09-21 → 2026-09-23)

### What was done
- Promoted `corvus-ckd` v9 Staging → Production (human gate from Phase 2)
- `api/` — FastAPI: `POST /predict` (24 fields, strict 422), `POST /batch_predict` (CSV, all-or-nothing), `GET /health`, `GET /model_info`; version pinned at startup; every response carries `model_version` (Claim 4)
- `api/db.py` — full-record Postgres logging (fields + prediction + probability + version + timestamp); fail-closed 503 when DB unavailable
- `docker/` — health-gated Compose (API + MLflow + Postgres); mlruns volume-mount with Windows→Linux URI rebase script; localhost host-header fix on the tracking server
- `frontend/app.py` — Streamlit UI over predict + batch (zero model logic); enhanced 2026-09-23: grouped clinical sections, live serving sidebar, verdict cards, batch summary + CSV download, demo-patient presets
- `tests/test_api.py` — TestClient suites (predict/health/version/batch/log/oversize/unavailable)
- `batch.csv` — 12-row demo batch (7 CKD + 5 healthy, shuffled) for presentations

### Results
- Compose smoke proven live: `/health` + `/predict` 200 on v9, Postgres row timestamped v9, clean `down` with zero containers
- **45/45 tests green** · 14/14 verifier must-haves · review: 0 critical
- Pending: human UAT test 2 (Streamlit in browser) — `03-UAT.md` (test 1 passed, agent-executed with evidence)

## Data Track — Big-Cohort Retrain 🟡 NHANES derivation in progress (from 2026-10-10)

### What was done
- Dataset hunt + forensic vetting: 200K (leaky eGFR label), 20K (synthetic fingerprints), 4K (circular `ckd_pred`), 25.8K KDIGO (rule-deterministic Target, 7 combos 0 mixed; card stats contradicted file), NHANES-derived 11.9K CSV (fiat-labeled Unknown block), UCI-857 (binned + contaminated binaries, rejected for validation too) — all rejected, disproven files deleted
- NHANES 2021–2023 fetched from CDC (public): `DEMO_L` 11,933 + `BIOPRO_L` 7,199 + `ALB_CR_L` 8,493 + `MCQ_L` 11,744 → expected ~6–7K joinable adults
- `data/nhanes/NHANES_PROTOCOL.md` written: KDIGO label rule, 10-column quarantine list (eGFR/ACR/creatinine banned from inputs), 3 audit gates — derivation blocked on user approval

### Results
- **NHANES derivation PASSED all 3 audit gates 2026-10-10:** 5,343 labeled adults (eGFR+ACR complete), 17.3% positive, 0 duplicates; circularity probe (allowed-inputs-only RF) = 86% — real signal, no leak
- **`data/nhanes/nhanes_ckd_derived.csv` (5,343 × 177) is the big-cohort training set** — 13× UCI-336; quarantine (creatinine/eGFR/ACR banned from inputs) held throughout; v2 re-derivation merged all 10 XPTs (BMI/BP/HbA1c/diabetes now present, cohort unchanged, gates re-passed with 83 allowed inputs at 86%)
- Next: harmonize to 24-field schema → retrain loop → validate → promote

## Phase 4 — CI/CD + Monitoring ⬜ Not started (runs after data track)

### What was done
- (Scope: GitHub Actions test → build → push; Prometheus metrics; Grafana dashboard)

### Results
- (Pending)

## Phase 5 — Drift Detection + Auto-Retraining ⬜ Not started

### What was done
- (Scope: Evidently drift report, UCI-336 vs UCI-857; Airflow trigger DAGs — Claim 5; champion/challenger promotion)

### Results
- (Pending)

## Phase 6 — Visualization + Polish ⬜ Not started

### What was done
- (Scope: standalone `src/visualization/` — Component 102; integration tests; docs/diagram/demo)

### Results
- (Pending)
