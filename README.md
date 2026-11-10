# Corvus

An end-to-end MLOps platform for automated training, deployment, and monitoring
of disease-prediction models, with Chronic Kidney Disease (CKD) as the pilot use
case: raw NHANES survey data -> leakage-audited cohort build -> tracked training
runs -> a versioned model registry -> a prediction API -> a React clinical
console -> Prometheus/Grafana monitoring -> drift-triggered retraining.

Every number below was read off the running stack. Where something is not
proven, it says so.

## Status

- [x] Phase 1 - Data pipeline and quality gates
- [x] Phase 2 - Experiment tracking and model training (MLflow)
- [x] Phase 3 - Prediction API and containers
- [x] Phase 4 - CI/CD and monitoring (GitHub Actions, Prometheus, Grafana, Alertmanager)
- [x] Phase 5 - Drift detection and retraining DAG (Airflow standalone; triggers wired, no production signal consumed yet)
- [x] Phase 6 - Visualization (React console, 11 pages) and Grafana dashboard
- [x] Phase 7 - NHANES-native retrain (v15, the served model)
- [x] Phase 8 - Web platform with JWT auth and per-user prediction history
- [x] Phase 9 - Stabilisation: browser E2E suite, docs reconciled with the served model

## Quickstart

Requirements: Docker Desktop (with Compose v2), and ~6 GB of free disk.

```bash
git clone https://github.com/Lalitkhavale12/Corvus.git
cd Corvus
cp .env.example .env          # Windows: Copy-Item .env.example .env
docker compose -f docker/docker-compose.yml up -d --build
```

The API refuses to start without `SECRET_KEY`, which is why `.env` is a required
step. First build takes a few minutes; afterwards the stack comes up in under a
minute.

| Service | URL | Notes |
|---|---|---|
| Clinical console | http://localhost:3000 | React + Vite, served by nginx |
| API docs | http://localhost:8000/docs | Swagger UI |
| MLflow | http://localhost:5000 | 15 registered versions |
| Prometheus | http://localhost:9090 | 3 scrape targets, 7 alert rules |
| Grafana | http://localhost:3001 | `admin` / `corvus-grafana`, dashboard `corvus-api` |
| Alertmanager | http://localhost:9093 | |
| Airflow | http://localhost:8080 | standalone; drift + retrain DAG |

Register an account in the console (or `POST /auth/register`) to sign in and
submit an assessment. Emails must be real-format domains such as
`example.com`; the schema rejects `.local` and other reserved names.

## What is being served

`/v2/*` serves the NHANES-native model. `/model_info` and `/health` pin the
version at startup, so the served identity cannot change under a live process.

| Property | Value |
|---|---|
| Registered model | `corvus-ckd` **version 15**, stage `Production` |
| Run | `30830a7152394ff2a63ea1005da9f035` |
| Algorithm | GradientBoostingClassifier (`lr=0.1`, `max_depth=3`, `n_estimators=100`) |
| Inputs | 23 native fields (20 numeric + `RIAGENDR`, `DMDEDUC2`, `DIQ010`) |
| Training cohort | 15,244 adults, 17.69% positive, cycles 9/10/12 |
| Split | holdout = whole cycle 12 (5,343 rows); dev = 9,901 rows, 5-fold CV |
| Holdout ROC-AUC | **0.8214** (95% CI 0.8062-0.8362) |
| Holdout PR-AUC | **0.5895** (primary metric; 82.3% accuracy is the majority-class baseline, so accuracy is never the headline) |
| Precision / recall | 0.3239 / 0.8378 at the tuned threshold 0.10256 |
| Brier score | 0.1042 |

A second, legacy slot stays live for backward compatibility: `/predict` and
`/model_info` serve the original UCI-trained v9 model on its 24-field contract,
and `/health` reports both pins (`model_version` = v9, `model_version_v2` = 15).
The console uses `/v2` exclusively.

The label is derived, not copied: CKD-EPI 2021 race-free eGFR < 60 **or** urine
ACR >= 30. An independent re-derivation from a separately supplied NHANES
extract agreed on 9,900 of 9,901 shared rows, the one disagreement being an ACR
of 29.996 rounded to 30.0. All 11 label-source columns are quarantined from the
feature matrix, and a circularity probe scores 0.8201 against a 0.99 limit.

## Verify it yourself

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v2/model_info
curl http://localhost:8000/metrics | findstr corvus_predictions_total   # Windows
curl http://localhost:8000/metrics | grep corvus_predictions_total      # Unix
```

`/v2/predict` and `/v2/batch_predict` require a bearer token, so an
unauthenticated call returns 401 by design. A fuller end-to-end check (the
values below are a real 62-year-old profile and return `prediction: 1`):

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo1234!","full_name":"Demo","role":"patient"}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo1234!"}'
# -> {"access_token": "...", "token_type": "bearer"}
```

