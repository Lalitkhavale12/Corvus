---
phase: 07-nhanes-native-retrain
plan: 01
subsystem: training
tags: [sklearn, mlflow, nhanes, logistic-regression, quarantine-gate, claim-2, pytest]

# Dependency graph
requires:
  - phase: 02-model-training
    provides: run_experiment Claim-2 shape, ESTIMATORS seeded pattern, compute_metrics
  - phase: 01-data-pipeline
    provides: leak-safe pipeline builder shape, ColumnTransformer idiom, config-driven columns
provides:
  - Native NHANES training path (config keys, quarantined pipeline builder, LR Claim-2 runner)
  - Challenger v10 registered under corvus-ckd (v9 Production untouched)
  - Wave 0 NHANES training test suite (5 tests, synthetic fixture)
affects: [07-02 9-config sweep, 07-03 v2 serving, challenger-vs-v9 comparison]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 4500
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns: [quarantine-gate-before-split, locked-holdout-first, schema-tagged-mlflow-runs, derived-label-disclosure-tag]

key-files:
  created:
    - src/preprocessing/preprocess_nhanes.py
    - src/training/train_nhanes.py
    - tests/test_nhanes_training.py
  modified:
    - config/config.yaml
    - tests/conftest.py

key-decisions:
  - "Quarantine gate checks the allow-list-projected training frame, not the raw CSV (raw CSV carries the label-source columns by design)"
  - "Tracer registers challenger v10 in stage None; v9 stays Production; no Staging/Production transition without the human gate"
  - "Native pipeline artifact uses its own filename (preprocessing_pipeline_nhanes.joblib) so the v1 artifact is never overwritten"

patterns-established:
  - "assert_quarantine(X) runs after allow-list projection and before locked_holdout_split; SystemExit is the one deliberate fail-closed exception to warning-not-crash"
  - "Every native MLflow run carries schema=nhanes-native, label_disclosure, and quarantine_attested tags next to its metrics (D-08)"
  - "Native tests use synthetic_nhanes_df + tmp_mlflow_store only; the real derived CSV and real mlruns are never opened in tests"

requirements-completed: [FR-2.1, FR-2.2, FR-2.3]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "NHANES-native LR trains end-to-end into one Claim-2 MLflow run tagged schema=nhanes-native with pipeline + model artifacts"
    requirement: "FR-2.3"
    verification:
      - kind: unit
        ref: "tests/test_nhanes_training.py#test_claim2_native"
        status: pass
    human_judgment: false
  - id: D2
    description: "Quarantine gate aborts training before any split when a banned column is in the training frame"
    requirement: "FR-2.1"
    verification:
      - kind: unit
        ref: "tests/test_nhanes_training.py#test_quarantine_aborts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Locked 20 percent holdout shares zero row indices with dev data any pipeline or estimator is fitted on"
    requirement: "FR-2.2"
    verification:
      - kind: unit
        ref: "tests/test_nhanes_training.py#test_holdout_disjoint"
        status: pass
    human_judgment: false
  - id: D4
    description: "Live tracer run logged under corvus-ckd-nhanes (holdout roc_auc=0.8246) with disclosure string attached"
    requirement: "FR-2.2"
    verification:
      - kind: other
        ref: "mlflow run 763555dad2d54cf99c5fc1fc885141f5 in experiment corvus-ckd-nhanes (FINISHED, schema=nhanes-native, preprocessing artifact present)"
        status: pass
    human_judgment: false

# Metrics
duration: 35min
completed: 2026-10-15
status: complete
---

# Phase 07 Plan 01: Tracer Native Retrain Summary

**NHANES-native logistic regression trains end-to-end into a schema-tagged Claim-2 run (holdout ROC-AUC 0.8246, challenger v10 registered, v9 untouched) behind a quarantine gate, with 5 Wave 0 training tests green and the suite at 50 passed**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-10-15T07:02:00Z
- **Completed:** 2026-10-15T07:36:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Native LR Claim-2 run logged under experiment `corvus-ckd-nhanes` tagged `schema=nhanes-native` (run 763555da, FINISHED): 5 metrics + `holdout_roc_auc` 0.8246, pipeline artifact at `preprocessing`, model registered as `corvus-ckd` v10 (stage None); v9 remains Production
- Quarantine gate (`QUARANTINE_11` + `assert_quarantine`) aborts with `SystemExit` before any split when any of the 11 banned names reaches the training frame or the config allow-list
- Locked 80/20 stratified holdout (seed 42) proven disjoint; native pipeline (median+StandardScaler / most-frequent+OneHotEncoder drop-first) fits on dev only
- `DERIVED_LABEL_DISCLOSURE` defined once and attached to the live run as a tag, printed next to metrics, and asserted in tests (D-08)
- Full suite green: 50 passed (45 pre-plan baseline + 5 new), 0 failed

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer: native pipeline plus quarantine gate plus LR Claim-2 run** - `a3a4efb` (feat)
2. **Task 2: Wave 0 training tests plus NHANES synthetic fixture** - `e54135c` (test)

