---
phase: 1-data-pipeline
plan: "03"
subsystem: testing
tags: [pytest, pandas, sklearn, great-expectations, tmp_path, synthetic-data]

# Dependency graph
requires:
  - phase: 1-data-pipeline plan 01
    provides: GX 1.x run_raw_validation runner interface that validation tests import
provides:
  - Ingestion quirk normalization pinned by synthetic-CSV tests
  - summarize() shape/ordering pinned independent of the real CSV
  - save_outputs() isolated round-trip with real-dir protection
  - Validation-gate accept plus three reject cases
  - Full suite green (13 passed) with zero real-dataset dependency
affects: [phase-2 model training (consumes pipeline outputs), phase-5 drift/retraining]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 2089
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns: [synthetic-frame plus tmp_path pytest idiom, config redirect via monkeypatched load_config plus cache_clear, gate accept/reject via in-memory frames]

key-files:
  created: [tests/test_ingestion.py, tests/test_save_outputs.py, tests/test_validation.py]
  modified: []

key-decisions:
  - "Good validation frame sized at 320 rows to satisfy the suite's 300-500 row-count range (a 40-row frame would fail the range expectation)"
  - "Real processed-dir protection proven by mtime/size snapshot comparison, not just git status (dir was already untracked)"

patterns-established:
  - "Synthetic-only tests: no new test reads the real CSV; kidney_disease and data/raw appear zero times across new files"
  - "Config redirect: deepcopy real config, override one key, cache_clear, monkeypatch at the consuming module attribute"

requirements-completed: [FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-1.7]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Ingestion quirk normalization pinned (? markers, whitespace/tab stripping, numeric-as-string) via synthetic CSV"
    requirement: "FR-1.1"
    verification:
      - kind: unit
        ref: "tests/test_ingestion.py#test_question_mark_cells_load_as_missing + test_whitespace_and_tab_affixes_stripped"
        status: pass
    human_judgment: false
  - id: D2
    description: "summarize() column set, descending missing_pct sort, and 0-100 bounds pinned"
    requirement: "FR-1.2"
    verification:
      - kind: unit
        ref: "tests/test_ingestion.py#test_summarize_shape_sorted_and_bounded"
        status: pass
    human_judgment: false
  - id: D3
    description: "Config-driven raw path (FR-1.7) proven via override yaml plus monkeypatched load_config"
    requirement: "FR-1.7"
    verification:
      - kind: unit
        ref: "tests/test_ingestion.py#test_config_override_redirects_default_path"
        status: pass
    human_judgment: false
  - id: D4
    description: "save_outputs() isolated round-trip: 4 artifacts under tmp_path, row conservation, reloadable joblib, real dir untouched"
    requirement: "FR-1.6"
    verification:
      - kind: integration
        ref: "tests/test_save_outputs.py#test_save_outputs_round_trip_isolated"
        status: pass
    human_judgment: false
  - id: D5
    description: "Validation gate accepts good frame and rejects unknown-label, missing-target-column, and tiny frames"
    requirement: "FR-1.1"
    verification:
      - kind: unit
        ref: "tests/test_validation.py (4 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full suite green with no real-dataset dependency (FR-1.3 through FR-1.5 via re-run pre-existing tests)"
    requirement: "FR-1.3"
    verification:
      - kind: unit
        ref: ".\\venv\\python.exe -m pytest tests/ -q => 13 passed"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-09-19
status: complete
---

# Phase 1 Plan 03: Pytest Expansion Summary

**Synthetic-only pytest expansion pinning quirk normalization, summarize shape, isolated save_outputs round-trip, and gate accept/reject — 13 passed, real output dir untouched**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-19T16:15:00Z
- **Completed:** 2026-09-19T16:27:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Quirky synthetic CSV (bare/padded `?`, padded whitespace, tabbed labels, numeric-as-string) loads with quirks normalized through the real `load_raw_data`
- `summarize()` column set, descending `missing_pct` sort, and 0–100 bounds pinned independent of the real CSV
- `save_outputs()` writes 3 CSVs plus reloadable `.joblib` into an isolated tmp dir with exact row conservation; real `data/processed/` byte-identical before and after
- Validation runner accepts a good 320-row synthetic frame and rejects unknown-label, missing-target-column, and 2-row frames with `success False`, never raising
- Full suite (`.\venv\python.exe -m pytest tests/ -q`) green: **13 passed** (4 pre-existing + 9 new), zero references to the real CSV

## Task Commits

Each task was committed atomically:

1. **Task 1: Ingestion quirk tests plus summarize and config-override tests** - `c2d0f77` (test)
2. **Task 2: save_outputs() tmp_path integration test with real-dir protection** - `9cf0321` (test)
3. **Task 3: Validation-gate accept/reject tests plus full-suite green** - `97f6812` (test)

## Files Created/Modified

- `tests/test_ingestion.py` - Quirk normalization, summarize shape, config-override tests (4 tests)
- `tests/test_save_outputs.py` - Isolated save_outputs round-trip with real-dir snapshot guard (1 test)
- `tests/test_validation.py` - Gate accept plus three reject cases via sys.path runner import (4 tests)

## Decisions Made

- Good validation frame sized at 320 rows (mirroring the 01-01 probe) because the suite's `ExpectTableRowCountToBeBetween(300, 500)` rejects the plan's nominal "at least 40 rows" — documented here, not a plan change.
- Real-dir protection asserted by mtime/size snapshot inside the test (stronger than git status, since `data/processed/` was already untracked pre-existing state).
- Reworded a docstring (`load_raw_data/summarize` contained a `data/` substring) to hold the test_ingestion.py no-`data/`-literal acceptance criterion.

## Deviations from Plan

None - plan executed exactly as written. (The docstring reword above is a same-file acceptance-criteria satisfaction, not a deviation: no behavior, scope, or file change beyond the plan.)

## Issues Encountered

None. First-run passes on all three files after a pre-write behavior probe confirmed `?` → NA, tab-strip, and pandas int inference on the quirky frame.

## Threat Flags

None — no new surface beyond the plan's threat model. T-1-07 mitigated (tmp_path redirect + snapshot proof + clean `git status --short data/processed/` modulo pre-existing untracked state); T-1-08 mitigated (tests call real `load_raw_data`, zero regex literals); T-1-09 mitigated (`kidney_disease`/`data/raw` grep clean); T-1-SC holds (no installs).

## Known Stubs

None.

## Self-Check: PASSED

- `tests/test_ingestion.py`, `tests/test_save_outputs.py`, `tests/test_validation.py` exist.
- `c2d0f77`, `9cf0321`, `97f6812` all present in `git log`.
- Full suite re-run at summary time: 13 passed.

## Next Phase Readiness

- Phase 1 test layer complete: quirk handling, output persistence, and the validation gate are all regression-guarded for Phase 2 consumption.
- No blockers. No modifications to `src/`, `data/validation/`, `notebooks/`, `STATE.md`, or `ROADMAP.md`.

---
*Phase: 1-data-pipeline plan 03*
*Completed: 2026-09-19*
