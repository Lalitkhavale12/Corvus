---
phase: 03-prediction-api-containerization
plan: 03
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, postgres, batch, claim-4]

# Dependency graph
requires:
  - phase: 02-model-training-experiment-tracking
    provides: corvus-ckd registry v1-v9 with v9 winner (mlp-relu) in Production
  - phase: 03-prediction-api-containerization plan 02
    provides: lifespan-pinned v9 serving, /predict + minimal /batch_predict, 12 API tests
provides:
  - hardened POST /batch_predict (size/row caps, warn-ignore extras, typed response)
  - D-04 full-record logging (per-row created_at stamp, single-commit unit of work)
  - 19 green API tests, full suite 45 green
affects: [03-04 compose frontend, phase-5 drift reads]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 3000
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns: [size-gated CSV upload (bytes then row count before pandas parse), warn-and-ignore unknown columns, per-row created_at stamping with server_default fallback]

key-files:
  created: []
  modified: [api/schemas.py, api/app.py, api/db.py, tests/conftest.py, tests/test_api.py]

key-decisions:
  - "Unexpected batch columns warn-logged and ignored (train.py extras pattern), not 422 — 03-02's strict rejection softened per T-03-08"
  - "created_at stamped per row in app code plus column-level default — mocked captures carry the D-04 timestamp"
  - "Single shared session.commit() call site kept instead of the plan's 'exactly 2' — same atomicity, less duplication"

patterns-established:
  - "Batch fixtures via _batch_csv_from_rows helper: valid_batch_csv (5 clean rows), bad_row_batch_csv (row 3 rbc=ripe)"
  - "413 tests use oversized raw bytes (parse never reached); extras test appends a mystery column"

requirements-completed: [FR-4.1, FR-4.2, FR-4.3, FR-5.2]

# Coverage metadata (#1602) — drives DETERMINISTIC UAT routing in verify-work.
coverage:
  - id: D1
    description: "POST /batch_predict accepts a 24-column CSV, returns count + per-row items + model_version 9 with one commit"
    requirement: "FR-4.1"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_batch_valid_returns_count_and_row_items"
        status: pass
    human_judgment: false
  - id: D2
    description: "One bad row rejects the whole batch naming the row number with zero writes"
    requirement: "FR-4.1"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_batch_bad_row_3_rejects_with_zero_writes + test_batch_all_or_nothing_names_row_2"
        status: pass
    human_judgment: false
  - id: D3
    description: "Missing columns 422 naming the column; oversized bodies 413 before parsing"
    requirement: "FR-4.2"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_batch_missing_column_is_422 + test_batch_oversize_body_is_413"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every logged row holds all 24 fields + prediction + probability + model_version 9 + non-null created_at"
    requirement: "FR-5.2"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_batch_logged_rows_carry_full_record + test_logged_row_carries_model_version"
        status: pass
    human_judgment: false
  - id: D5
    description: "Unset DATABASE_URL fails closed with 503 naming DATABASE_URL on batch; extras warn-ignored"
    requirement: "FR-4.3"
    verification:
      - kind: unit
        ref: "tests/test_api.py#test_batch_db_unavailable_returns_503 + test_batch_extra_columns_warn_ignored"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-09-23
status: complete
plan_head_before: 00e853d166162eb4b6d028b093d1421df429cbf9
commits: 2
---

# Phase 03 Plan 03: Batch Expansion + Full-Record Logging Summary

**Hardened POST /batch_predict with 5MB/10k-row 413 guards, warn-ignored extras, typed row/count/version response, and per-row timestamped single-commit Postgres logging — 45-test suite green**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-23T07:00:00Z
- **Completed:** 2026-09-23T07:15:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Batch route hardened per D-07/D-08 and T-03-07→T-03-09: byte cap checked on raw upload, row cap counted pre-parse, lineage/target dropped via imported constants, missing columns 422, extras warn-ignored, all-rows-validated-first with first-offender row number, single commit
- D-04 full record proven: every PredictionLog row carries all 24 request fields plus prediction, probability, model_version 9, and a non-null created_at stamped per row
- 7 new tests pin the contract (valid batch count/items, row-3 rejection with zero writes, missing column, 413 oversize, extras ignored, full-record shape, batch 503); API file 19 passed, full suite 45 passed
- db.py review clean: add-all-then-single-commit, no per-row commits, no raw/f-string SQL in api/, retry only around create_tables, DATABASE_URL value never logged

## Task Commits

Each task was committed atomically:

1. **Task 1: Add all-or-nothing /batch_predict CSV route** - `7566086` (feat)
2. **Task 2: Cover batch semantics and full-record logging with tests** - `d243235` (test)
3. **Task 3: Hold the full suite green with batch wired in** - no code changes (review-only; no commit)

## Files Created/Modified