## Files Created/Modified

- `config/config.yaml` - Additive `data.nhanes_*` keys (16 numeric, 5 categorical, 11 quarantine, holdout/seed/CV/bootstrap), `mlflow.nhanes_experiment_name`, `api.v2_pinned_version=""`; all existing keys byte-identical
- `src/preprocessing/preprocess_nhanes.py` - `QUARANTINE_11`, `DERIVED_LABEL_DISCLOSURE`, `get_nhanes_column_lists`, `assert_quarantine`, `build_native_pipeline` (unfitted), `locked_holdout_split`
- `src/training/train_nhanes.py` - LR-only `NATIVE_ESTIMATORS`, `build_native_estimator`, `run_experiment_native`, `main`
- `tests/conftest.py` - `synthetic_nhanes_df` fixture (60 rows, ~17% positive, all 11 quarantine cols present, fully synthetic)
- `tests/test_nhanes_training.py` - 5 tests: quarantine abort, pipeline shape, tmp-store Claim-2, holdout disjointness, seeded LR

## Decisions Made

- Gate placement on the projected training frame (see deviation 1) — the only structural decision; everything else followed the plan as specified
- Challenger v10 left in stage None (no Staging transition) — the plan's key link requires registration only; stage movement belongs to 07-02's comparison + the human gate (D-04)
- Native pipeline dump uses `preprocessing_pipeline_nhanes.joblib`, never the v1 filename — prevents overwriting the frozen v1 artifact in `data/processed/`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Quarantine gate targeted the wrong frame and made training impossible**
- **Found during:** Task 1 (gate smoke check before the live run)
- **Issue:** Gating the raw derived CSV always aborts because the locked CSV carries all 11 quarantined label-source columns by design (verified live: `assert_quarantine(raw_df)` raised on all 11 names). Applied literally, the tracer could never train — the plan contradicts its own must-have ("quarantine gate runs before train_test_split" on the training frame).
- **Fix:** `assert_quarantine` checks the config allow-list plus the frame it is given; `run_experiment_native` projects the 16+5 allow-list first (logging the 11 dropped label-source columns), then gates the projected training frame `X` before `locked_holdout_split`. A banned name in the allow-list aborts via the config check; a banned column smuggled into `X` aborts via the frame check. Test `test_quarantine_aborts` pins the frame-abort path.
- **Files modified:** src/preprocessing/preprocess_nhanes.py, src/training/train_nhanes.py
- **Verification:** Breach frame aborts, clean projected frame (5,343 x 21) passes; live run proceeded; `test_quarantine_aborts` passes
- **Committed in:** a3a4efb (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness — without it no native run could ever log. No scope creep; threat mitigations T-07-01/T-07-02/T-07-03 all hold as designed.

## Issues Encountered

- `src/training/train.py` and `src/training/train_mlp.py` show uncommitted working-tree modifications, but those diffs (formatting-only) pre-existed execution — visible in the execution-start `git status` before any plan edit, and this plan never wrote to either file. Pre-plan state preserved.
- PowerShell inline `python -c` with nested double quotes breaks parsing; verification probes were run via a temp script file instead (removed afterwards).

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or schema changes beyond the plan's threat model. T-07-01 (allow-list + abort, pinned by abort test), T-07-02 (seed-42 stratified split, pinned by disjointness test), T-07-03 (disclosure tag on the run) all mitigated in this plan. T-07-04 accepted (no secrets in scope). T-07-SC holds (zero new packages).

## Known Stubs

None — no hardcoded empty values, placeholder text, or unwired components in the files this plan created or modified. `NATIVE_ESTIMATORS` holds LR only by plan design (07-02 expands to 9); `api.v2_pinned_version` is empty-string by plan design until the human gate promotes.

## Self-Check: PASSED

- FOUND: config/config.yaml (nhanes keys present)
- FOUND: src/preprocessing/preprocess_nhanes.py
- FOUND: src/training/train_nhanes.py
- FOUND: tests/test_nhanes_training.py
- FOUND: a3a4efb, e54135c in git log
- Live run 763555da FINISHED under corvus-ckd-nhanes with schema tag + preprocessing artifact; v9 Production / v10 None confirmed

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for 07-02: 9-config sweep reuses `build_native_pipeline` + `locked_holdout_split` + Claim-2 run shape; challenger lineage started at v10
- Watch item for 07-02: live LR holdout ROC-AUC is 0.8246 with recall 0.28 at default threshold — honest derived-label signal without creatinine; the paired harmonized-holdout comparison (not the recorded UCI 1.0) remains the only valid promotion protocol
- No blockers

---
*Phase: 07-nhanes-native-retrain*
*Completed: 2026-10-15*
