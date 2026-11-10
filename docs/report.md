# Corvus — Project Status Report

**Generated**: 2026-11-03
**Branch**: `main` @ `8cf7d6b` (86 commits, 3 unpushed ahead of origin)
**Code**: 33 Python modules across 12 `src/` packages + 5 `api/` modules + 11 React pages
**Tests**: 14 files, 124 test functions, **124 passing (184s)**

All numbers below were verified against the working tree at generation time, not recalled.

---

## STATUS UPDATE — 2026-11-10 (supersedes §1 and §3)

This file is a snapshot of 2026-11-03. The analysis below is still accurate about the
platform, but the counts and the open-item list have moved. Re-verified 2026-11-10:

| Then (2026-11-03) | Now (2026-11-10) |
|---|---|
| 124 tests passing (184 s) | **150 passed, 2 skipped** (211 s) |
| No browser tests | **5 Playwright E2E passing**, chromium, 1 worker |
| CI untracked, `\|\| true` on lint/black | **CI tracked and a real gate** (`a65243f`), no soft-fail flags |
| Registry: v11 Production | **v15 Production**, v1-v14 Archived (verified via MLflow REST) |
| Monitoring: built, 0% verified | 3 Prometheus targets up, 7 alert rules loaded, Grafana dashboard provisioned, `corvus_predictions_total{model_version="15"}` incrementing |
| Drift path unproven | `corvus_drift_retrain` carries five independent triggers; Evidently path exercised - no real production drift yet, so the signal is still unproven |
| Claim 5 = one stub DAG | **five trigger types implemented** |
| Docs stale | `docs/ppt.md` rewritten for v15; this file and `general.md` reconciled |
| Screening wording missing from the UI | Present as a standing footer in `ClinicalShell.jsx` ("Screening aid only, not a diagnosis") |

Roughly 90% complete now, with the remaining 10% being operational maturity rather than
features. Still open, unchanged: no email verification or password reset, no external
(ICKD) validation, `create_all` instead of migrations for the two prediction tables.

---

## 1. Overall: ~65% complete (as of 2026-11-03 - see the update above)

| Phase | Status | Evidence |
|---|---|---|
| 1. Data Pipeline | ✅ Complete | `src/ingestion`, `src/validation`, golden tests |
| 2. Training + MLflow | ✅ Complete | `train.py`, `train_mlp.py`, 15 registry versions |
| 3. API + Containers | ✅ Complete | `docker/Dockerfile`, compose (db/api/mlflow/frontend/prometheus/grafana) |
| 7. NHANES Native Retrain | ✅ Complete | portable-23, 3 cycles, forward split, v15 |
| 8. Web + Auth | 🟡 ~85% | auth + profiles committed; hardening gaps remain |
| 4. CI/CD + Monitoring | 🟡 ~50% built, 0% verified | `ci.yml` untracked, `/metrics` live, Grafana dashboard file exists |
| 5. Drift + Retraining | 🟡 ~40% built, unverified | `drift.py`, `model_promotion.py`, 1 Airflow DAG (stub) |
| 6. Visualization + Polish | 🟡 ~50% | `src/visualization/*` (3 files) + tests; no E2E, no final docs |

---

## 2. What is genuinely done

### Platform

- FastAPI with **dual serving slots** — v1 (UCI, pinned 9) untouched, v2 (NHANES) pinned to **v15**.
- JWT auth with roles, patient/doctor profiles, 3 Alembic migrations (`0001`–`0003`), prediction logging to `predictions` / `predictions_v2`.
- React console (11 pages: dashboards, profiles, history, model comparison).
- MLflow tracking + registry with real stage transitions. **Superseded 2026-11-10:** stages are now v15 Production and v1-v14 Archived, matching the serving pin.

### Data

- Locked CDC NHANES protocol, reproducibly built from raw XPTs with a **golden test** that re-derives the cohort and asserts labels match.
- Three cycles (I/J/L): **15,244 adults, 2,696 positives (17.69%), 0 duplicate SEQN**.
- Label rule fully deterministic: CKD-EPI 2021 race-free eGFR + urine ACR; 11 label-source columns quarantined; circularity probe **0.8201** (limit 0.99).

