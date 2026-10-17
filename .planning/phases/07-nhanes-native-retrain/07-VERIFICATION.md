---
phase: 07-nhanes-native-retrain
verified: 2026-10-17T00:00:00Z
status: passed
score: 12/12 automated must-haves + 2/2 human verification items passed
---

# Phase 07: NHANES-Native Retrain — Verification Report

**Phase goal:** NHANES-native pipeline + 9 configs on 5,343 derived rows with CV + CIs + locked holdout; challenger vs v9 under the paired harmonized-holdout protocol; human-gated promotion executed (v11 Production); /v2 endpoints serving the challenger while v1 untouched.

**Plans verified:** 07-01-PLAN.md + 07-02-PLAN.md + 07-03-PLAN.md (must_haves from all three) against the actual codebase.
**Method:** goal-backward. Ran `.\venv\python.exe -m pytest tests -q` (74 passed, 0 failed), live MLflow registry probe (v11 Production / v9 Archived), live v2 artifact load + TestClient probes (`/v2/model_info` 200 version 11; `/v2/predict` inference ran with version '11' stamped; unconfigured state 503 fail-closed).

## Must-Haves

| # | Source | Must-have truth | Status | Evidence (file:line) |
|---|--------|-----------------|--------|----------------------|
| 1 | 07-01 | One NHANES-native config (LR) trains end-to-end on the locked derived CSV; single MLflow run tagged schema=nhanes-native, pipeline + model co-logged | ✓ VERIFIED | `src/training/train_nhanes.py:244` (`run_experiment_native`); live run `763555da` FINISHED under `corvus-ckd-nhanes` (SUMMARY-claimed, registry lineage v10 run id matches probe: v10 run=763555da); `tests/test_nhanes_training.py` `test_claim2_native` passes (in 74-green suite) |
| 2 | 07-01 | Any of the 11 quarantined columns in the training frame aborts training before any split or fit | ✓ VERIFIED | `src/preprocessing/preprocess_nhanes.py:29` (`QUARANTINE_11`), `:61` (`assert_quarantine` raises SystemExit), gated before `locked_holdout_split` in `train_nhanes.py:244+`; `test_quarantine_aborts` passes |
| 3 | 07-01 | Locked 20% holdout shares zero row indices with any fitted data | ✓ VERIFIED | `src/preprocessing/preprocess_nhanes.py:133` (`locked_holdout_split`, seed 42, stratify); `test_holdout_disjoint` passes |
| 4 | 07-01 | Every logged/reported metric carries the derived-label disclosure string | ✓ VERIFIED | `src/preprocessing/preprocess_nhanes.py:47` (`DERIVED_LABEL_DISCLOSURE`); tags on runs + printed next to metrics; suite green |
| 5 | 07-02 | All 9 configs (6 classical + MLP sigmoid/tanh/relu) train on native schema with stratified 5-fold CV on dev + bootstrapped CIs, no leakage | ✓ VERIFIED | `src/training/train_nhanes.py:62` (`NATIVE_ESTIMATORS` 9 entries), `:161` (`run_cv_native`, StratifiedKFold 5, fresh pipeline per fold, dev-only), `:195` (`bootstrap_auc_ci`, 2000 reps, seed 42); `test_cv_determinism` passes; live sweep: GB CV-mean 0.8203, holdout 0.8265 |
| 6 | 07-02 | Challenger vs v9 on identical locked holdout rows + identical derived labels; promotion iff challenger ROC-AUC strictly greater (paired bootstrap diff CI, never cross-dataset) | ✓ VERIFIED | `src/evaluation/evaluate_nhanes.py:55` (`paired_bootstrap_diff`), `:84` (`compare_challenger`, strict-greater), `:107` (`apply_challenger_stages`); `test_paired_comparison_same_rows_same_labels` passes; live: 0.8265 vs 0.5479, diff CI [0.2239, 0.3349], qualifies=True; no `uci` reference in source (word-boundary scan test passes) |
| 7 | 07-02 | Challenger versions append under corvus-ckd as v10+ in Staging; nothing reaches Production without the human gate | ✓ VERIFIED | `scripts/promote_challenger.py` requires `--version` (help verified live); registry probe: v10 Archived (superseded tracer), v11 Production only after recorded APPROVAL; `apply_challenger_stages` Production guard (`evaluate_nhanes.py:107`) + `test_production_guard` passes |
| 8 | 07-02 | Harmonization adapter is eval-only and unreachable from serving code | ✓ VERIFIED | `src/training/harmonize_v9.py` exists (NHANES_TO_UCI_MAP, read-only v9 load, no `fit`); `Select-String 'api\*.py' -Pattern 'harmonize'` returns empty; `test_adapter_not_served` passes |
| 9 | 07-03 | POST /v2/predict + /v2/batch_predict accept native-schema requests, validate strictly, return versioned predictions with model_version stamped | ✓ VERIFIED | `api/schemas.py:57` (`CKDRequestNative`), `:93` (`NativeBatchItem`); `api/app.py:300+` (/v2 routes); live TestClient: `/v2/model_info` 200 `{"model_version":"11","run_id":"5954f069…"}`, `/v2/predict` inference ran probability 0.9971 with log row stamped `'11'` (500 only from in-memory-sqlite missing table, not inference); 15 v2 tests pass incl. 422 strictness, 413 caps, all-or-nothing naming |
| 10 | 07-03 | v1 /predict /batch_predict /health /model_info byte-identical behavior, still serving pinned v9 | ✓ VERIFIED | `config/config.yaml:58` (`pinned_version: "9"` unchanged); `tests/test_api.py` 19 tests pass unchanged inside the 74-green suite; v1 loader `load_serving_artifacts` untouched (`api/model_loader.py:82`) |
| 11 | 07-03 | Every v2 prediction logs model_version per row to a store that never shares a table with v1 | ✓ VERIFIED | `api/db.py:77` (`PredictionLogV2`, `__tablename__ = "predictions_v2"`); v1 `PredictionLog`/`predictions` untouched; live probe log row carried `model_version '11'` + native fields + timestamp |
| 12 | 07-03 | With no approved challenger pin, /v2 routes fail closed 503 naming the missing configuration | ✓ VERIFIED | `api/app.py:116` (`_require_v2`); `api/model_loader.py:133` (`resolve_v2_version`, env-wins else config, `""` default at `config/config.yaml:61`); live probe: default config → `/v2/model_info` 503 naming `api.v2_pinned_version`; `MODEL_VERSION_V2=11` → 200 (deploy-time cutover path proven) |

