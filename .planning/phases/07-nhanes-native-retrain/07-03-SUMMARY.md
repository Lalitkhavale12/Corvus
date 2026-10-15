---
phase: 07-nhanes-native-retrain
plan: 03
subsystem: api-serving
tags: [fastapi, pydantic, nhanes, v2-serving, fail-closed, pytest]

# Dependency graph
requires:
  - phase: 07-nhanes-native-retrain plan 01
    provides: Native 16+5 column lists, quarantine gate, native pipeline shape
  - phase: 07-nhanes-native-retrain plan 02
    provides: Challenger v11 Production (gradient-boosting, run 5954f069), api.v2_pinned_version="11" handoff
provides:
  - CKDRequestNative plus NativeBatchItem strict native validation
  - Second loader slot (resolve_v2_version plus load_v2_artifacts) with native width assert
  - POST /v2/predict plus POST /v2/batch_predict plus GET /v2/model_info with 503 fail-closed
  - predictions_v2 isolated log table with version-stamped rows
  - 15-test v2 suite with v1 regression plus adapter isolation plus artifact-path drift pin
affects: [production cutover (pin flip), Phase 4 monitoring of predictions_v2]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 7200
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns: [dual-slot-pinned-loader, fail-closed-unconfigured-slot, separate-table-per-schema, artifact-path-drift-pin-test]

key-files:
  created:
    - tests/test_api_v2.py
  modified:
    - api/schemas.py
    - api/model_loader.py
    - api/app.py
    - api/db.py

key-decisions:
  - "Native categoricals are int Literals (RIAGENDR {1,2}, RIDRETH1 {1..5}, DMDEDUC2 {1..5,9}, DIQ010 {1,2,3}, MCQ035 {1,2,9}) verified against the locked CSV — float 1.0 coerces, 1.5 and strings 422"
  - "Config pin api.v2_pinned_version stays empty-string: flipping it would break test_api.py hermeticity (lifespan would hit the real registry); cutover is a deploy-time MODEL_VERSION_V2/config flip, not a code change"
  - "Rule 1 fix: v2 loader reads preprocessing_pipeline_nhanes.joblib (07-01 distinct filename), not the v1 path — proven by live v11 load (width 30 == n_features_in_)"
  - "Commits stay on main per the sequential-orchestrator instruction and the 07-01/07-02 precedent"

patterns-established:
  - "load_v2_artifacts mirrors load_serving_artifacts on the native schema with its own probe literals and artifact path constant"
  - "_require_v2 503s naming api.v2_pinned_version before any log-store or inference work when the slot is unconfigured"
  - "V2_PIPELINE_ARTIFACT_PATH drift-pinned against train_nhanes.NATIVE_PIPELINE_FILENAME by unit test"

requirements-completed: [FR-4.1, FR-4.2, FR-4.3]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Native requests validate strictly on /v2 with version-11 stamped predictions and isolated predictions_v2 rows"
    requirement: "FR-4.1"
    verification:
      - kind: unit
        ref: "tests/test_api_v2.py (valid single, batch, model_info, log shape)"
        status: pass
      - kind: other
        ref: "live v11 probe 2026-10-15: GB run 5954f069 loads via v2 slot, width 30, real NHANES rows score (5,2)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Missing native field 422s naming the field, bad Literal 422s, null numerics flow to imputers, unconfigured v2 503s naming v2_pinned_version"
    requirement: "FR-4.2"
    verification:
      - kind: unit
        ref: "tests/test_api_v2.py (missing-field, bad-literal, null-numeric, unconfigured-503)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every v2 response and every predictions_v2 row carries model_version 11; v1 predictions table and v9 stamping unchanged"
    requirement: "FR-4.3"
    verification:
      - kind: unit
        ref: "tests/test_api_v2.py (log shape, v1 regression) + tests/test_api.py 19 passed unchanged"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-10-15
status: complete
---

# Phase 07 Plan 03: v2 Native Serving Summary

**/v2/predict + /v2/batch_predict + /v2/model_info live beside untouched v1 routes with isolated version-stamped logging; unconfigured state fails closed 503; full suite 74 passed with v1 regression pinned**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-10-15T20:45Z (approx)
- **Completed:** 2026-10-15T21:30Z (approx)
- **Tasks:** 3 of 3
- **Files modified:** 5 (4 code + 1 new test file)

## Accomplishments

