# Phase 1 Data Pipeline — Verification Report

**Phase:** 1-data-pipeline — **Verdict:** PASSED
**Verified:** 2026-09-19 — **Score:** 14/14 must-haves verified
**Plans verified:** 01-01 (GX validation gate) · 01-02 (EDA notebook) · 01-03 (pytest expansion)

## 1. Plan ↔ SUMMARY ↔ Commit Match

| Plan | SUMMARY self-check | Commits claimed | In `git log --oneline` |
|---|---|---|---|
| 01-01 | PASSED | `d7bf95c` (gate slice + suite + wiring), `0ea71ef` (docstring sweep fix) | both present |
| 01-02 | PASSED | `1a58870` (skeleton + missingness), `f04d986` (distributions + correlation) | both present |
| 01-03 | PASSED | `c2d0f77` (ingestion tests), `9cf0321` (save_outputs test), `97f6812` (validation tests) | all three present |

All three SUMMARY.md files state `Self-Check: PASSED`. All 7 claimed hashes verified
present in `git log --oneline` on `main`. `git ls-files` confirms every promised
artifact is tracked: `data/validation/ckd_suite.json`, `data/validation/validate.py`,
`src/preprocessing/preprocess.py` (gate wiring), `notebooks/01_eda_ckd.ipynb`,
`tests/test_ingestion.py`, `tests/test_save_outputs.py`, `tests/test_validation.py`.

## 2. Goal-Backward Check (ROADMAP Phase 1 Remaining Items)

| Remaining item | Delivered as | Evidence |
|---|---|---|
| EDA notebook — distributions, correlations, missing-value heatmap | `notebooks/01_eda_ckd.ipynb`, 11 cells (4 md + 7 code), committed with **0 stored outputs / 0 tracebacks** | cell/output counts probed from notebook JSON (see §4) |
| Great Expectations validation schema | `data/validation/ckd_suite.json` — 9 version-agnostic `{expectation_type, kwargs}` dicts | file read: columns-match (exact_match false), label domain, not-null, row-count 300–500 range, 5 non-null-proportion floors |
| Additional test coverage (ingestion + `save_outputs()` integration) | `tests/test_ingestion.py` (4 tests), `tests/test_save_outputs.py` (1 test), `tests/test_validation.py` (4 tests) | full suite: **13 passed** (4 pre-existing + 9 new) |

### Core invariants (all hold)

- **Leak-safe split-first ordering untouched:** gate call site is a single `run_raw_validation`
  call at `preprocess.py:219`, ordered `load_raw_data() (210)` → gate (219) → `clean_raw() (222)`.
  Exactly 1 call site. Split/fit/save bodies unchanged (4 pre-existing tests green).
- **Single sklearn Pipeline Claim-2 artifact preserved:** pre-existing Pipeline-type +
  no-NaN tests pass inside the 13-test green run.
- **Notebook read-only:** imports `load_raw_data`/`summarize`/`clean_raw` + `NUMERIC_COLS`/
  `CATEGORICAL_COLS` from `src.*`; forbidden-logic scan (`.fit(`, `fit_transform`,
  `get_dummies`, `os.system`, `!pip`) clean; committed outputs-free.
- **Tests synthetic + `tmp_path` isolated:** `kidney_disease` / `data/raw` grep across the
  three new test files returns zero hits; real `data/processed/` untouched by design
  (tmp_path redirect).

## 3. Must-Haves Verification (14/14)

### Plan 01-01 (5/5)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Runner vs real CSV exits 0 | ✓ VERIFIED | `.\venv\python.exe data/validation/validate.py` → `RAW VALIDATION PASSED`, EXIT=0 (re-run by verifier, §4) |
| 2 | Synthetic bad frame exits non-zero, no traceback | ✓ VERIFIED | `run_raw_validation` wraps data failures fail-closed (`SimpleNamespace(success=False)`); reject behavior pinned by 3 tests in `test_validation.py`, all passing |
| 3 | `main()` aborts before `clean_raw` on failure, completes on pass | ✓ VERIFIED | gate at line 219 precedes `clean_raw` at 222; `SystemExit` path present in source |
| 4 | 4 pre-existing tests still pass | ✓ VERIFIED | included in the 13-passed suite run |
| 5 | No hard-coded row count / path / stray `.fit` | ✓ VERIFIED | grep over `data/validation/*` for `.fit(`, `fit_transform`, `== 400` → zero hits; all paths via `load_config` |

