---
phase: 02-model-training-experiment-tracking
plan: 01
subsystem: ml-training
tags: [sklearn, mlflow, logistic-regression, model-registry, pytest]

# Dependency graph
requires:
  - phase: 01-data-pipeline
    provides: data/processed/*_raw.csv splits + preprocessing_pipeline.joblib + Claim 2 training-input contract
provides:
  - Tracer LR path: raw CSVs through train-only pipeline re-fit into one Claim 2 MLflow run
  - src/evaluation/evaluate.py with strict-max ROC-AUC ranking + Staging/Archived lifecycle
  - Wave 0 fixtures (conftest.py) reused by plan 02-02's 9-config expansion
affects: [02-02 nine-config expansion, phase-3 API model resolution]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 9000
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns: [uniform per-run train-log shape, tmp-tracking-URI MLflow isolation, proba-based ROC-AUC, register-every-version + transition-winner]

key-files:
  created: [src/training/train.py, src/evaluation/evaluate.py, tests/conftest.py, tests/test_training.py, tests/test_registry.py]
  modified: []

key-decisions:
  - "MLflow 3.x logged-model linkage asserted instead of run-artifact path for the model"
  - "MLFLOW_ALLOW_FILE_STORE opt-in set in module entry points (file store is the locked architecture)"
  - "evaluate.py reads latest registry version as winner via search_model_versions (get_latest_versions returns one-per-stage)"

patterns-established:
  - "Uniform per-run shape: load_raw_splits -> train-only pipeline re-fit -> fit estimator -> one start_run block with params + 5 metrics + pipeline artifact + model"
  - "MLflow isolation in tests: tmp tracking URI via tmp_path, never the real mlruns/"
  - "Registry assertions via mocked MlflowClient for stage strings, tmp-store client for versioning"

requirements-completed: [FR-2.1, FR-2.2, FR-2.3, FR-2.4]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Logistic regression trains end-to-end from train_raw.csv into one MLflow run with params, 5 metrics, pipeline artifact, and model"
    requirement: "FR-2.1"
    verification:
      - kind: integration
        ref: "tests/test_training.py#test_run_logs_pipeline_and_model"
        status: pass
      - kind: other
        ref: ".\\venv\\python.exe -m src.training.train (1 run, logistic-regression, 5 metrics)"
        status: pass
    human_judgment: false
  - id: D2
    description: "All 5 metrics logged per run with ROC-AUC from predict_proba"
    requirement: "FR-2.2"
    verification:
      - kind: unit
        ref: "tests/test_training.py#test_all_nine_configs_construct + test_lineage_excluded_feature_count_24"
        status: pass
    human_judgment: false
  - id: D3
    description: "Claim 2: preprocessing_pipeline.joblib + model logged in the same run; loader reads *_raw.csv only with 24 lineage-free features"
    requirement: "FR-2.3"
    verification:
      - kind: unit
        ref: "tests/test_training.py#test_loader_reads_raw_only + test_lineage_excluded_feature_count_24"
        status: pass
    human_judgment: false
  - id: D4
    description: "Winner ranked by strict max test ROC-AUC and transitioned to Staging; superseded to Archived; never Production"
    requirement: "FR-2.4"
    verification:
      - kind: unit
        ref: "tests/test_registry.py (4 tests)"
        status: pass
      - kind: other
        ref: ".\\venv\\python.exe -m src.evaluation.evaluate (WINNER logistic-regression, stage=Staging)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-09-21
status: complete
---

# Phase 02 Plan 01: Tracer Slice Summary

**Logistic-regression train-to-MLflow-to-registry path: one Claim 2 run (roc_auc=1.0) ranked by strict-max ROC-AUC into Staging, full suite 24 green**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-21T20:35:00Z
- **Completed:** 2026-09-21T21:00:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Wave 0 stubs (conftest + test_training + test_registry) collected red, then turned green through implementation
- `src/training/train.py`: raw-CSV loader, seeded LR estimator registry, Claim 2 single-run logging (roc_auc=1.0 on test)
- `src/evaluation/evaluate.py`: proba-based metrics, strict-max winner, winner-to-Staging / superseded-to-Archived, int-exit main
- Full pytest suite green (24 passed); real `mlruns/` holds 1 run + registered model `corvus-ckd` v1 in Staging

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test stubs (conftest + test_training + test_registry)** - `a33fb05` (test)
2. **Task 2: End-to-end logistic-regression path** - `f2a5100` (feat)
3. **Task 3: evaluate.py ranking + Staging transition** - `d11280d` (feat)

⚡ Tracer verified end-to-end — expanding (plan 02-02 reuses the per-run shape for all 9 configs).

## Files Created/Modified

- `src/training/train.py` - load_raw_splits(), build_estimator(), run_experiment(), ESTIMATORS (LR), main()
- `src/evaluation/evaluate.py` - compute_metrics(), select_winner(), apply_registry_stages(), run_evaluation(), main()
- `tests/conftest.py` - synthetic_ckd_df (40 rows) + tmp_mlflow_store fixtures
- `tests/test_training.py` - config construct, lineage-24, raw-only loader, Claim 2 run artifacts
- `tests/test_registry.py` - strict-max ranking, stage strings, versioning, no-Production

## Decisions Made

- MLflow 3.x model assertion via `search_logged_models` linkage (log_model no longer lands under run artifacts) — verified against installed 3.16.1
- `MLFLOW_ALLOW_FILE_STORE=true` opt-in via `os.environ.setdefault` in both entry points (file store is the locked architecture; user override wins)
- `search_model_versions` instead of `get_latest_versions` in run_evaluation (latter returns one version per stage, hiding history)
- Single registered-model name `corvus-ckd` per RESEARCH open question 1 resolution

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Loader assumed string labels; raw CSVs already carry binary 0/1 targets**
- **Found during:** Task 2 (training test run)
- **Issue:** `load_raw_splits` string-compared every target to positive_label, yielding all-zero y and a single-class solver error
- **Fix:** Detect pre-encoded 0/1 targets and use as-is; string-compare fallback otherwise
- **Files modified:** src/training/train.py
- **Verification:** test_training.py 4 passed; real train distribution {1: 174, 0: 105}
- **Committed in:** f2a5100 (part of task commit)

**2. [Rule 3 - Blocking] MLflow 3.x file store gated behind MLFLOW_ALLOW_FILE_STORE**
- **Found during:** Task 2 (first MLflow run)
- **Issue:** FileStore raises MlflowException in maintenance mode without the env opt-in
- **Fix:** `os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")` in train.py and evaluate.py
- **Files modified:** src/training/train.py, src/evaluation/evaluate.py
- **Verification:** `python -m src.training.train` exits 0, run created
- **Committed in:** f2a5100, d11280d (part of task commits)

**3. [Rule 1 - Bug] Test asserted model under run artifacts; MLflow 3.x uses linked logged-models**
- **Found during:** Task 2 (Claim 2 test)
- **Issue:** `client.list_artifacts(run_id)` contains only `preprocessing`; the model is a logged-model entity
- **Fix:** Assert linkage via `search_logged_models` DataFrame `source_run_id` column
- **Files modified:** tests/test_training.py
- **Verification:** test_run_logs_pipeline_and_model passes
- **Committed in:** f2a5100 (part of task commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes required for correctness against installed mlflow 3.16.1. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above. No auth gates, no checkpoints hit (autonomous plan).

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary crossings. `mlruns/` confirmed git-ignored (T-02-02). No installs performed (T-02-SC). joblib.load only from config-resolved `data/processed/` (T-02-01).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Tracer path proven: plan 02-02 can expand ESTIMATORS to all 9 configs reusing `run_experiment()` shape
- Registry holds `corvus-ckd` v1 in Staging; plan 02-02 will add versions + superseded-to-Archived coverage
- Manual-only verifications pending (MLflow UI: 9 runs after 02-02; Registry Models tab)

---
*Phase: 02-model-training-experiment-tracking*
*Completed: 2026-09-21*

## Self-Check: PASSED

- tests/conftest.py, tests/test_training.py, tests/test_registry.py, src/training/train.py, src/evaluation/evaluate.py all FOUND
- Commits a33fb05, f2a5100, d11280d all FOUND in git log
- Full suite: 24 passed
