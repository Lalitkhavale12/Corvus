# CORVUS - Technical Project Dossier (for PPT generation)

Status: current as of 2026-11-11, branch `main`, served model `corvus-ckd` **version 15**.
Every number below was read from the running stack, the MLflow store, or the repository -
not recalled. Where something is planned rather than built, it says so.

Rule for the deck: the honest headline is **holdout ROC-AUC 0.8214, PR-AUC 0.5895,
precision 0.324 at recall 0.838**. Corvus is a **screening** aid. Never present it as a
diagnostic device, and never show a 1.000 metric - that number belonged to the retired
336-row UCI proof of concept and is not the model being served.

---

## SECTION 1 - PROJECT IDENTITY

| Field | Value |
|---|---|
| Name | Corvus |
| Domain | Chronic Kidney Disease (CKD) risk screening from routine blood and urine panels |
| Core idea | A patient or clinician enters a standard lab/clinical panel; Corvus returns a calibrated CKD risk, the decision cut-off it used, and the exact model version that produced it |
| Model served | `corvus-ckd` v15 - sklearn `GradientBoostingClassifier` inside a `ColumnTransformer` pipeline, 36 input features |
| Stack | Python 3.11, scikit-learn, pandas, MLflow 3, FastAPI, Pydantic v2, PostgreSQL 16, React 19 + Vite, nginx, Docker Compose, Prometheus + Grafana + Alertmanager, Airflow 3 |
| Public entry points | `http://localhost:3000` (React console), `http://localhost:8000/docs` (API), `http://localhost:5000` (MLflow) |
| Source of truth | `config/config.yaml`, MLflow run `30830a71...`, `docs/ppt.md` (this file) |

### Explain CORVUS in 30 seconds
Corvus takes the blood and urine numbers a lab already produces, derives a reproducible
CKD label from them, trains a gradient-boosted model on three NHANES cycles, and serves it
through a versioned API and a React console. Every prediction records which model version
answered. On the one cycle it never saw it scores ROC-AUC 0.82, flagging 84% of true cases -
as a screening tool, with the precision cost stated openly.

### Explain CORVUS in 1 minute
Chronic kidney disease is silent until late; a serum creatinine and a urine albumin ratio
are cheap and already ordered. Corvus turns that routine panel into a risk score. Labels
come from KDIGO criteria (CKD-EPI 2021 race-free eGFR < 60 or urine ACR >= 30), computed
deterministically - no clinician chart lookups, nothing circular. The cohort is three
NHANES cycles, 15,244 adults, 2,696 positives. Validation is a forward split: the newest
cycle is held out whole, so no row from the evaluation cohort was ever fitted on. The
served model is a depth-3 gradient boosting classifier on a 23-field portable contract
(20 labs plus three demographics), encoded to 36 pipeline features. The API pins the
version at startup, and the registry, the response, and the database row all carry it.

### Explain CORVUS technically to an examiner
`src/training/train_nhanes.py` reads `data/nhanes/nhanes_ckd_multi.csv` (15,244 x 28),
drops eleven label-source columns that would leak the target, builds the portable-23
contract, holds out SDDSRVYR cycle 12 entirely, tunes a decision threshold on 5-fold
out-of-fold dev probabilities to hit 80% recall, and logs params, metrics, the fitted
sklearn Pipeline and the estimator into the `corvus-ckd-nhanes` experiment. Selection is
PR-AUC first, since the positive class is 17.7% and accuracy is a trap. The winner is
registered as a version of `corvus-ckd`; FastAPI (`api/model_loader.py`) loads that
version at startup, asserts the pipeline width equals the estimator's `n_features_in_`
(36), and serves `/v2/predict`, writing each answer to `predictions_v2`.

---

## SECTION 2 - PROJECT MOTIVATION

- **Clinical gap.** CKD is staged from eGFR and albuminuria, both of which sit in routine
  panels. Risk is therefore computable before symptoms, but nobody scores it consistently.
- **Technical gap.** Public CKD demos train on 300-400 row curated CSVs, report perfect
  metrics, and collapse on real cohorts. Corvus is built to survive a real cohort and to
  report the number it actually gets.
- **Engineering gap.** Most student ML projects stop at a notebook. Corvus ships the whole
  path: reproducible data build, tracked experiments, registry versions, a versioned API,
  a UI, containers, metrics, alert rules, and an E2E suite.

## PROBLEM -> GAP -> CORVUS SOLUTION

| Problem | Gap in existing tools | What Corvus does |
|---|---|---|
| CKD is under-detected | Risk is never computed from data already on hand | Deterministic KDIGO label + 23-field risk model |
| Published demos are unrepresentative | Tiny curated cohorts, 1.000 metrics | 15,244-row real cohort, forward split, honest 0.82 |
| Predictions are unattributable | "The model" with no version | `model_version` on every response and every DB row |
| Models silently rot | Nothing watches drift or volume | Exporters, 7 alert rules, 5 retrain triggers in Airflow |