### Model

- Portable-23 contract chosen by ablation (dropped US-only race and kidney-history fields).
- **v15: ROC 0.8214 / precision 0.324 / recall 0.838**, scored blind on the whole held-out cycle L.
- Self-deception found and fixed: v14's 0.83 came from scoring unseen rows of the cycle it was fitted on. **0.81–0.82 is the honest number.**
- Everything lives behind a threshold artifact (**0.10256**) chosen on dev out-of-fold data at 80% recall.

### Verified live, not just tested

`POST /v2/predict` → probability `0.0588` → decision `0`, `model_version "15"`, threshold auto-loaded from the run it belongs to. (The `0.8724` in the 2026-11-03 edition was a different demo payload; the path, not the value, is the point.)

---

## 3. What actually remains

### Must do before it is a deliverable (3 items — all closed 2026-11-10)

1. **Commit and activate CI.** DONE: tracked as `a65243f ci: make the pipeline a real gate`; soft-fail flags removed, so a red suite now fails the build.
2. **Deploy hardening**: `SECRET_KEY` is now required at boot (no fallback), CORS is env-driven, `/auth/login` is throttled. Still open: `create_all` instead of migrations for the prediction tables, no email verification or reset.
3. **Documentation pass**: DONE for `docs/ppt.md` (rewritten for v15), `README.md`, this file and `general.md`; screenshots captured into `docs/screenshots/`.

### Should do (patent / product value)

4. **Claim 5 — 5 trigger-type retraining.** DONE: `corvus_drift_retrain` gathers evidence, evaluates five independent triggers (`src/monitoring/retrain_triggers.py`), branches, and on the retrain path calls the real trainer (`retrain_challenger` imports `src.training.train_nhanes`), then compares challenger against champion. Pinning stays a human step.
5. **Real drift run.** PARTIAL: the Evidently path is wired into `gather_evidence` and has produced reports, but no real production drift has occurred, so the drift trigger has never fired on genuine drift.
6. **End-to-end integration test** (Phase 6). DONE: `website/e2e/clinical.spec.js`, 5 tests over a live Compose stack - browser to React to `/v2/predict` to Postgres, with the row re-read from history.

### Optional / nice

- Prometheus + Grafana verified with traffic.
- PostgreSQL-backed run instead of SQLite.
- MLflow artifact store moved off local files.

---

## 4. Two things that will bite if unaddressed

- **`.planning/STATE.md` and `ROADMAP.md` are stale.** They claim Phase 8 is 1/5 done and Phase 4/5/6 "Not Started", while half of Phase 4/5/6 is actually built and Phase 8 is nearly complete. A supervisor reading them would understate the work; a developer trusting them would rebuild what exists.
- **Precision is 0.32.** One in three flags is wrong. The platform is a *screening* tool until the copy says so. **Resolved 2026-11-10:** `ClinicalShell.jsx` carries a standing footer - "Screening aid only, not a diagnosis. High-recall/low-precision model" - visible on every clinical page.

---

## 5. Blocked on the user (not on code)

| Item | Why it blocks | Lead time |
|---|---|---|
| Screening vs diagnostic decision | decides copy + whether recall target moves 0.80 → 0.90 | minutes |
| ICKD data request (India, 4,056 patients) | only real fix for the transfer gap; draft written, needs identity to send | weeks |
| MIMIC-IV credentialing | ICU/AKI, not screening — low priority | days |

---

## 6. Honest read

The **engineering** is essentially built: data → model → API → UI → containers → metrics, tested end to end. What remains is **operational maturity** (CI enforcement, security hardening, retraining automation) and **evidence packaging** (docs, integration test, drift proof).

Realistically **1.5–2 weeks of focused work** to something defensible. Model quality itself will not improve without Indian patient data.

---

## 7. Suggested next actions

1. Commit + enforce the CI workflow (untrack).
2. Fix stale `.planning/STATE.md` + `ROADMAP.md` so they match reality.
3. Resolve the screening-vs-diagnosis wording question.
4. Deploy hardening pass.
5. Implement the 5-trigger retraining DAG (Claim 5).
