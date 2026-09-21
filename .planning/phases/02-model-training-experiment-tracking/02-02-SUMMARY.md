---
phase: 02-model-training-experiment-tracking
plan: 02
subsystem: ml-training
tags: [sklearn, mlflow, xgboost, lightgbm, mlp, model-registry, pytest]
requires:
  - phase: 02-model-training-experiment-tracking
    plan: 01
    provides: tracer LR run_experiment shape + evaluate ranking/Staging lifecycle + Wave 0 fixtures
provides:
  - Full 9-config slate (6 classical + 3 MLP) training through the proven Claim 2 run shape
  - run_id-linked winner-to-version resolution in evaluate.py
  - 9 registered versions of corvus-ckd with winner in Staging, 8 in Archived
affects: [phase-3 API model resolution, phase-5 retraining promotion]
tech-stack:
  added: []
  patterns: [estimator-registry-per-config, thin-mlp-variant-reusing-train-shapes, run-id-version-resolution, tmp-store-registry-tests]
key-files:
  created: [src/training/train_mlp.py]
  modified: [src/training/train.py, src/evaluation/evaluate.py, tests/test_training.py, tests/test_registry.py]
key-decisions:
  - "Winner version resolved via ModelVersion.run_id linkage (tracer latest-version heuristic broke at 9 versions)"
  - "train_mlp.py imports load_raw_splits/compute_metrics from train.py — reuse, not a duplicated run loop"
  - "Canonical 9-run pass done on a reset gitignored mlruns/ so the store holds exactly 9 runs/versions"
requirements-completed: [FR-2.1, FR-2.5, FR-3.1, FR-3.2, FR-3.3]
actuals:
  tokens: 3200
  tasks: 3
  commits: 3
  plan_head_before: 19a1c30
duration: 20min
completed: 2026-09-21
status: complete
---

# Phase 02 Plan 02: Nine-Config Expansion Summary

**9 seeded configs (6 classical + 3 MLP) trained through the tracer's Claim 2 run shape; winner mlp-relu v9 in Staging, 8 superseded in Archived, full suite 26 green**

## Performance

- **Duration:** 20 min
- **Started:** 2026-09-21T15:34:00Z
- **Completed:** 2026-09-21T15:55:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- `src/training/train.py`: ESTIMATORS extended to 6 classical configs (LR byte-identical, DT/RF/GB/XGB/LGBM seeded 42, LGBM `verbosity=-1`), `main()` loops all 6 through unchanged `run_experiment()`
- `src/training/train_mlp.py` (new): thin variant reusing `load_raw_splits`/`compute_metrics` from train.py; ACTIVATIONS sigmoid→logistic/tanh/relu, `hidden_layer_sizes=(50,)`, `max_iter=500`, seeded, no early stopping; ConvergenceWarning logged via module logger
- `src/evaluation/evaluate.py`: new `resolve_winner_version()` maps winning run → version via `ModelVersion.run_id`; `select_winner`/`apply_registry_stages` untouched
- Canonical real-store pass: 9 runs (each 5 metrics + pipeline artifact + linked model), 9 versions, winner `mlp-relu` v9 in Staging, v1–v8 in Archived, nothing in Production
- Full pytest suite green (26 passed, Phase 1 + Phase 2)

## Task Commits

Each task was committed atomically:

1. **Task 1: Full classical slate in train.py** - `642ff55` (feat)
2. **Task 2: train_mlp.py 3 activation runs** - `d7721c9` (feat)
3. **Task 3: run_id-linked winner resolution + 9-version tests** - `fbae070` (feat)

## Files Created/Modified

- `src/training/train.py` - 6-entry ESTIMATORS with per-choice rationale comments, looping main()
- `src/training/train_mlp.py` - ACTIVATIONS map, build_estimator, run_experiment, main()
- `src/evaluation/evaluate.py` - resolve_winner_version(), run_evaluation uses run_id linkage
- `tests/test_training.py` - 6-config construct assertions, new test_mlp_activations_valid (incl. 6+3=9 count)
- `tests/test_registry.py` - test_every_run_registers_version asserts 9 versions, new run_id resolution test

## Decisions Made

- Winner→version resolution via `ModelVersion.run_id` (verified present in installed mlflow 3.16.1) instead of the tracer's latest-version heuristic — required once 9 runs register 9 versions
- `train_mlp.py` imports shared helpers from `train.py` rather than duplicating the run loop; the only new code is the estimator factory
- Reset the gitignored `mlruns/` scratch store before the canonical pass so "run once" yields exactly 9 runs/versions (tracer + Task 2 verification runs would otherwise inflate counts)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tracer winner-version heuristic mapped the winner to the latest version**
- **Found during:** Task 3 (9-run design review before the canonical pass)
- **Issue:** `run_evaluation` used `max(v.version)` as the winner version; with 9 versions the strict-max-ROC-AUC winner is rarely the last-registered run
- **Fix:** Added `resolve_winner_version()` resolving through `ModelVersion.run_id` == winner `run_id`, latest-version fallback only on no match; `select_winner` and `apply_registry_stages` unchanged per plan
- **Files modified:** src/evaluation/evaluate.py, tests/test_registry.py
- **Verification:** `test_winner_version_resolves_via_run_id` passes; canonical pass resolved winner run → v9 correctly
- **Committed in:** fbae070 (part of task commit)

**2. [Rule 3 - Blocking] Stale verification runs would break the exactly-9 acceptance**
- **Found during:** Task 3 (canonical real-store pass)
- **Issue:** Real `mlruns/` already held tracer v1 + 3 Task-2 verification versions; appending 9 more yields 13 versions, failing "holds 9 versions"
- **Fix:** Deleted the gitignored `mlruns/` scratch store (reproducible by re-running; never committed per T-02-02), then ran train + train_mlp + evaluate exactly once
- **Files modified:** none (scratch state only)
- **Verification:** verify script OVERALL: PASS (9 runs, 9 versions, 1 Staging / 8 Archived / 0 Production)
- **Committed in:** n/a (no source change)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both required for correctness of the 9-run lifecycle. No scope creep; no grid search, no Production transition, stages-deprecated TECH DEBT comment intact.

## Issues Encountered

None beyond the auto-fixed deviations above. No auth gates, no checkpoints hit (autonomous plan).

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary crossings. `mlruns/` confirmed gitignored (T-02-02). No installs performed (T-02-SC). joblib load path unchanged from tracer, config-resolved `data/processed/` only (T-02-01). Stub scan over all 5 touched files: clean.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase goal delivered: 9 seeded runs tracked under experiment `corvus-ckd`, winner registered to Staging, superseded Archived
- Phase 3 can resolve the champion via `models:/corvus-ckd/Staging` (currently v9, mlp-relu, test roc_auc=1.0)
- Manual-only verifications pending (MLflow UI: 9 runs with metrics + 2 artifacts each; Models tab: v9 Staging)

---
*Phase: 02-model-training-experiment-tracking*
*Completed: 2026-09-21*

## Self-Check: PASSED

- src/training/train.py, src/training/train_mlp.py, src/evaluation/evaluate.py, tests/test_training.py, tests/test_registry.py all FOUND
- Commits 642ff55, d7721c9, fbae070 all FOUND in git log
- Full suite: 26 passed; registry verify script OVERALL: PASS
