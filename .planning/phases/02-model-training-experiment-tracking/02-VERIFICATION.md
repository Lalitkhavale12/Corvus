---
phase: 02-model-training-experiment-tracking
verified: 2026-09-21T21:30:00Z
status: human_needed
score: 6/6 must-haves verified
covered_files:
  - .planning/phases/02-model-training-experiment-tracking/02-01-PLAN.md
  - .planning/phases/02-model-training-experiment-tracking/02-02-PLAN.md
  - .planning/phases/02-model-training-experiment-tracking/02-01-SUMMARY.md
  - .planning/phases/02-model-training-experiment-tracking/02-02-SUMMARY.md
  - .planning/REQUIREMENTS.md
  - src/training/train.py
  - src/training/train_mlp.py
  - src/evaluation/evaluate.py
  - tests/test_training.py
  - tests/test_registry.py
  - tests/conftest.py
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open MLflow UI (mlflow ui --backend-store-uri mlruns) and confirm experiment corvus-ckd shows 9 runs with 5 metrics + artifacts each"
    expected: "9 runs (logistic-regression, decision-tree, random-forest, gradient-boosting, xgboost, lightgbm, mlp-sigmoid, mlp-tanh, mlp-relu), each with accuracy/precision/recall/f1/roc_auc and preprocessing artifact + linked model"
    why_human: "UI rendering and artifact browsability cannot be verified programmatically; API-level store state was verified (see evidence)"
  - test: "Check MLflow UI Models tab for registered model corvus-ckd"
    expected: "9 versions; v9 (mlp-relu) in Staging, v1-v8 in Archived, nothing in Production"
    why_human: "Registry tab rendering needs eyes; client-level stage state was verified (1 Staging / 8 Archived / 0 Production)"
---

# Phase 02: Model Training & Experiment Tracking Verification Report

**Phase Goal:** Trained models logged to MLflow, best model registered — 9 configs (LR, DT, RF, GB, XGB, LGBM + MLP Sigmoid/Tanh/ReLU), 5 metrics per run, pipeline+model artifacts in the same run (Claim 2), winner by test ROC-AUC in Staging, every run versioned, superseded Archived, Production untouched.
**Verified:** 2026-09-21T21:30:00Z
**Status:** human_needed (all automated checks pass; 2 UI-only eyeball items remain)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LR trains end-to-end from train_raw.csv through pipeline into one MLflow run with params, 5 metrics, pipeline artifact + model (02-01 tracer) | ✓ VERIFIED | `src/training/train.py:117-153` run_experiment; live store holds `logistic-regression` run with 5 metrics; `test_run_logs_pipeline_and_model` passes |
| 2 | Winner ranked by strict max test ROC-AUC (proba-based), winner to Staging, superseded to Archived, never Production | ✓ VERIFIED | `src/evaluation/evaluate.py:49-51` select_winner, `:68-84` apply_registry_stages; live Registry: v9 Staging, v1-v8 Archived, 0 Production; `test_winner_is_strict_max_roc_auc`, `test_stage_transitions`, `test_no_production_transition` pass |
| 3 | Full pytest suite stays green | ✓ VERIFIED | Executed `.\venv\python.exe -m pytest tests -q` from project root: **26 passed** |
| 4 | All 9 configs train with library defaults + fixed seeds + one rationale each, no grid search | ✓ VERIFIED | `src/training/train.py:49-62` 6 seeded classical entries with rationale comments; `src/training/train_mlp.py:42` ACTIVATIONS, `:55-60` seeded MLP factory; grep for GridSearchCV/RandomizedSearch/verbose=/seed= clean; `test_all_nine_configs_construct` + `test_mlp_activations_valid` (incl. 6+3=9 count) pass |
| 5 | MLP runs share tracer run shape, differ only in activation (logistic/tanh/relu, never sigmoid), hidden (50,), fixed max_iter, no early stopping | ✓ VERIFIED | `src/training/train_mlp.py:25-29` reuses load_raw_splits/compute_metrics, `:63-106` mirrors Claim 2 run block, `:45` MAX_ITER=500, no early_stopping param (defaults False); live store has mlp-sigmoid/mlp-tanh/mlp-relu runs |
| 6 | Every run registers a version; winner in Staging, superseded in Archived; Production untouched | ✓ VERIFIED | Live query: 9 runs, 9 versions, 9 linked models (`all_runs_have_model: True`), v9=mlp-relu Staging, v1-v8 Archived; `test_every_run_registers_version` (9 versions) + `test_winner_version_resolves_via_run_id` pass |

