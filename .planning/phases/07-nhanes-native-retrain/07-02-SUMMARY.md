---
phase: 07-nhanes-native-retrain
plan: 02
subsystem: training
tags: [sklearn, mlflow, nhanes, gradient-boosting, stratified-cv, bootstrap-ci, champion-challenger, pytest]

# Dependency graph
requires:
  - phase: 07-nhanes-native-retrain plan 01
    provides: Native pipeline builder, quarantine gate, locked holdout split, tracer LR run, synthetic fixture
provides:
  - 9-config native sweep with dev-only CV plus bootstrap CIs (winner gradient-boosting, v11 Production)
  - Eval-only v9 harmonization adapter plus paired same-rows same-labels comparison (qualifies=True)
  - Human-gate promotion EXECUTED on explicit approval: v11 Production, v9 Archived, api.v2_pinned_version="11" for 07-03
affects: [07-03 v2 serving, Production promotion decision]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 14000
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns: [dev-only-cv-plus-single-holdout-scoring, paired-bootstrap-difference-ci, eval-only-adapter-with-import-ban, production-guard-on-stage-transitions]

key-files:
  created:
    - src/training/harmonize_v9.py
    - src/evaluation/evaluate_nhanes.py
    - scripts/promote_challenger.py
  modified:
    - src/training/train_nhanes.py
    - tests/test_nhanes_training.py

key-decisions:
  - "Winner is gradient-boosting (CV-mean 0.8203, holdout 0.8265), not the tracer LR — selection ran before any holdout peek"
  - "Winner run persists holdout_predictions.csv (row_id/y_true/y_proba) so evaluation proves same-rows same-labels without refitting"
  - "v9 harmonized AUC 0.5479 carries the documented handicap (10 mode-filled categoricals, 5 median-imputed numerics) — the strict-greater rule still governs"
  - "Tracer v10 parked None->Archived as a superseded challenger; v9 Production untouched"
  - "APPROVED v11: explicit human approval executed via promote_challenger.py --version 11 (PROMOTED audit line); v11 Production, v9 Archived with artifacts intact, api.v2_pinned_version=\"11\" handed to 07-03"

patterns-established:
  - "run_cv_native fits a fresh native pipeline per fold-train on dev only; the holdout is referenced only in run_experiment_native"
  - "paired_bootstrap_diff resamples holdout indices once per replicate and scores both models per resample — paired by construction"
  - "apply_challenger_stages refuses any transition naming the Production version and asserts Production after"

requirements-completed: [FR-2.1, FR-2.2, FR-2.3, FR-2.4, FR-2.5, FR-3.1, FR-3.2, FR-3.3]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "9 native configs train through dev-only stratified 5-fold CV with mean plus SD, winner refit on full dev and scored once on the locked holdout"
    requirement: "FR-2.4"
    verification:
      - kind: unit
        ref: "tests/test_nhanes_training.py#test_cv_determinism"
        status: pass
      - kind: other
        ref: "live sweep 2026-10-15: 9 CV lines printed, TRAINED native-gradient-boosting roc_auc=0.8265"
        status: pass
    human_judgment: false
  - id: D2
    description: "Challenger and v9 score identical locked holdout rows against identical derived labels; qualifies iff challenger strictly greater with paired difference CI"
    requirement: "FR-2.5"
    verification:
      - kind: unit
        ref: "tests/test_nhanes_training.py#test_paired_comparison_same_rows_same_labels"
        status: pass
      - kind: other
        ref: "live evaluate 2026-10-15: CHALLENGER v11 0.8265 vs v9 0.5479 diff CI [0.2239, 0.3349] qualifies=True"
        status: pass
    human_judgment: false
  - id: D3
    description: "Challenger v11 sits in Staging with v9 still Production; adapter provably absent from serving imports"
    requirement: "FR-3.1"
    verification:
      - kind: unit
        ref: "tests/test_nhanes_training.py#test_adapter_not_served"
        status: pass
      - kind: other
        ref: "registry snapshot 2026-10-15: v9 Production, v10 Archived, v11 Staging"
        status: pass
    human_judgment: false
  - id: D4
    description: "Human gate APPROVED v11 and the approved Production promotion executed (v11 Production, v9 Archived, pin 11 for 07-03)"
    requirement: "FR-3.3"
    verification:
      - kind: other
        ref: "PROMOTED corvus-ckd version=11 stage=Production audit line, 2026-10-15"
        status: pass
      - kind: other
        ref: "registry snapshot post-promotion 2026-10-15: v11 Production (run 5954f069), v9 Archived (run 10ac3e5e, artifacts intact), v1-v8/v10 untouched"
        status: pass
      - kind: unit
        ref: "full suite post-promotion: 59 passed, 0 failed"
        status: pass
    human_judgment: false
    rationale: "D-04 approval itself was an explicit human decision (APPROVE v11, recorded in the continuation dispatch); execution and post-state are programmatically verified above"