Save this as `payload.json` (all 23 native fields; any key may be `null` to
mean "not measured", but the key itself must be present):

```json
{
  "RIDAGEYR": 62, "INDFMPIR": 2.4, "LBDSBUSI": 18, "LBDSGLSI": 110,
  "LBXSNASI": 140, "LBXSKSI": 4.1, "LBDSCASI": 9.4, "LBDSPHSI": 3.6,
  "LBXHGB": 13.5, "LBXHCT": 40, "LBXWBCSI": 7.2, "LBXRBCSI": 4.6,
  "LBXGH": 6.1, "BMXBMI": 27.5, "BPXOSY1": 130, "BPXODI1": 80,
  "LBXRDW": 13.2, "LBDSUASI": 5.5, "LBXSAL": 4.1, "LBXSGTSI": 28,
  "RIAGENDR": 2, "DMDEDUC2": 5, "DIQ010": 1
}
```

```bash
curl -X POST http://localhost:8000/v2/predict \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

`RIAGENDR`, `DMDEDUC2` and `DIQ010` are NHANES-coded, not text: `2` = female,
`1` = male; `DMDEDUC2` is 1-5 or 9 for "don't know"; `DIQ010` is 1 = yes,
2 = no, 3 = borderline. An out-of-vocabulary code returns 422 before inference.

The response carries `prediction`, `probability`, and `model_version`, and the
row is persisted to `predictions_v2` so it shows up in the console history and
in `GET /auth/predictions`.

## Testing

```bash
python -m pytest tests -q                    # 150 passed, 2 skipped (~3 min)
cd website && npm install && npm run e2e     # 5 browser tests, stack must be up
```

The Playwright suite drives the real console against the running compose stack
(no fixture server, no mocked API), covering both login portals, bad
credentials, registration, an end-to-end prediction landing in history, and the
models page reporting the served version.

CI (`.github/workflows/ci.yml`) runs the API suite on every push and is green on
`main`.

## Repository layout

```
Corvus/
  api/                FastAPI app: routes, schemas, DB models, auth, metrics
  src/                ingestion, preprocessing, feature engineering, training,
                      evaluation, prediction, monitoring, deployment, auth
  website/            React 19 console (11 pages) + Playwright E2E suite
  docker/             compose stack, Dockerfiles, nginx, Prometheus rules,
                      Grafana provisioning, .mlruns.container (tracked registry mirror)
  airflow/dags/       drift detection -> retrain -> compare -> promote DAG
  config/             config.yaml (dataset, splits, thresholds, monitoring)
  data/               NHANES protocol + committed training cohort CSV
  tests/              pytest suite
  scripts/            promotion and registry helpers
  docs/               report, slide deck, guides, screenshots
  reports/, logs/     generated artifacts
```

## Datasets

- **Served model**: NHANES 2017-2020 pre-pandemic (`DEMO_I/J/L`, `BIOPRO_I/J/L`,
  `BMX`, `BPX`, `CBC`, `ALB_CR`, `DIQ`, `GHB`). The 2.3 MB finished cohort
  (`data/nhanes/nhanes_ckd_multi.csv`) is committed, so training is reproducible
  without downloading ~40 MB of XPT files; `data/nhanes/NHANES_PROTOCOL.md`
  records how it was built.
- **Legacy/eval only**: the UCI CKD cohort (~400 rows, 24 features) backs the v1
  slot and the backward-compatibility tests.

## Known limitations

- **A screening aid, not a diagnosis.** Recall is deliberately high and
  precision low: the model flags candidates for a clinician, it does not rule
  disease in or out.
- **Data ceiling.** The cohort caps out around ROC-AUC 0.82. Improving on that
  needs Indian population data, which is the next external input, not more
  tuning; model deltas under 0.02 AUC are noise at this sample size.
- **Drift retraining is wired but unproven.** The five trigger types and the
  Airflow DAG exist and run, but no production traffic has produced a real
  drift signal yet.
- **Dev-grade secrets and credentials.** `.env` values, the Grafana password,
  and the Postgres password are local-demo defaults and must be replaced before
  anything is exposed publicly.
- **Not load-tested.** Throughput and concurrency behaviour are unmeasured.

## Documentation

- `docs/ppt.md` - presentation dossier: architecture, results, decisions,
  limitations, viva Q&A (start here)
- `docs/report.md` - project report and current status
- `docs/general.md` - phase log and design notes
- `docs/CORVUS_FINAL_GUIDE.md` - the original Phase-1 plan (historical; banner
  explains what was built instead)
- `docs/dataset_requirements.md` - dataset selection, label derivation, and the
  independent cross-check
- `docs/screenshots/` - console and dashboard captures