**Score:** 12/12 automated must-haves verified. No gaps. No stubs/anti-patterns found in phase files (grep for TODO/FIXME/placeholder/empty-return across `src/preprocessing/preprocess_nhanes.py`, `src/training/train_nhanes.py`, `src/training/harmonize_v9.py`, `src/evaluation/evaluate_nhanes.py`, `api/*`, `scripts/promote_challenger.py`: clean).

## Requirements Traceability (PLAN IDs × .planning/REQUIREMENTS.md)

Every requirement ID declared in the three PLAN frontmatters is accounted for. Note: the plans phase-scope the global FR numbers to native-retrain work; mapping below ties each to its global REQUIREMENTS.md text and the native evidence.

| Req ID | REQUIREMENTS.md text (short) | Claimed by | Status | Evidence |
|--------|------------------------------|------------|--------|----------|
| FR-2.1 | Train ≥ LR, RF, XGB, LGBM, MLP (sig/tanh/relu) | 07-01, 07-02 | ✓ SATISFIED (native-scoped) | 9-config `NATIVE_ESTIMATORS` (`train_nhanes.py:62`): LR + tree + RF + GB + XGB + LGBM + 3 MLP activations; exact-set + seed tests pass; live 9-CV-line sweep |
| FR-2.2 | Log accuracy, precision, recall, F1, ROC-AUC per run | 07-01, 07-02 | ✓ SATISFIED | 5 metrics + `holdout_roc_auc` + CV mean/SD + CI bounds in Claim-2 runs; `test_claim2_native` asserts all 5 names |
| FR-2.3 | Log pipeline + model in same run (Claim 2) | 07-01, 07-02 | ✓ SATISFIED | `preprocessing_pipeline_nhanes.joblib` + model co-logged; `test_claim2_native` asserts preprocessing artifact entry |
| FR-2.4 | Compare all; best by ROC-AUC | 07-02 | ✓ SATISFIED | `select_by_cv` strict-max on CV-mean; GB 0.8203 wins; `aggregate_cv` |
| FR-2.5 | Register best to Registry | 07-02 | ✓ SATISFIED | Winner registered v11; registry probe confirms v11 exists (now Production) |
| FR-3.1 | Registry with Staging/Production/Archived | 07-02 | ✓ SATISFIED | Registry probe: 11 versions with stages (v11 Production, rest Archived) |
| FR-3.2 | Version tracking for all registered models | 07-02 | ✓ SATISFIED | v1–v11 all present, run ids intact, zero deletions |
| FR-3.3 | Promote/demote between stages | 07-02 | ✓ SATISFIED | `promote_challenger.py --version 11` executed on approval; PROMOTED audit line; v11→Production, v9→Archived, artifacts intact |
| FR-4.1 | Endpoints /predict /batch_predict /health /model_info | 07-03 | ✓ SATISFIED | v1 four endpoints untouched + green; v2 `/v2/predict`, `/v2/batch_predict`, `/v2/model_info` live (200/503 probed) |
| FR-4.2 | Pydantic request/response validation | 07-03 | ✓ SATISFIED | `CKDRequestNative` int-Literal categoricals + nullable numerics; 422/413 tests pass |
| FR-4.3 | Log model_version per prediction (Claim 4) | 07-03 | ✓ SATISFIED | `predictions_v2` rows carry `model_version`; live row stamped `'11'`; v1 stamping unchanged |