- Native schemas: `CKDRequestNative` (16 nullable numerics, 5 NHANES-coded int-Literal categoricals verified against the locked derived CSV) plus `NativeBatchItem` for the batch path; v1 `CKDRequest` byte-identical; existing `PredictionResponse`/`BatchPredictionResponse` reused
- Second loader slot: `resolve_v2_version` (`MODEL_VERSION_V2` env else `api.v2_pinned_version`) plus `load_v2_artifacts` with native-schema probe and width assert; v1 resolver/loader untouched
- v2 routes: lifespan v2 slots, `_require_v2` 503 fail-closed naming `api.v2_pinned_version`, `COLUMN_ORDER_V2` + `DROP_COLS_V2`, `/v2/predict`, `/v2/batch_predict` (413 caps, DROP via constants, warn-ignore extras, 422 missing columns, 1-indexed per-row validation, single-commit all-or-nothing to `predictions_v2`), `/v2/model_info`; v1 handlers untouched; 500 handler covers v2
- Isolated logging: `PredictionLogV2` on `predictions_v2` (16 nullable Float, 5 String(16), outcome + version + timestamp); v1 `PredictionLog`/`predictions` untouched; `create_all` picks the table up with no `create_tables` change
- 15-test v2 suite on dual-slot stubs (v1→9, v2→11): versioned predict, 422 strictness, null-numeric imputer path, unconfigured 503, model_info, batch guards (bytes + rows 413), all-or-nothing offender naming, extras ignored, v2 log shape, v1 v9 regression, adapter isolation scan, artifact-path drift pin
- Live proof beyond stubs: real `corvus-ckd` v11 (GradientBoostingClassifier, run 5954f069) loads through `load_v2_artifacts`, width assert 30 == 30, 5 real NHANES rows transform and score
- Full suite green: 74 passed (59 pre-plan + 15 new), 0 failed

## Task Commits

Each task was committed atomically:

1. **Task 1: Native schemas plus second loader slot** - `f9b60dc` (feat)
2. **Task 2: V2 routes plus separate v2 log table** - `2a0c899` (feat)
3. **Task 3: V2 API test suite with v1 regression** - `fcb7f68` (test)
4. **Rule 1 fix: v2 loader reads native pipeline artifact path** - `ff0b32e` (fix)

## Files Created/Modified

- `api/schemas.py` - `CKDRequestNative` (21 native fields, int-Literal categoricals with observed-code docstring) + `NativeBatchItem`; v1 classes untouched
- `api/model_loader.py` - `_V2_PROBE_CATEGORICALS`, `resolve_v2_version`, `load_v2_artifacts` (native probe + width assert), `V2_PIPELINE_ARTIFACT_PATH`; v1 functions untouched
- `api/app.py` - Lifespan v2 slots with unconfigured warning, `_require_v2`, `COLUMN_ORDER_V2`/`DROP_COLS_V2`, `_frame_from_native_request`, `_predict_frame_v2`, `_log_predictions_v2`, `/v2/predict`, `/v2/batch_predict`, `/v2/model_info`; v1 handlers untouched
- `api/db.py` - `PredictionLogV2` on `predictions_v2`; v1 `PredictionLog` untouched
- `tests/test_api_v2.py` - 15 tests: dual-slot stubs, strictness, fail-closed, guards, isolation, regression, drift pin

## Decisions Made