---

## SECTION 3 - COMPLETE PROJECT SCOPE

### A. COMPLETED (built, and verified against the running stack)
- Reproducible NHANES cohort build (multi-cycle, XPT -> CSV), golden test re-derives it.
- Deterministic label rule with 11 label-source columns quarantined.
- Portable-23 feature contract, chosen by ablation, with measured cost.
- Six tracked NHANES training runs; champion = v15; threshold artifact per run.
- MLflow registry `corvus-ckd`: v1-v9 legacy UCI archived, v10-v15 NHANES, v15 Production.
- FastAPI service with dual serving slots, 22 routes, JWT auth, roles, profiles, history.
- PostgreSQL logging of every v2 prediction, fail-closed if the row cannot be written.
- React 19 console: 11 pages (login, register, patient/doctor dashboards, assessment form,
  history, model comparison, models, profiles, patient assignment/detail).
- Docker Compose stack: db, api, mlflow, frontend, prometheus, grafana, alertmanager,
  node-exporter, postgres-exporter, airflow.
- Observability proven live: 3 Prometheus targets up, 7 alert rules loaded, Grafana
  dashboard provisioned, `corvus_predictions_total{model_version="15"}` incrementing.
- Airflow DAG `corvus_drift_retrain` with five independent retrain triggers.
- Test suite: 150 pytest passed / 2 skipped; 5 Playwright E2E passed; CI green on main.

### B. IMPLEMENTED, NEEDS A HUMAN EYEBALL
- Grafana dashboard content (scrapes and panels verified by API, screenshots pending).
- Doctor-role flows exist end to end but no doctor account is seeded in the demo DB.

### C. PARTIALLY IMPLEMENTED
- Drift: Evidently report generation exists and is wired to a trigger; no long-running
  production traffic to make the drift signal meaningful yet.
- Security hardening: JWT, throttled login, required `SECRET_KEY`, env-driven CORS, but no
  email verification, password reset, or refresh-token rotation.

### D. PLANNED / NOT STARTED
- Email verification and password reset.
- Per-user rate limiting beyond login throttling.
- Model card export as PDF.

### E. FUTURE / STRETCH
- Indian cohort (ICKD, 4,056 patients) as an external validation set.
- MIMIC-IV for ICU/AKI - different clinical question, low priority.
- Survey-weighted NHANES estimates (the current model is unweighted by design decision).

---

## SECTION 4 - DATASETS

### Primary cohort (VERIFIED from `data/nhanes/nhanes_ckd_multi.csv`)
| Property | Value |
|---|---|
| Source | CDC NHANES, merged multi-cycle extract |
| Cycles | SDDSRVYR 9 (2015-16), 10 (2017-20), 12 (2021-23) |
| Rows | 15,244 adults |
| Columns | 28 after merge |
| Positives | 2,696 (17.69%) |
| Duplicate SEQN | 0 |
| Label | KDIGO-derived: CKD-EPI 2021 race-free eGFR < 60 OR urine ACR >= 30 |

### Label audit
- 11 columns that encode the label (creatinine, eGFR, urine albumin, urine creatinine,
  ACR, ...) are quarantined and never used as inputs.
- Circularity probe: a model trained on those columns reaches 0.8201 AUC; the recorded
  limit is 0.99, so the label is not trivially recoverable from the allowed features.
- Independent cross-check against an external labeled dataset: 9,901 shared SEQN,
  **1 disagreement, 99.9899% agreement** (SEQN 98699).

### Retired dataset
The earlier UCI "Chronic Kidney Disease" CSV (400 rows: 279/40/81 split) is still in
`data/raw/` and still served by the legacy v1 slot at v9, but it is no longer the model
under discussion. Its perfect metrics were an artefact of a tiny curated cohort.

---

## SECTION 5 - DATA PIPELINE

```
NHANES XPT (CDC) -> ingestion -> quirk normalisation -> merged multi-cycle CSV
      -> GX-style fail-closed gate (row bounds, duplicate SEQN, label sanity)
      -> portable-23 projection (label-source columns dropped)
      -> forward split: cycle 12 held out whole
      -> ColumnTransformer fit on dev only
      -> estimator -> MLflow run (params, metrics, pipeline, model)
```

Gate behaviour: a cohort that fails bounds or contains duplicate SEQN aborts the run.
The gate attestation is logged as the `quarantine_attested=true` tag on each run.

---

## SECTION 6 - DATA SPLITTING & LEAKAGE PREVENTION