### Plan 01-02 (4/4)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Notebook shows distributions, correlation heatmap, missingness heatmap from real CSV | ✓ VERIFIED | 11 cells; hemo-KDE + rbc-count + masked correlation (`vmin -1 vmax 1 center 0`) + missing bar/heatmap sections present per SUMMARY; `load_raw_data()` no-arg call confirmed |
| 2 | Missingness numbers match `summarize()` exactly | ✓ VERIFIED | notebook displays `summarize(eda_df)` output directly as single source of truth (no recomputation) |
| 3 | Executes top-to-bottom without error | ✓ VERIFIED | SUMMARY records `nbconvert --execute` exit 0; file parses as JSON with 11 cells (verifier re-parsed) |
| 4 | No mutating/fitting logic, no duplicated quirk handling | ✓ VERIFIED | forbidden-logic scan clean (re-run by verifier, §4) |

### Plan 01-03 (5/5)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Quirky synthetic CSV normalizes, no regex duplicated | ✓ VERIFIED | `test_ingestion.py` quirk tests pass; no regex literal in test file per plan acceptance |
| 2 | `summarize()` shape/ordering pinned independent of real CSV | ✓ VERIFIED | shape/sort/bounds test passes on synthetic frame |
| 3 | `save_outputs()` isolated round-trip, row conservation, real dir untouched | ✓ VERIFIED | `test_save_outputs.py` passes (4 artifacts under tmp_path, counts sum, joblib reloads) |
| 4 | Gate accepts good frame, rejects 3 bad frames | ✓ VERIFIED | `test_validation.py` 4 tests pass |
| 5 | Full suite green, no real-dataset dependency | ✓ VERIFIED | `.\venv\python.exe -m pytest tests/ -q` → **13 passed** (verifier re-run, §4) |

## 4. Test Evidence (verifier-executed, not SUMMARY claims)

**Command:** `.\venv\python.exe -m pytest tests/ -q`
**Output:** `.............  [100%]` → **13 passed in 8.95s**
**Result:** GREEN — no FAILED, no ERROR. Matches SUMMARY claim (13 = 4 pre-existing + 9 new).

**Command:** `.\venv\python.exe data/validation/validate.py`
**Output:** `Loaded raw data: 400 rows x 26 cols … Raw-data validation success=True` →
`RAW VALIDATION PASSED`, **EXIT=0**. Matches plan 01-01 acceptance criterion.

**Notebook probe:** cells 11, stored outputs 0, tracebacks 0,
`load_raw_data`/`summarize`/`clean_raw` all imported, forbidden-token violations `[]`.

**Grep probes:** forbidden patterns in `data/validation/*` → zero hits;
`kidney_disease`/`data/raw` in new tests → zero hits;
`run_raw_validation` call sites in `preprocess.py` → exactly 1 (line 219).

## 5. Requirements Spot-Check (FR-1.1 → FR-1.7)

| Req | Traceable to | Status |
|---|---|---|
| FR-1.1 quirk ingestion | `src/ingestion/load_data.py` + `test_ingestion.py` quirk tests + GX suite + `test_validation.py` | ✓ satisfied |
| FR-1.2 quality summary | `summarize()` + notebook display + summarize-shape test | ✓ satisfied |
| FR-1.3 label cleaning | `clean_raw()` + pre-existing clean test (green) | ✓ satisfied |
| FR-1.4 leak-safe split-first | `split_raw()` before fit + disjointness test (green) | ✓ satisfied |
| FR-1.5 single Pipeline, train-only fit | `fit_transform_split()` + Pipeline-type/no-NaN tests (green) | ✓ satisfied |
| FR-1.6 `.joblib` + CSV outputs | `save_outputs()` + isolated round-trip test (green) | ✓ satisfied |
| FR-1.7 config-driven | `config/config.yaml` + `load_config` everywhere + config-override test (green) | ✓ satisfied |

## GAPS

None. No blockers, no warnings, no human-verification items outstanding.
(Untracked `??` entries in `git status` are pre-existing repo files never committed —
outside Phase 1 scope; all Phase 1 deliverables are tracked. `reports/figures/` PNGs
are gitignored runtime outputs per plan contract, not missing artifacts.)

---

_Verifier: gsd-verifier · Method: goal-backward, SUMMARY claims re-executed on disk_