- Native categoricals typed as int `Literal`s (not strings): the training frame carries numeric NHANES codes and the fitted OneHotEncoder expects numerics; pydantic coerces 1.0→1 while rejecting 1.5 and strings (probed live before writing schemas)
- Config pin stays `""` in this plan: setting `"11"` in `config.yaml` would make `tests/test_api.py` lifespan hit the real registry (it patches only the v1 loader), breaking test hermeticity; the D-06 cutover is a deploy-time `MODEL_VERSION_V2=11` env (or config) flip, verified safe by the live probe
- Rule 1 artifact-path fix over plan-literal path: the plan pointed at `PIPELINE_ARTIFACT_PATH`, but v11's run holds `preprocessing_pipeline_nhanes.joblib` (07-01 distinct-filename design); the live probe's `MlflowException` proved the plan path wrong, the registry listing proved the right one
- Commits stay on `main` per the sequential-orchestrator instruction and the 07-01/07-02 precedent; per-task `git add <specific files>` only

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] v2 loader pointed at the v1 pipeline artifact path**
- **Found during:** Post-Task-2 live verification (read-only v11 load probe)
- **Issue:** `load_v2_artifacts` reused `PIPELINE_ARTIFACT_PATH` (`preprocessing/preprocessing_pipeline.joblib`), but the v11 run logs `preprocessing/preprocessing_pipeline_nhanes.joblib` — startup load raised `MlflowException`, so /v2 could never have served v11
- **Fix:** New `V2_PIPELINE_ARTIFACT_PATH` constant used by `load_v2_artifacts`, plus a drift-pinning test asserting it equals `preprocessing/{train_nhanes.NATIVE_PIPELINE_FILENAME}` and differs from the v1 path
- **Files modified:** api/model_loader.py, tests/test_api_v2.py
- **Verification:** Live probe post-fix — v11 GB run 5954f069 loads, width 30 == `n_features_in_` 30, real NHANES rows score; full suite 74 passed
- **Committed in:** ff0b32e

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness — without it the plan's core objective (serve v11 on /v2) fails at startup. No scope creep; threat mitigations T-07-10/T-07-11/T-07-12/T-07-13/T-07-14 and T-07-SC all hold.

## Issues Encountered

- PowerShell inline `python -c` with nested quotes breaks parsing (same as 07-01/07-02) — probes ran via temp scripts under `C:\Users\Lalit\AppData\Local\Temp\opencode\` (outside the repo, never committed)
- `api/*` carried pre-existing formatting-only working-tree diffs (blank line + import/return rewraps, noted in 07-01/07-02); this plan's changes are purely additive on top — verified via `git diff` removal-hunk inspection (only the two pre-existing lines removed)
- One self-inflicted edit dropped the `def get_database_url` line in `api/db.py`; caught and restored immediately, verified by import + table-name probe before committing

## Threat Flags

None — no new surface beyond the plan's threat model. T-07-10 (Literal vocabularies 422 fail-closed, probed), T-07-11 (separate `predictions_v2`, v1 table name + 29-column shape verified intact), T-07-12 (both 413 caps tested bytes + rows), T-07-13 (500 handler covers v2 by shared path; 503 names the key, never secrets; no `DATABASE_URL` value logged), T-07-14 (`_require_v2` 503 tested configured + unconfigured; width assert proven live against v11). T-07-SC holds (zero new packages).

## Known Stubs

None — no hardcoded empty values, placeholder text, or unwired components in the files this plan created or modified. `api.v2_pinned_version` remains `""` in `config.yaml` by decision above (cutover is deploy-time); flip to `"11"` (gradient-boosting, run 5954f069, Production) via `MODEL_VERSION_V2=11` env or config edit when deploying.

## Self-Check: PASSED

- FOUND: api/schemas.py (CKDRequestNative, NativeBatchItem), api/model_loader.py (resolve_v2_version, load_v2_artifacts, V2_PIPELINE_ARTIFACT_PATH), api/app.py (/v2/predict, /v2/batch_predict, /v2/model_info, _require_v2), api/db.py (PredictionLogV2), tests/test_api_v2.py (15 tests)
- FOUND: f9b60dc, 2a0c899, fcb7f68, ff0b32e in git log
- Full suite: 74 passed, 0 failed (59 pre-plan + 15 new)
- Live: v11 loads via v2 slot, width 30, real rows score

## User Setup Required

None - no external service configuration required. Deploy-time note: set `MODEL_VERSION_V2=11` (or `api.v2_pinned_version: "11"`) where the API serves, with `DATABASE_URL` pointed at Postgres carrying the `predictions_v2` table (auto-created by `create_tables` on startup).

## Next Phase Readiness

- **Phase 7 COMPLETE with this plan:** all three wave plans done (07-01 tracer, 07-02 sweep + APPROVED promotion, 07-03 v2 serving). Remaining: production cutover flip + Phase 4 monitoring of `predictions_v2`
- Watch item: `predictions_v2` categorical columns are `String(16)` while requests carry int codes — Postgres assignment casts handle int→varchar on INSERT; if a strict store ever rejects, stringify codes in `_log_predictions_v2`
- Watch item (inherited): v9's harmonized 0.5479 is a handicap artifact — never quote outside the paired-protocol framing
- No blockers

---

*Phase: 07-nhanes-native-retrain*
*Completed: 2026-10-15*