| Decision | Choice | Why |
|---|---|---|
| Split type | Forward (whole cycle out) | Random splitting on pools of cycles leaks future rows of the same cycle into training |
| Holdout | SDDSRVYR 12, 5,343 rows, never fitted | Makes the reported metric a real generalisation number |
| Dev set | Cycles 9 + 10, 9,901 rows | Enough for 5-fold CV and threshold tuning |
| Threshold tuning | Out-of-fold dev probabilities only | Never optimised on the holdout |
| Preprocessing | Fitted inside the dev fold only | No imputer or scaler sees holdout statistics |
| Burned split | Cycle 12 retired from tuning after use | Re-tuning against it would turn it into a second dev set |

**A real defect this caught.** An earlier version reported holdout ROC 0.83. It was scoring
unseen rows of the same cycle it was fitted on. Fixing the split dropped the honest number
to 0.8214. That correction is part of the project's story, not a footnote to hide.

---

## SECTION 7 - PREPROCESSING

| Step | Applied to | Detail |
|---|---|---|
| Median imputation | 20 numeric fields | Skewed labs; median is stable against the tail |
| Most-frequent imputation | 3 categorical fields | `RIAGENDR`, `DMDEDUC2`, `DIQ010` |
| StandardScaler | numeric block | Not strictly needed by trees, kept so linear baselines are comparable on one pipeline |
| OneHotEncoder (`handle_unknown="ignore"`) | categorical block | An unseen code degrades to all-zeros instead of raising |
| Output width | **36 features** | API asserts this equals `n_features_in_` at startup |

The API accepts a categorical as `null` ("not recorded") and imputes it. A key that is
simply missing from the JSON is a client bug and still returns 422; an out-of-vocabulary
code also returns 422 rather than being silently coerced.

---

## SECTION 8 - FEATURES

Portable-23 contract: chosen so the same model can run on non-US data later.

| Block | Count | Fields |
|---|---|---|
| Kidney function markers | 9 | serum creatinine, urea nitrogen, uric acid, sodium, potassium, calcium, phosphorus, albumin, ALT |
| Hematology | 5 | haemoglobin, haematocrit, WBC, RBC, RDW |
| Glycaemia | 1 | HbA1c |
| Anthropometric / BP | 3 | BMI, systolic BP, diastolic BP |
| Demographics | 2 | age, poverty-income ratio |
| Categorical | 3 | sex, education, diabetes status |

**Dropped deliberately:** `RIDRETH1` (US race categories) and `MCQ035` (US-only kidney
history item, 81.6% missing). Measured cost of dropping both: dev dROC -0.0015,
holdout dROC -0.0031 - inside noise. This is what makes the contract portable.

---

## SECTION 9 - MACHINE LEARNING MODELS

Six runs in experiment `corvus-ckd-nhanes`, all on the same forward split and the same
preprocessing:

| Run suffix | Model | Notes |
|---|---|---|
| `763555` | Logistic Regression | linear baseline, v10 |
| `5954f0` | Gradient Boosting (`log_loss`, depth 3, 100 trees) | v11 |
| `7889e8` | Gradient Boosting variant | v12 |
| `ba51e2` | Gradient Boosting variant | v13 |
| `2d5ad4` | Random Forest | v14 - highest ROC, lower PR-AUC |
| `30830a` | Gradient Boosting (`log_loss`, depth 3, 100 trees, seed 42) | **v15, champion** |

Why no neural net: on 9.9k dev rows with mostly tabular labs, boosted trees matched the
linear model within noise, and a small MLP added tuning burden without evidence of gain.
The earlier UCI phase did compare six classical models and three MLP variants; that
comparison is history, not the current selection rationale.

---

## SECTION 10 - EXPERIMENTATION AND RESULTS

### v15 on the blind held-out cycle (5,343 rows)

| Metric | Value |
|---|---|
| ROC-AUC | **0.8214** (95% bootstrap CI 0.8062 - 0.8362) |
| PR-AUC (primary) | **0.5895** |
| Brier score | 0.1042 |
| 5-fold CV AUC on dev | 0.8205 +/- 0.0120 |
| Deployed threshold | **0.10256** (chosen on out-of-fold dev for 80% recall) |
| Precision at deployed threshold | 0.3239 |
| Recall at deployed threshold | 0.8378 |
| F1 at deployed threshold | 0.4671 |
| Accuracy at deployed threshold | 0.6691 |
| Precision / recall at the naive 0.50 cut | 0.7140 / 0.3589 |

**Read this table the right way.** At 0.50 the model is precise and misses two thirds of
cases - useless for screening. At 0.10256 it catches 84% of cases and is wrong on two of
every three flags. That trade is a clinical decision, not a modelling accident, which is
why the threshold is a versioned artefact of the run rather than a constant in the code.

**Why accuracy is never the headline.** A "nobody has CKD" predictor scores 82.3% here.
Quoting 0.6691 accuracy at our operating point without the recall context would make the
model look worse than the do-nothing baseline while being far more useful.