# Metrics
duration: 20min + gate execution 45min
completed: 2026-10-15
status: complete
---

# Phase 07 Plan 02: 9-Config Sweep plus Paired Comparison plus Approved Promotion Summary

**Gradient-boosting wins the native 9-config CV sweep (holdout ROC-AUC 0.8265) and beats harmonized v9 on the paired locked holdout (0.8265 vs 0.5479, diff CI [0.2239, 0.3349]); human gate APPROVED v11 — challenger promoted to Production, v9 Archived intact, api.v2_pinned_version="11" handed to 07-03**

> **GATE STATUS: APPROVED + EXECUTED 2026-10-15.** The human approved Production promotion of
> challenger version 11 (gradient-boosting, run 5954f069, holdout ROC-AUC 0.8265).
> `scripts/promote_challenger.py --version 11` ran and printed
> `PROMOTED corvus-ckd version=11 stage=Production`. Post-state verified: v11 Production,
> v9 Archived (artifacts intact, NOT deleted), all 11 versions present. Full suite green post-promotion.

## Performance

- **Duration:** ~20 min (tasks 1-2) + ~45 min gate-execution continuation (registry probes, promotion, full suite re-run, docs)
- **Started:** 2026-10-15T07:47:46Z
- **Completed:** 2026-10-15T08:05:03Z (tasks 1-2); gate executed 2026-10-15T15:07Z (~20:37 IST)
- **Tasks:** 3 of 3 (gate approved and executed)
- **Files modified:** 5 (code) + 3 (docs: SUMMARY, STATE, ROADMAP)

## Accomplishments

- Live 9-config sweep on the 5,343-row derived cohort: dev-only stratified 5-fold CV per config (gradient-boosting CV-mean 0.8203 ± 0.0135 wins; decision-tree 0.6310 trails; MLP ConvergenceWarnings logged, never raised), winner refit on full dev, single holdout scoring (roc_auc 0.8265, CI [0.7910, 0.8572]), Claim-2 run registered as `corvus-ckd` v11 with CV mean/SD, CI bounds, and `holdout_predictions.csv` artifact
- Paired comparison on the identical locked holdout rows against identical derived labels: challenger 0.8265 vs v9-harmonized 0.5479 (documented handicap: 10 mode-filled categoricals + 5 median-imputed numerics), paired-bootstrap difference CI [0.2239, 0.3349], strict-greater `qualifies=True`
- Registry now: v11 Production (run 5954f069, promoted on approval), v9 Archived (run 10ac3e5e, artifacts intact — transition only, never deleted), v10 Archived (superseded tracer), v1-v8 Archived untouched — disclosure string attached to every reported metric
- Gate execution verified end to end: pre-state snapshot (v11 Staging / v9 Production), PROMOTED audit line, post-state snapshot (v11 Production / v9 Archived / nothing deleted), full suite re-run green post-promotion
- Full suite green: 59 passed (50 pre-plan baseline + 9 new), 0 failed — before AND after promotion

## Task Commits

Each task was committed atomically:

