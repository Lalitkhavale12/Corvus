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

  **Superseded:** the 24-field harmonization was abandoned. The native NHANES contract
  (portable-23) went straight into the API as slot v2 instead of being squeezed into the
  UCI shape — see Phase 7 below.

## Phase 4 — CI/CD + Monitoring ✅ Complete (closed 2026-11-10)

### What was done
- `.github/workflows/ci.yml` tracked and enforced (`a65243f ci: make the pipeline a real gate`) — the `|| true` soft-fails are gone, so lint or tests failing now fails the build; no docker build/push (the demo is local-first)
- `api/app.py` exports `/metrics` with `corvus_predictions_total{model_version=...}` plus request counts and latency histograms
- Compose grew to 10 services: `prometheus` (9090), `grafana` (3001), `alertmanager` (9093), `node-exporter` (9100), `postgres-exporter` (9187) alongside db/api/mlflow/frontend
- 3 scrape jobs (API, node, postgres) and 7 alert rules — `APIDown`, `APIHighErrorRate`, `APIHighLatency`, `HighPredictionVolume`, `LowPredictionProbability`, `DatabaseConnectionsHigh`, `NoNewUsers`
- Grafana dashboard provisioned from `docker/grafana/` (uid `corvus-api`), Prometheus as default datasource
- Removed the MLflow scrape job: MLflow 3 dropped `/metrics`, and a permanently-down target is worse than no target

### Results
- Verified live: 3/3 Prometheus targets up, 7 rules loaded, Alertmanager ready, Grafana healthy, prediction counter incrementing on v15
- **150 passed / 2 skipped** at the time this closed (was 45/45 in Phase 3)

## Phase 5 — Drift Detection + Auto-Retraining ✅ Complete, drift signal unproven (closed 2026-11-10)

### What was done
- `src/monitoring/retrain_triggers.py` — five independent triggers: champion age (30 days), drifted-feature share (0.3), unabsorbed production rows (500), labelled-batch ROC-AUC floor (0.80), manual `force_retrain`
- `airflow/dags/corvus_drift_retrain.py` — `gather_evidence → decide_retrain --(retrain)--> retrain_challenger → compare_with_champion → report`, with a `skip_retraining` branch; the retrain task calls the real trainer (`src.training.train_nhanes`), not a log line
- Champion/challenger verdict written to `reports/retrain/` and tagged on the challenger run
- `scripts/promote_challenger.py` / `promote_production.py` — promotion stays a human gate; nothing auto-deploys

### Results
- Claim 5 (evidence-triggered retraining) is implemented across all five trigger types
- Honest gap: with demo traffic, no trigger has fired on genuine production drift; the mechanism is exercised, the clinical signal is not

## Phase 6 — Visualization + Polish 🟡 Absorbed into Phases 8 and 9 (2026-11-10)

### What was done
- `src/visualization/` kept as the figure source (ROC/PR curves, confusion matrix, feature
  importance) — it feeds documentation, not the served product
- The "polish" half of the phase was absorbed: the console became React (Phase 8), and the
  integration tests, diagrams and doc pass landed in Phase 9

### Results
- No standalone visualization deliverable. Figures are generated on demand into
  `reports/figures/`, which is intentionally not committed (empty directory, .gitkeep only)

## Phase 7 — NHANES Native Retrain ✅ Complete (closed 2026-11-10)

### What was done
- Cohort rebuilt as three cycles (I/J/L): **15,244 adults, 2,696 positives (17.69%), 0 duplicate SEQN**
- Forward split: whole cycle L held out (5,343 rows); dev = cycles I+J (9,901); threshold tuned on dev out-of-fold only
- Portable-23 contract: 20 numeric + 3 categorical (`RIAGENDR`, `DMDEDUC2`, `DIQ010`); dropped US-only `RIDRETH1` and `MCQ035` — measured cost dev dROC -0.0015, holdout dROC -0.0031 (inside noise)
- Pipeline width asserted at **36** at API startup, so a contract mismatch fails the boot instead of the prediction
- 6 tracked runs in `corvus-ckd-nhanes`; selection on PR-AUC, not accuracy

### Results
- Champion **v15** (`30830a71...`): GradientBoosting, log_loss, depth 3, 100 trees, seed 42
- Holdout: ROC **0.8214** (CI 0.8062-0.8362), PR-AUC **0.5895**, Brier 0.1042, CV 0.8205 +/- 0.0120
- At deployed threshold **0.10256**: precision **0.3239**, recall **0.8378**, F1 0.4671, accuracy 0.6691; at 0.50: 0.7140 / 0.3589
- v14 (random forest) had the best ROC (0.8313) but lower PR-AUC (0.5628) — wrong shape for a 17.7% positive class, so v15 shipped
- Leakage corrected: an earlier 0.83 came from scoring unseen rows of a cycle partially fitted on

## Phase 8 — Web Console + Auth ✅ Complete (closed 2026-11-10)

### What was done
- React 19 + Vite 8 + Tailwind 3 + React Router 7 console, 11 pages, served by nginx on 3000 (replaced Streamlit)
- JWT auth with roles (patient/doctor), clinical profiles, doctor-to-patient mapping; Alembic `0001`-`0003` own the auth/profile tables
- Prediction history served from Postgres (`GET /auth/predictions`), so clearing the browser no longer erases the audit trail
- `docker/nginx.conf` SPA fallback — deep links and reloads stopped 404ing
- Screening disclaimer as a standing footer in `ClinicalShell.jsx`

### Results
- Login, register, assessment, result card showing `model_version`, history, models and comparison pages all working against the live API
- Deviation kept and documented: `predictions` / `predictions_v2` are created by SQLAlchemy `create_all`, not Alembic (`0004` deliberately not written). Consequence learned the hard way — `create_all` never alters an existing table, so a nullability change needs an explicit drop and recreate

## Phase 9 — Stabilisation ✅ Complete (closed 2026-11-10)

### What was done
- Playwright E2E suite (`website/e2e/clinical.spec.js`, chromium, 1 worker) over the running Compose stack — no `webServer`, so it tests the real containers
- Registry stages normalised to match the serving pin: v15 Production, v1-v14 Archived
- `docs/ppt.md` rewritten as a v15 dossier; `README.md`, `report.md` and this log reconciled

### Results
- E2E found four real defects, each fixed with a test pinning it: missing SPA fallback; coded categoricals posted as strings plus four missing lab fields; a reload that silently logged the user out (profile 404 cleared the token); NOT NULL columns predating nullable categoricals
- **5/5 E2E green** (11 s) · **150 passed / 2 skipped** in pytest (211 s) · CI green on `main`