**Selection rule.** PR-AUC first, then ROC-AUC, then the recall constraint. v14 (random
forest) had the best ROC (0.8313) but a lower PR-AUC (0.5628) - the wrong shape for an
imbalanced screening task - so v15 was served.

---

## SECTION 11 - MLFLOW

- Tracking store: file store (`mlruns/`), mirrored into the containers as
  `docker/.mlruns.container/` so MLflow, the API and CI resolve the same artifacts.
- Experiments: `corvus-ckd` (legacy UCI, 9 runs) and `corvus-ckd-nhanes` (6 runs).
- Every run logs: params (full estimator spec), 15 metrics, the fitted `Pipeline`, the
  estimator, an input signature, plus the git commit and source file as tags.
- Stage transitions are real: v15 sits in **Production**; every superseded version is
  **Archived** (verified live, 2026-11-10).

## CLAIM 2 - PIPELINE AND MODEL TRAVEL TOGETHER
Each run stores the `ColumnTransformer` pipeline and the estimator in the same run, so
serving resolves one `run_id` and gets both halves. `api/model_loader.py` then asserts the
pipeline's output width equals the estimator's `n_features_in_` (36) before the service
accepts traffic - a width mismatch is a startup failure, not a bad prediction.

---

## SECTION 12 - MODEL SELECTION AND LIFECYCLE

```
train -> MLflow run (params + metrics + pipeline + model)
      -> registry version (corvus-ckd v10..v15)
      -> challenger evaluated on the forward holdout
      -> human promotion (scripts/promote_challenger.py / promote_production.py)
      -> serving pin (config: api.v2_pinned_version = "15")
      -> superseded version archived
```

- Promotion is a human decision. Nothing auto-deploys to the serving slot.
- The pin is configuration, not a database stage read, so a registry label cannot silently
  change what answers requests.
- Rollback is a one-line config change plus an API restart; history stays attributable
  because old rows still carry their own `model_version`.

---

## SECTION 13 - FASTAPI SERVICE

| Method | Path | Purpose |
|---|---|---|
| POST | `/v2/predict` | NHANES-native single prediction (bearer JWT) |
| POST | `/v2/batch_predict` | All-or-nothing batch, per-row errors (bearer JWT) |
| GET | `/v2/model_info` | Served v2 model identity (`15`, run id, resolution) |
| POST | `/predict`, `/batch_predict` | Legacy UCI v1 slot, pinned v9 |
| GET | `/model_info`, `/health`, `/metrics` | Legacy identity, readiness (reports both pins), Prometheus scrape |
| POST | `/auth/register`, `/auth/login` | Account creation and JWT issue (login throttled) |
| GET | `/auth/me`, `/auth/profile`, `POST /auth/profile` | Identity and clinical profile |
| GET | `/auth/predictions`, `/auth/predictions/{id}` | Server-side prediction history |
| GET/POST | `/doctors/patients`, `/doctors/patients/assign` | Doctor-to-patient mapping |
| GET | `/api/v1/models`, `/{version}/details`, `/compare` | Registry browsing |
| POST | `/api/v1/models/promote` | Promotion endpoint |

- Validation is Pydantic v2: 20 numeric keys required (may be `null`), 3 categorical keys
  required (may be `null`), out-of-vocabulary codes rejected.
- Two slots run side by side, so `/health` reports both pins:
  `{"status":"ok","model_version":"9","model_version_v2":"15"}`. The first is the
  legacy v1 slot that `/predict` still serves; the second is the model the console and
  every `/v2` route use. Reading only `model_version` would suggest the retired UCI
  model is live, which it is not.
- Failure modes are explicit: 401 unauthenticated, 422 schema, 503 database unavailable,
  500 without a stack trace in the body.
- Logging fails closed: if the prediction row cannot be written, the caller gets 500 rather
  than an unattributable answer.

---

## SECTION 14 - PREDICTION VERSIONING (CLAIM 4)

`POST /v2/predict` returns `{"prediction": 0, "probability": 0.0588, "model_version": "15"}`
and the same version string is stored on the `predictions_v2` row. Verified live
2026-11-10 with a 23-key payload (age 58, BMI 27.4, sex 1): probability 0.058789,
decision 0 against the 0.10256 cut, row id 2 for that user, `model_version` `"15"`.

Chain: prediction -> `model_version` -> registry version -> `run_id` -> exact pipeline,
estimator and params. Any historical prediction re-resolves to the model that made it.

---

## SECTION 15 - POSTGRESQL

- PostgreSQL 16 in Compose, database `corvus`, health-gated before the API starts.
- Tables: `users`, profiles, doctor-patient mapping, `predictions` (v1), `predictions_v2`
  (native, 23-field aware).