1. **Task 1: 9-config sweep plus stratified CV plus bootstrap CIs** - `73827e1` (feat)
2. **Task 2: Harmonization adapter plus paired comparison plus challenger staging** - `a40dbe1` (feat)
3. **Task 3 (gate prep): challenger promotion script, created unrun** - `65f6663` (feat)
4. **Task 3 (gate execution, APPROVED): v11 promoted to Production** — registry-only transition, no file diff by design (`mlruns/` is gitignored; the audit trail is the `PROMOTED corvus-ckd version=11 stage=Production` stdout line plus the pre/post registry snapshots recorded here)
5. **Docs: gate-executed summary + state + roadmap** - recorded in the plan metadata commit below

## Files Created/Modified

- `src/training/train_nhanes.py` - Full 9-config `NATIVE_ESTIMATORS`, `run_cv_native`, `bootstrap_auc_ci`, `sweep_native` + strict-max `select_by_cv`, winner refit + single holdout scoring + Claim-2 run with CV/CI metrics and holdout-predictions artifact
- `src/training/harmonize_v9.py` - Eval-only adapter: `NHANES_TO_UCI_MAP` (9 shared numerics) + per-field unit notes, frozen-pipeline categorical modes, read-only v9 load at pinned version 9, never any `fit`
- `src/evaluation/evaluate_nhanes.py` - `aggregate_cv`, `paired_bootstrap_diff`, `compare_challenger` (strict-greater), `apply_challenger_stages` (Production guard), `run_evaluation` (same-rows/same-labels enforcement + Staging)
- `scripts/promote_challenger.py` - `promote_production` shape with required `--version`; created, `--help` verified, NEVER executed
- `tests/test_nhanes_training.py` - 14 tests (5 carried + 9 new): exact-set/seeds, CV determinism, bootstrap CI, no-recorded-UCI-AUC scan, paired same-rows/labels, paired determinism, strict-max, harmonized frame, Production guard, api isolation scan

## Decisions Made

- Gradient-boosting wins honestly: selection ran on dev-only CV means before any holdout peek; the holdout was scored exactly once by the winner's refit
- `holdout_predictions.csv` (row_id/y_true/y_proba) persisted in the winner run so evaluation enforces same-rows/same-labels programmatically (row-id set equality + label equality) with zero native refitting
- Keeping v9 on a failed gate would have been an acceptable evidence outcome; the gate passed on merit (difference CI far from zero), so the question before the human is promotion, not validity
- Tracer v10 moved to Archived as a superseded challenger per the plan's staging rule — it was never a candidate, only lineage
- APPROVED v11 executed 2026-10-15: pre-state verified (v11 Staging / v9 Production / v10 Archived), `promote_challenger.py --version 11` printed the PROMOTED line with `archive_existing_versions=true`, post-state verified (v11 Production / v9 Archived with run 10ac3e5e artifacts intact / all 11 versions present / nothing deleted); v1 serving code and v9 artifacts never touched
- Commits stay on `main` per the sequential-orchestrator instruction and the 07-01 precedent (all phase commits live on `main`; no worktree in use)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] UCI-absence scan tripped on the word "reproducible"**
- **Found during:** Task 1 (test run)
- **Issue:** The no-recorded-UCI-AUC scan matched the substring "uci" inside "reproducible" in a seeding comment — a test-construction bug, not a source violation
- **Fix:** Scan uses word-boundary `\buci\b` (case-insensitive) plus the `1.0`-literal check
- **Files modified:** tests/test_nhanes_training.py
- **Verification:** `test_no_recorded_uci_auc_reference` passes; source still carries no UCI reference
- **Committed in:** 73827e1 (part of task commit)

**2. [Rule 2 - Missing Critical] Winner run persists its holdout predictions**
- **Found during:** Task 1 (designing the evaluation handoff)
- **Issue:** The plan's comparison needs same-rows/same-labels proof, but logged scalar AUCs cannot prove it — evaluation would have to rescore the holdout (a second scoring, contaminating the promotion metric)
- **Fix:** `run_experiment_native` writes `holdout_predictions_native.csv` (row_id, y_true, y_proba) and logs it under `evaluation/`; `run_evaluation` downloads it and asserts row-id set equality plus label equality before comparing
- **Files modified:** src/training/train_nhanes.py, src/evaluation/evaluate_nhanes.py
- **Verification:** Live run artifact downloaded and matched the locked holdout exactly; evaluation proceeded
- **Committed in:** 73827e1 / a40dbe1 (respective task commits)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both necessary for correctness — the scan fix keeps the cross-dataset-comparison ban enforced without false positives; the predictions artifact is what makes the single-scoring rule and the same-rows proof jointly satisfiable. No scope creep; threat mitigations T-07-05/T-07-06/T-07-07/T-07-08/T-07-09 and T-07-SC all hold.