**Score:** 6/6 truths verified (0 present-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/training/train.py` | 6 classical configs, Claim 2 run shape | ✓ VERIFIED | 163 lines, substantive; ESTIMATORS + build_estimator + load_raw_splits + run_experiment + main all present and exercised |
| `src/training/train_mlp.py` | 3 MLP activation runs, thin variant | ✓ VERIFIED | 116 lines; ACTIVATIONS map, reuse imports from train.py, own run_experiment/main |
| `src/evaluation/evaluate.py` | Ranking + registry lifecycle | ✓ VERIFIED | 143 lines; compute_metrics/select_winner/resolve_winner_version/apply_registry_stages/run_evaluation/main |
| `tests/test_training.py` | 9-config + lineage + Claim 2 tests | ✓ VERIFIED | 5 tests, all pass |
| `tests/test_registry.py` | Ranking + stage + versioning tests | ✓ VERIFIED | 5 tests, all pass |
| `tests/conftest.py` | Synthetic + tmp-store fixtures | ✓ VERIFIED | Exists, suite collects |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| train.py / train_mlp.py | data/processed/*_raw.csv | load_raw_splits reads `{split}_raw.csv` only | ✓ WIRED | `train.py:87`; spy test `test_loader_reads_raw_only` passes; grep for transformed CSV reads clean (one docstring mention only) |
| train.py / train_mlp.py / evaluate.py | mlruns/ | tracking URI via PROJECT_ROOT + config | ✓ WIRED | `train.py:120`, `train_mlp.py:66`, `evaluate.py:90` all use `str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"])` |
| metrics | predict_proba[:, 1] | ROC-AUC from probabilities | ✓ WIRED | `train.py:135`, `train_mlp.py:87`, `evaluate.py:45`; no label-based ROC-AUC path |
| train_mlp.py | train.py run shape | reuse load_raw_splits/compute_metrics | ✓ WIRED | `train_mlp.py:25-29` imports; identical MLflow block `:94-104` |
| evaluate.py | all 9 runs | search_runs + strict-max, unchanged | ✓ WIRED | `evaluate.py:94-109`; winner resolved via run_id `:113` |
| log_model | Registry + Phase 3 load path | serialization_format=cloudpickle pinned | ✓ WIRED | `train.py:149`, `train_mlp.py:102` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| 9 MLflow runs | 5 test metrics | Real test-split inference (fitted pipeline + estimator) | ✓ FLOWING | Live metrics differ per config (e.g. decision-tree roc_auc=0.9804 vs 1.0 elsewhere) — not static |
| 9 runs | preprocessing artifact | joblib.dump of fitted pipeline per run | ✓ FLOWING | `preprocessing` artifact listed on all 9 runs |
| 9 runs | model entity | mlflow.sklearn.log_model per run | ✓ FLOWING | 9 logged models, source_run_ids == all 9 run ids |
| Registry | stages | apply_registry_stages via run_evaluation | ✓ FLOWING | 1 Staging / 8 Archived / 0 Production in live store |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite green | `.\venv\python.exe -m pytest tests -q` | 26 passed in 67.61s | ✓ PASS |
| 9 runs × 5 metrics | MlflowClient search_runs on corvus-ckd | 9 runs, each with accuracy/precision/recall/f1/roc_auc | ✓ PASS |
| 9 versions, winner Staging | search_model_versions corvus-ckd | v1-v8 Archived, v9 (mlp-relu) Staging | ✓ PASS |
| Claim 2 same-run artifacts | list_artifacts + search_logged_models | `preprocessing` on all 9 runs; all 9 runs have linked model | ✓ PASS |
| No Production transition | stage census | 0 versions in Production | ✓ PASS |

Step 7b note: training/evaluate entry points not re-executed (would append duplicate runs/versions to the canonical 9-run store); store state verified read-only instead.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FR-2.1 | 02-01, 02-02 | Train LR, RF, XGB, LGBM, MLP (Sigmoid/Tanh/ReLU as separate runs) | ✓ SATISFIED | All present in live store (+ DT/GB extras); minimum slate exceeded, no conflict |
| FR-2.2 | 02-01 | Log accuracy, precision, recall, F1, ROC-AUC per run | ✓ SATISFIED | All 9 runs carry all 5 metrics (live query) |
| FR-2.3 | 02-01 | Pipeline + model in same MLflow run (Claim 2) | ✓ SATISFIED | All 9 runs: preprocessing artifact + linked logged model |
| FR-2.4 | 02-01 | Compare all models; best by ROC-AUC | ✓ SATISFIED | select_winner strict-max; winner mlp-relu recorded |
| FR-2.5 | 02-02 | Register best model to Registry | ✓ SATISFIED | v9 in Staging |
| FR-3.1 | 02-02 | Registry with Staging / Production / Archived stages | ✓ SATISFIED | Staging + Archived exercised with exact strings; Production stage untouched by design (D-06) |
| FR-3.2 | 02-02 | Version tracking for all registered models | ✓ SATISFIED | 9 versions, one per run, run_id-linked |
| FR-3.3 | 02-02 | Promote/demote between stages | ✓ SATISFIED | transition_model_version_stage used for Staging + Archived moves (mock + live) |

All 8 phase requirement IDs accounted for. No orphaned requirements (FR-1.x → Phase 01, FR-4+ → later phases).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | TBD/FIXME/XXX/TODO/placeholder/console-only/empty-return scan over src/training + src/evaluation + touched tests | — | Clean: only benign docstring/comment mentions ("Never reads transformed…", "Never Production (D-06)") |

Debt markers: none. Commits a33fb05, f2a5100, d11280d, 642ff55, d7721c9, fbae070 all present in git log. `mlruns/` gitignored (`.gitignore:13`).

### Human Verification Required

### 1. MLflow UI — 9 runs with metrics + artifacts

**Test:** `mlflow ui --backend-store-uri mlruns`, open experiment `corvus-ckd`
**Expected:** 9 runs (logistic-regression, decision-tree, random-forest, gradient-boosting, xgboost, lightgbm, mlp-sigmoid, mlp-tanh, mlp-relu), each showing 5 metrics and preprocessing artifact + model
**Why human:** UI rendering needs eyes; API-level store state verified (9 runs / 5 metrics / artifacts confirmed via MlflowClient)

### 2. Registry Models tab — v9 Staging

**Test:** In the same UI, open Models tab for `corvus-ckd`
**Expected:** 9 versions; v9 (mlp-relu) in Staging, v1–v8 in Archived, nothing in Production
**Why human:** Registry tab rendering needs eyes; client-level stages verified (1 Staging / 8 Archived / 0 Production)

### Gaps Summary

No gaps. Every must-have from 02-01-PLAN.md and 02-02-PLAN.md verified against code (file:line) and live `mlruns/` state (9 runs, 9 versions, 9 linked models, 1 Staging / 8 Archived / 0 Production, 26/26 tests green). SUMMARY.md claims match observed reality — no falsification found. Only the two manual MLflow-UI eyeball checks from 02-VALIDATION.md remain, which is expected for this phase.

---

_Verified: 2026-09-21T21:30:00Z_
_Verifier: the agent (gsd-verifier)_