- Alembic owns the auth/profile tables (`0001`-`0003`). The two prediction tables are
  created by SQLAlchemy `create_all` - a documented deviation, chosen because their shape
  changes with the model contract. Consequence, learned the hard way: `create_all` never
  alters an existing table, so a nullability change needs an explicit drop and recreate.
- Users, profiles and predictions are joined by `user_id`; history is served from the
  database, so clearing the browser does not erase the audit trail.

---

## SECTION 16 - FRONTEND

React 19 + Vite 8 + Tailwind 3 + React Router 7, served by nginx on port 3000, 11 pages.

| Page | Role |
|---|---|
| Clinical login / register | Role select (patient, doctor), JWT stored client-side |
| Assessment dashboard | The NHANES form, grouped by clinical section, posts to `/v2/predict` |
| Result card | Probability, decision, cut-off, `model_version` - the version is visible to the user |
| Prediction history | Server-side list with model version per row |
| Models / model comparison | Registry versions, metrics per version, promotion view |
| Patient and doctor profiles, patient detail, assign patients | Clinical workflow scaffolding |

Design decisions: the UI holds **zero model logic** - no thresholds, no feature engineering,
no fallback scoring. A screening disclaimer is shown wherever a risk is displayed. Deep
links work because nginx rewrites unknown paths to `index.html` (this was a real 404 bug,
fixed with `docker/nginx.conf`).

---

## SECTION 17 - DOCKER AND DEPLOYMENT

| Service | Port | Role |
|---|---|---|
| `frontend` | 3000 | nginx serving the React build, SPA fallback |
| `api` | 8000 | FastAPI + uvicorn, model pinned at startup |
| `db` | 5432 | PostgreSQL 16 with healthcheck |
| `mlflow` | 5000 | Tracking UI and registry API |
| `prometheus` | 9090 | Scrape + rule evaluation |
| `grafana` | 3001 | Dashboards (host 3001 to avoid a local conflict) |
| `alertmanager` | 9093 | Alert routing |
| `airflow` | 8080 | Standalone scheduler/webserver for the retrain DAG |
| `node-exporter` / `postgres-exporter` | 9100 / 9187 | Host and database telemetry |

`docker compose -f docker/docker-compose.yml up -d` brings the whole platform up.
`api/` and `src/` are bind-mounted read-only, so code changes apply on `restart api`
without a rebuild; the frontend needs an image rebuild because Vite output is baked in.

---

## SECTION 18 - TESTING

| Layer | Count | What it proves |
|---|---|---|
| pytest: API contract | 17 in `tests/test_api_v2.py` | 23-field contract, null categoricals imputed, missing key 422, bad literal 422, auth 401, logging round trip |
| pytest: data and label | golden re-derivation test | The cohort and its labels rebuild byte-for-byte |
| pytest: model and pipeline | metric, threshold, artifact tests | Threshold tuning, width assertion, registry helpers |
| pytest: integrations | drift, promote, auth, metrics | Each plugin behaves and fails closed |
| Full suite | **150 passed, 2 skipped** (210 s) | Regression floor |
| Playwright E2E | **5 passed** | Login page, wrong-credential rejection, registration, a real `/v2/predict` round trip appearing in history with v15, models page showing the pinned version |
| CI | GitHub Actions green on `main` | Lint, tests, and the ASCII constraint on `train_nhanes.py` |

The E2E suite is the layer that found real defects: a missing SPA fallback, coded
categoricals sent as strings, a reload that silently logged the user out, and NOT NULL
columns that predated nullable categoricals. Each was fixed with a test pinning it.

---

## SECTION 19 - FORMAL PROJECT CLAIMS

| Claim | Statement | Evidence |
|---|---|---|
| 1 | Labels are derived deterministically from KDIGO criteria, not chart review | Label builder + golden test; 99.9899% agreement with an external labelled set |
| 2 | The preprocessing pipeline and the estimator are versioned together | Same MLflow run holds both; startup width assertion |
| 3 | Evaluation is on a cohort the model never saw | Whole SDDSRVYR cycle held out; no threshold tuning on it |
| 4 | Every prediction is attributable to a model version | Response field, DB column, registry chain - verified live |
| 5 | Retraining is triggered by evidence, not a calendar alone | Five independent triggers in `corvus_drift_retrain` |

---

## SECTION 20 - PHASE HISTORY (honest)

| Phase | What happened |
|---|---|
| 1. Data pipeline | UCI cohort first (400 rows), reproducible ingestion, fail-closed gate |
| 2. Training + MLflow | 9 configs, registry v1-v9, MLP-ReLU champion on a tiny cohort - metrics saturated at 1.000 |
| 3. API + containers | FastAPI, Postgres logging, Compose stack, Streamlit UI |
| 4. CI + monitoring | GitHub Actions, `/metrics`, Prometheus, Grafana, alert rules |
| 5. Airflow + drift | Five retrain triggers, Evidently drift report path, promotion scripts |
| 6. Rebuild on NHANES | Real cohort, forward split, portable-23 contract, honest 0.82 |
| 7. Native retrain | v10-v15 challengers, PR-AUC selection, threshold artefact |
| 8. React console + auth | 11 pages, JWT, roles, profiles, server-side history |
| 9. Stabilisation | E2E suite, SPA fallback fix, nullability fix, registry stages aligned to serving |