## Issues Encountered

- PowerShell inline `python -c` with nested quotes breaks parsing (same as 07-01) — registry probes ran via a temp script file outside the repo (removed afterwards)
- `src/training/train.py` / `train_mlp.py` / `api/*` show working-tree modifications that pre-existed execution (noted in 07-01); this plan never wrote to them — verified via per-task `git add <specific files>`
- Live sweep logs a long `Unexpected columns` warning (130+ non-allow-list columns in the 177-column derived CSV) — expected warning-not-crash behavior, allow-list projection drops them

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or schema changes beyond the plan's threat model. T-07-05 (dev-only CV + single holdout scoring, pinned by disjointness + determinism tests), T-07-06 (v9 read-only at pinned 9, no `fit` in adapter), T-07-07 (blocking-human gate; no Production transition exists), T-07-08 (adapter import-ban scan passes), T-07-09 (disclosure on every metric + cross-dataset path absent by scanned construction) all mitigated. T-07-SC holds (zero new packages).

## Known Stubs

None — no hardcoded empty values, placeholder text, or unwired components in the files this plan created or modified. `api.v2_pinned_version` in `config.yaml` remains `""` until 07-03 flips it; the value 07-03 MUST pin is recorded here: **`"11"`** (gradient-boosting, run 5954f069, Production since 2026-10-15).

## Self-Check: PASSED

- FOUND: src/training/train_nhanes.py (9 configs), src/training/harmonize_v9.py, src/evaluation/evaluate_nhanes.py, scripts/promote_challenger.py, tests/test_nhanes_training.py (14 tests)
- FOUND: 73827e1, a40dbe1, 65f6663 in git log
- Live: winner run 5954f069 (FINISHED) under corvus-ckd-nhanes, holdout_roc_auc 0.8265; registry v9 Production / v10 Archived / v11 Staging confirmed by snapshot (pre-promotion)
- Full suite: 59 passed, 0 failed

## Gate Execution Self-Check: PASSED (2026-10-15)

- PRE-STATE: v11 Staging (run 5954f069), v9 Production (run 10ac3e5e), v10 Archived — matches the halted SUMMARY exactly
- PROMOTED line: `PROMOTED corvus-ckd version=11 stage=Production` (only stdout; the FutureWarning about stage deprecation is upstream MLflow notice, not a failure)
- POST-STATE: v11 Production (run 5954f069), v9 Archived (run 10ac3e5e — still present, artifacts intact), v1-v8 + v10 Archived untouched — 11 versions total, zero deletions
- v1 serving code (`api/*`, `src/training/train.py`, `src/training/train_mlp.py`) never staged or committed by this run; pre-existing working-tree modifications left alone
- Full suite post-promotion: 59 passed, 0 failed
- Pin for 07-03: `api.v2_pinned_version = "11"` recorded here and in STATE.md

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Gate resolved — 07-03 UNBLOCKED:** serve `api.v2_pinned_version = "11"` (gradient-boosting, run 5954f069, Production). v1 routes keep serving v9's frozen artifacts until the 07-03 hard cutover (D-06); the v9 model files still exist under Archived run 10ac3e5e
- Watch item for 07-03: v9's harmonized 0.5479 is a handicap artifact of mode/median filling, NOT a claim about v9's UCI performance — never quote it outside the paired-protocol framing
- No blockers

---

*Phase: 07-nhanes-native-retrain*
*Completed: 2026-10-15*
*Gate: APPROVED + EXECUTED — v11 Production, pin "11" for 07-03*