Orphan check: REQUIREMENTS.md maps no other IDs to Phase 7 beyond these 11; FR-2.1–FR-2.3 are opened in 07-01 and completed across 07-01/07-02 per plan headers — consistent. No orphaned IDs.

## Live Verification Log (commands run, project root)

1. `.\venv\python.exe -m pytest tests -q` → **74 passed, 0 failed** (94s).
2. Registry probe (`MLFLOW_ALLOW_FILE_STORE=true`): v1–v8 Archived, v9 Archived (run 10ac3e5e), v10 Archived (run 763555da, tracer), **v11 Production (run 5954f069)** — promotion executed, nothing deleted.
3. `data/nhanes/nhanes_ckd_derived.csv` shape **(5343, 177)** — 5,343-row cohort confirmed.
4. `load_v2_artifacts("11")` → GradientBoostingClassifier, width 30 == n_features_in_ 30; 5 real NHANES rows score (probas 0.0245–0.1775).
5. TestClient, default config: `GET /v2/model_info` → **503** naming `api.v2_pinned_version` (fail-closed ✓).
6. TestClient, `MODEL_VERSION_V2=11`: `GET /v2/model_info` → **200** `model_version 11, run 5954f069`; `POST /v2/predict` → inference OK (p=0.9971, version '11' in log row; HTTP 500 solely from in-memory-sqlite lacking `predictions_v2` — Postgres `create_tables` path is test-pinned, not a serving defect).
7. `Select-String 'api\*.py' -Pattern 'harmonize'` → empty (serving isolation ✓). `promote_challenger.py --help` → required `--version` ✓.

## Known Honest Caveats (from SUMMARIES, confirmed, not gaps)

- `api.v2_pinned_version` stays `""` in `config.yaml` by design (keeps `test_api.py` hermetic); production cutover is the deploy-time `MODEL_VERSION_V2=11` flip — path proven in probe 6.
- v9's harmonized 0.5479 is a mode/median-fill handicap artifact, valid only inside the paired-protocol framing — never quoted otherwise.
- `predictions_v2` categoricals are `String(16)` vs int request codes; Postgres casts on INSERT (test-pinned); stringify in `_log_predictions_v2` if a strict store ever rejects.
## Human Verification — Completed

### 1. Live /v2 prediction with version stamp (deployed environment) — PASSED

**Test:** With `MODEL_VERSION_V2=11` and Postgres `DATABASE_URL` set, `POST /v2/predict` a native-schema row.
**Result:** 200 `{"prediction":1,"probability":0.892,"model_version":"11"}` against the live compose stack at http://127.0.0.1:8000. Row written to `predictions_v2` in Postgres.

### 2. Registry Models tab shows v11 Production — PASSED

**Test:** Confirm `corvus-ckd` v11 = Production, v1–v10 = Archived, 11 versions total.
**Result:** MLflow API probe: v1–v10 Archived, v11 Production (run 5954f069), 11 versions total, zero deletions. Matches API `/v2/model_info` (`model_version: "11"`, run `5954f06965324f3e954f363c7c691a48`).

## Gaps Summary

None. All 12 automated must-haves + 2 human verification items verified against the deployed stack (suite green, registry state confirmed, /v2 serving live). Status is `passed`.

---

_Verified: 2026-10-17T00:00:00Z_
_Verifier: human + agent_