The single most valuable event in that list is the moment the 1.000 metrics were abandoned.

---

## SECTION 21 - DRIFT DETECTION AND RETRAINING

Built, not merely planned:

- `src/monitoring/` builds an Evidently data-drift report from a baseline (training
  reference) against incoming production features.
- `airflow/dags/corvus_drift_retrain.py` fires a retrain if **any** of five conditions
  holds: champion older than `schedule_days` (30), drifted-feature share above
  `drift_threshold` (0.3), more than `min_new_rows` (500) unabsorbed production rows,
  labelled-batch ROC-AUC below `roc_floor` (0.80), or a manual trigger.
- A retrain produces a challenger, scores it on the forward holdout, and
  `scripts/promote_challenger.py` promotes only on a genuine improvement.
- Honest limit: with a demo traffic level, the drift trigger has never fired on real
  production drift. The mechanism is exercised, the clinical signal is not.

---

## SECTION 22 - CI/CD AND MONITORING

- CI: lint, full pytest, and a guard that keeps `src/training/train_nhanes.py` pure ASCII
  with no recorded UCI AUC reference. No image publishing - the demo is local-first.
- Metrics: `/metrics` exports `corvus_predictions_total{model_version=...}`, request
  counts and latency histograms.
- Prometheus scrapes three jobs: the API, node-exporter, postgres-exporter. The MLflow job
  was removed because MLflow 3 dropped `/metrics` - a permanently-down target is worse than
  no target.
- Seven alert rules: `APIDown`, `APIHighErrorRate`, `APIHighLatency`, `HighPredictionVolume`,
  `LowPredictionProbability`, `DatabaseConnectionsHigh`, `NoNewUsers`.
- Grafana dashboard is provisioned from `docker/grafana/`, with Prometheus as the default
  datasource.

---

## SECTION 23 - COMPLETE ARCHITECTURE

```
                +---------------------------+
  Browser  ---> | React console (nginx:3000)| ---> /v2/predict (JWT)
                +---------------------------+
                            |
                            v
                +---------------------------+        +----------------+
                | FastAPI (uvicorn:8000)    | -----> | PostgreSQL 16  |
                | pinned corvus-ckd v15     |        | users, logs    |
                +---------------------------+        +----------------+
                     |            |
        /metrics     |            | mlflow.load_model(run_id)
                     v            v
        +----------------+   +--------------------------+
        | Prometheus     |   | MLflow 3 file store      |
        | + Alertmanager |   | experiments + registry   |
        | + Grafana      |   +--------------------------+
        +----------------+              ^
                                        | run logging
                            +--------------------------+
                            | train_nhanes.py (Airflow)|
                            | drift -> retrain -> gate |
                            +--------------------------+
```

---

## SECTION 24 - ENGINEERING PRACTICES

- Fail-closed everywhere it matters: the data gate, prediction logging, model width check,
  missing `SECRET_KEY` at boot.
- Contract tests before behaviour: schema changes come with a test that pins 422 vs 200.
- Honest metrics: PR-AUC primary, confidence intervals, threshold stated, accuracy demoted.
- Reproducibility: seeded estimators, git commit tags on runs, golden data test.
- Deviation log: `create_all` instead of migrations for prediction tables, no Alembic
  `0004` - written down with its consequence rather than left as a surprise.

---

## SECTION 25 - IMPORTANT TECHNICAL DECISIONS

| Decision | Alternative rejected | Why |
|---|---|---|
| Move to a 15k-row NHANES cohort | Keep polishing the 400-row UCI set | Perfect metrics on a curated set prove nothing |
| Forward split on whole cycles | Stratified random split | Random splitting leaks same-cycle rows into training |
| PR-AUC as the selection metric | ROC-AUC alone | ROC flatters models on a 17.7% positive class |
| Recall-tuned threshold artefact | Fixed 0.50 | 0.50 misses two thirds of true cases |
| Portable-23 feature contract | Keep every NHANES column | US-only fields block any non-US deployment |
| Registry version pinned in config | Load "whatever is Production" | A label change must not silently change answers |
| Two serving slots (v1, v2) | Rewrite the v1 contract in place | Keeps the old demo working while the real model ships |
| Screening framing | Diagnostic framing | Precision 0.32 cannot support a diagnosis claim |

---

## SECTION 26 - LIMITATIONS (state these plainly)