- `api/schemas.py` - Added BatchPredictionItem (row, prediction, probability) and BatchPredictionResponse (predictions, count, model_version)
- `api/app.py` - MAX_BATCH_BYTES/MAX_BATCH_ROWS 413 guards, decode/row-count-before-parse, explicit DROP_COLS drop, warn-ignore extras, typed batch response, per-row created_at stamp
- `api/db.py` - created_at gains a client-side `default=datetime.now` mirroring server_default=func.now()
- `tests/conftest.py` - `_batch_csv_from_rows` helper, valid_batch_csv (5 rows), bad_row_batch_csv (row 3 rbc=ripe) fixtures
- `tests/test_api.py` - 7 new tests: count/items, row-3 zero-write rejection, missing column, 413 oversize, extras ignored, full-record row shape, batch 503

## Decisions Made

- Unexpected batch columns warn-logged and ignored (mirroring the train.py extras pattern) rather than 422: T-03-08's mitigation is "warn-logged and ignored never fed to the pipeline" — 03-02's strict rejection was the deviation, now corrected.
- created_at stamped per row in `_log_predictions` plus the column-level client default: column `default=` only fires at flush, so mocked-session captures still saw None; explicit stamping makes every row instance carry its D-04 timestamp in all environments.
- Kept the single shared `session.commit()` call site in `_log_predictions` instead of the plan acceptance text ("exactly 2, one per prediction route"): the atomicity guarantee (one commit per request, zero on rejection) is identical with less duplication — see deviations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Stamped created_at per row in app code**
- **Found during:** Task 2 (full-record logging test)
- **Issue:** Plan requires the mocked-session capture to assert a non-null created_at, but column `default=` fires only at DB flush — in-memory instances (and every mocked capture) still read None, so the test failed on first run (11 passed, 1 failed).
- **Fix:** `_log_predictions` passes `created_at=datetime.datetime.now()` on every PredictionLog construction (kept the column-level default as the real-INSERT fallback).
- **Files modified:** api/app.py, api/db.py
- **Verification:** test_batch_logged_rows_carry_full_record passes; full API file green.
- **Committed in:** d243235 (part of task commit)

**2. [Rule 1 - Bug] Softened 03-02's unexpected-column 422 to warn-and-ignore**
- **Found during:** Task 1 (column handling)
- **Issue:** 03-02 rejected unexpected columns with 422, but the plan and T-03-08 require warn-logged-and-ignored (train.py extras pattern); extras must never reach the pipeline but must not reject the batch.
- **Fix:** `log.warning` + select COLUMN_ORDER; added test_batch_extra_columns_warn_ignored.
- **Files modified:** api/app.py, tests/test_api.py
- **Verification:** extras test returns 200 with count 5 and 1 commit.
- **Committed in:** 7566086 / d243235

**3. [Acceptance-text deviation] One shared commit call site, not two**
- **Found during:** Task 3 (write-path review)
- **Issue:** Plan acceptance says "commit call sites in api/app.py number exactly 2, one per prediction route", but both routes share `_log_predictions` with a single `session.commit()` — the design 03-02 established and all tests pin.
- **Fix:** None in code (intentional): per-request behavior is exactly one commit on success and zero on rejection for both routes, verified by commit-count assertions on both /predict and /batch_predict tests. Duplicating the commit per route would add code to satisfy a count, not a property.
- **Files modified:** none
- **Verification:** grep shows one `.commit(` site; mock_session.commit.call_count == 1 asserted in valid-batch, single-predict, and log-row tests; == 0 in both rejection tests.

---

**Total deviations:** 3 (1 missing-critical, 1 bug, 1 acceptance-text clarification)
**Impact on plan:** All required for the plan's own acceptance criteria or for avoiding gratuitous duplication. No scope creep beyond the batch/logging contract.

## Threat Flags

None — no new trust boundaries. The batch upload boundary (T-03-07→T-03-09) and SQL boundary (T-03-11) mitigations from the plan threat register are all implemented and test-pinned; grep confirms no raw/f-string SQL in api/ and DATABASE_URL values never logged.

## Issues Encountered

- PowerShell `grep` with a quoted alternation pattern hung past the 120s tool timeout; switched to the dedicated content-search tool for the Task 3 SQL/commit scans — no impact on the repo.
- Full suite takes ~57s (MLflow-backed training/registry tests dominate); API file alone runs in <1s.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-04 unblocked: /predict + /batch_predict hardened with Claim-4 stamping; /health + /model_info report pinned v9 for Compose healthchecks and the Streamlit client.
- Phase 5 drift reads can rely on the D-04 contract: 24 request fields + prediction + probability + model_version + created_at on every row, single-commit atomic batches.
- Watch item: row cap (10k) and byte cap (5MB) are constants at the top of api/app.py if Compose/Streamlit needs them surfaced.

## Self-Check: PASSED

- FOUND: api/schemas.py, api/app.py, api/db.py, tests/conftest.py, tests/test_api.py
- FOUND: 7566086, d243235 (git log)
- Suite: tests/test_api.py 19 passed; full suite 45 passed, 0 failed

---
*Phase: 03-prediction-api-containerization*
*Completed: 2026-09-23*