1. **Precision 0.324.** Two of three flags are false positives at the operating point. The
   design accepts that to catch 84% of cases - but it is a screening aid, never a diagnosis.
2. **US cohort only.** NHANES is a US sample; transfer to Indian patients is unproven until
   ICKD data arrives.
3. **Unweighted.** Survey weights are deliberately not applied, so prevalence in the sample
   is not a population prevalence estimate.
4. **Single-measure labels.** KDIGO requires persistence over 3 months; a single eGFR/ACR
   reading is a proxy, so some labels are noise.
5. **Feature completeness.** Albumin, uric acid, ALT and RDW are strong contributors, so a
   deployment without those tests loses accuracy.
6. **Drift unproven in production.** The mechanism is built; there is no real traffic yet.
7. **Demo security.** No email verification, no password reset, no refresh-token rotation.

---

## SECTION 27 - FUTURE SCOPE

- External validation on Indian (ICKD) data, then a recalibration pass rather than a retrain.
- Calibration work: the Brier score of 0.1042 can be improved with isotonic calibration on
  the dev set, which would make the probabilities directly usable in cost models.
- Clinician-in-the-loop feedback capture, so precision at the operating point becomes a
  measured number rather than a held-out estimate.
- Survival framing (time to progression) instead of binary screening.

---

## SECTION 28 - FIGURES AND SCREENSHOTS

Captured into `docs/screenshots/` from the running stack:

| # | Figure | Source | What it proves |
|---|---|---|---|
| 1 | Clinical login | `localhost:3000/login` | Two portals, role selection |
| 2 | Assessment dashboard with result | `localhost:3000/dashboard` | Real `/v2/predict` answer, cut-off, `model_version: 15` |
| 3 | Prediction history | `localhost:3000/history` | Server-side rows, v15 stamped |
| 4 | Models page | `localhost:3000/models` | Pinned serving version, registry view |
| 5 | Grafana dashboard | `localhost:3001` | Live scrape, prediction counters |

Additional live-provable items: MLflow experiment table (6 NHANES runs with metrics),
registry stage column (v15 Production, v1-v14 Archived), Prometheus targets page (3 up),
pytest tail (150 passed), Playwright output (5 passed).

---

## SECTION 29 - EXAMINER / VIVA QUESTIONS

**Q: Why is your ROC-AUC only 0.82 when student projects report 0.99?**
A: Because the cohort is real. The 0.99 projects train and test on 300 curated rows from
one small dataset. Corvus evaluates on an entire NHANES cycle it never saw, and the
positive class is 17.7%, not 50%.

**Q: Why gradient boosting and not deep learning?**
A: Tabular labs with mostly monotone relationships: boosted trees capture interactions with
far less tuning. On the dev set the linear baseline was within noise; a small MLP added
cost, not accuracy evidence.

**Q: Why is recall 0.84 but precision 0.32 - is that not a bad model?**
A: It is a deliberate operating point for screening. A false positive costs one confirmatory
test; a false negative costs a missed diagnosis. The 0.50 cut gives 0.71 precision but
misses two thirds of cases.

**Q: How do you know the split is clean?**
A: The holdout is an entire survey cycle, excluded from training, threshold tuning and
feature selection. An earlier version scored unseen rows of a cycle it had partly fitted on
and reported 0.83 - fixing that produced the current 0.8214.

**Q: What happens when a prediction cannot be logged?**
A: The API returns 500. A risk figure nobody can attribute is not served.

**Q: How would a different model version be rolled out?**
A: Promote the version, change `api.v2_pinned_version`, restart the API. Old rows keep
their own version string, so the audit trail stays intact.

**Q: What is not finished?**
A: Drift on real traffic, email verification and password reset, and external validation on
Indian data.

---

## SECTION 30 - TEAM CONTRIBUTION

Fill with the actual split before presenting. Suggested framing, if the work was solo:
data build and label audit; modelling, thresholding and registry; API, database and auth;
React console; containers and observability; test suites and documentation.

---

## SECTION 31 - FINAL 12-14 SLIDE STORYLINE

| Slide | Title | Content |
|---|---|---|
| 1 | Corvus | CKD screening from routine labs; one-line problem |
| 2 | The problem | Silent disease, cheap tests already ordered, no consistent risk scoring |
| 3 | Why existing demos fail | 400-row curated sets, 1.000 metrics, no versioning |
| 4 | Data | Three NHANES cycles, 15,244 adults, 2,696 positives, deterministic KDIGO labels |
| 5 | Leakage discipline | Forward split, whole cycle held out, the 0.83 -> 0.82 correction |
| 6 | Features | Portable-23 contract; what was dropped and what it cost |
| 7 | Model | Depth-3 gradient boosting, why not deep learning |
| 8 | Results | ROC 0.8214, PR-AUC 0.5895, table at deployed and 0.50 thresholds |
| 9 | The threshold is clinical | Recall 0.84 vs precision 0.32, stated openly |
| 10 | Versioning | Registry v10-v15, v15 Production, version on every answer |
| 11 | Platform | FastAPI + Postgres + React + Compose, screenshots |
| 12 | Operations | Prometheus, 7 alerts, Grafana, five retrain triggers |
| 13 | Quality | 150 pytest, 5 E2E, CI green - and the four real bugs E2E found |
| 14 | Limits and next | Precision, US-only cohort, ICKD validation, calibration |

---

## SECTION 32 - FIVE CORE PROJECT SENTENCES

1. Corvus turns a routine blood and urine panel into a CKD risk score a clinician can act on
   and an auditor can trace.
2. Its labels are derived deterministically from KDIGO criteria and independently
   cross-checked at 99.99% agreement.
3. It is evaluated on an entire NHANES cycle it never saw, scoring ROC-AUC 0.8214 and
   PR-AUC 0.5895 - numbers that are honest rather than flattering.
4. It operates at a recall-tuned threshold of 0.10256, catching 84% of cases as a screening
   tool with a stated precision cost.
5. Every prediction carries the exact registry version that produced it, all the way into
   PostgreSQL.

---

## SECTION 33 - PROJECT FACT SHEET

| Field | Value |
|---|---|
| Dataset | NHANES 2015-16, 2017-20, 2021-23 |
| Rows / positives | 15,244 / 2,696 (17.69%) |
| Holdout | Cycle 12 (2021-23), 5,343 rows |
| Features in | 20 numeric + 3 categorical (23) |
| Pipeline width | 36 |
| Model | GradientBoostingClassifier, log_loss, depth 3, 100 trees, seed 42 |
| Served version | `corvus-ckd` v15, run `30830a71...` |
| Holdout ROC / PR-AUC | 0.8214 / 0.5895 |
| Precision / recall at operating point | 0.3239 / 0.8378 |
| Threshold | 0.10256 |
| Registry | v1-v9 legacy UCI archived, v10-v15 native, v15 Production |
| API | 22 routes, dual serving slots, JWT auth |
| Frontend | React 19, 11 pages, nginx |
| Observability | 3 scrape targets, 7 alert rules, 1 provisioned dashboard |
| Retraining | Airflow DAG, 5 triggers |
| Tests | 150 pytest passed / 2 skipped, 5 Playwright E2E passed |

---

## SECTION 34 - FINAL CONSISTENCY AUDIT

Verified on 2026-11-10 against the running stack:

- `/v2/model_info` -> version `15`, run `30830a7152394ff2a63ea1005da9f035`,
  `resolution: pinned-at-startup`.
- `POST /v2/predict` with a 23-key payload -> 200, probability 0.058789, `model_version`
  `"15"`; the row appears in `GET /auth/predictions` with the same version.
- MLflow registry: 15 versions; v15 in Production, all others Archived.
- Prometheus: 3/3 targets up; 7 alert rules loaded.
- Grafana: healthy, dashboard provisioned, Prometheus default datasource.
- pytest: 150 passed, 2 skipped. Playwright: 5 passed.

Anything in this document that conflicts with those six checks is wrong - the stack wins.

---

## SECTION 35 - SAFE FACTS VS UNSAFE CLAIMS

**Safe to say**
- "ROC-AUC 0.8214 on a held-out NHANES cycle" (quote the cohort).
- "Screening tool with a recall-tuned threshold."
- "Versioned, attributable predictions."
- "150 tests and an E2E suite that found four real defects."
- "Retraining triggers are implemented."

**Do not claim without extra evidence**
- Any accuracy above 0.85 as a headline (0.6691 at the operating point; 0.82 prevalence
  baseline makes accuracy meaningless).
- "Diagnoses CKD." It scores risk.
- "Works on Indian patients." Untested; ICKD data pending.
- "Deployed to production users." The demo is local Compose.
- "Drift detection validated." The mechanism exists; production drift has not occurred.
- Any 1.000 metric. Those were the retired UCI proof of concept.

---

## SECTION 36 - FINAL EXECUTIVE SUMMARY

Corvus is a complete CKD screening platform: a reproducible multi-cycle cohort, a
deterministic KDIGO label with quarantine discipline, a portably-scoped feature contract, a
tracked and versioned gradient-boosting model, a versioned API with authentication, a React
console, and the operational layer - metrics, alerts, dashboards, retraining triggers -
that separates a demo from a system. The model is deliberately not oversold: 0.8214 ROC-AUC
and 0.5895 PR-AUC on data it never saw, served at a threshold that catches 84% of cases as a
screening aid. Its weakest number, precision 0.324, is printed next to its strongest one
everywhere it appears, because that is the number a clinician has to live with. The next
real improvement is not a better estimator; it is Indian patient data.
