# Phase 1 Plan 01: GX Validation Gate Tracer Summary

**Phase:** 1-data-pipeline — **Plan:** 01 — **Status:** complete
**Date:** 2026-09-19 — **Requirements:** FR-1.1, FR-1.7

## One-liner

Raw-CSV validation gate proven end-to-end on GX 1.x only: persisted 9-expectation suite JSON, thin `run_raw_validation` runner, fail-fast wiring in `preprocess.main()`, real CSV exits 0, bad frames rejected without traceback, 4 existing tests still green.

## Interpreter + GX smoke evidence (plan acceptance criterion)

- `.\venv\python.exe --version` → **Python 3.11.0** (project interpreter used for every command; system Python untouched).
- `.\venv\python.exe -c "import great_expectations as gx; print(gx.__version__)"` → **1.23.1**.
- GX 1.x call-shape smoke run against installed 1.23.1 (before freezing the runner): `gx.get_context()` → `data_sources.add_pandas` → `add_dataframe_asset` → `add_batch_definition_whole_dataframe` → `get_batch(batch_parameters={"dataframe": df})` → `batch.validate(suite)` all confirmed working; all six needed `gx.expectations` classes confirmed present (`ExpectTableColumnsToMatchSet`, `ExpectColumnValuesToBeInSet`, `ExpectColumnValuesToNotBeNull`, `ExpectTableRowCountToBeBetween`, `ExpectColumnProportionOfNonNullValuesToBeBetween`).
- One API ordering fact discovered by the smoke runs (not in research): `gx.ExpectationSuite(name=...)` requires an **active** data context, so the runner calls `gx.get_context()` **before** building the suite (deviation 2).

## What was built

**`data/validation/ckd_suite.json`** (9 version-agnostic `{expectation_type, kwargs}` dicts):
- `ExpectTableColumnsToMatchSet`: full 26-column set, `exact_match: false`.
- `ExpectColumnValuesToBeInSet`: `classification` ∈ {`ckd`, `notckd`} (post-strip domain from `load_raw_data`).
- `ExpectColumnValuesToNotBeNull`: `classification`.
- `ExpectTableRowCountToBeBetween`: 300–500 (range; no exact-400 assertion anywhere).
- 5× `ExpectColumnProportionOfNonNullValuesToBeBetween` floors derived from live `summarize()` output, missing fractions rounded **up**: rbc 38.00% → min 0.60, rc 32.75% → 0.65, wc 26.50% → 0.70, pot 22.00% → 0.75, sod 21.75% → 0.75.

**`data/validation/validate.py`** — `run_raw_validation(df=None)` returning the GX result (carries `success` bool):
- `df=None` loads via `load_raw_data(raw_path=cfg["data"]["raw_path"])`; suite read from `Path(cfg["data"]["validation_dir"]) / "ckd_suite.json"` — all paths via `load_config`, zero hard-coded paths/counts, zero `.fit` calls.
- Minimal import guard only: `RuntimeError` with install hint when `great_expectations` is not importable — no parallel hand-rolled validator.
- Data failures fail closed (`success=False` result, no traceback); `__main__` prints one line and exits 0/1.

**`src/preprocessing/preprocess.py`** — `main()` only: gate block between `load_raw_data()` (line 210) and `clean_raw()` (line 222), single `run_raw_validation` call site (line 219), loaded via `importlib` file-location anchored at `PROJECT_ROOT` + `cfg data.validation_dir` (no `data.validation` package import — `data/` has no `__init__`); `SystemExit` before clean/split on failure.

## Verification results

| Check | Result |
|---|---|
| `.\venv\python.exe data/validation/validate.py` on real CSV | exit **0**, `RAW VALIDATION PASSED`, no Traceback/ModuleNotFoundError/AttributeError — PASS |
| `.\venv\python.exe -m pytest tests/test_preprocessing.py -x -q` | **4 passed** (before + after every edit) — PASS |
| Negative-path probe (TEMP script, not committed): bad label `maybe` / missing `classification` col / 2-row frame | all `success False`, no traceback — PASS |
| Good synthetic 320-row frame (all 26 cols, ckd/notckd, no missing) | `success True` — PASS |
| Fail-fast probe: `main()` with monkeypatched bad frame | `SystemExit`, `clean_raw` never reached — PASS |
| Good-path probe: real `main()` end-to-end | completed (`train 281 / val 38 / test 81` rows, pipeline joblib written to gitignored `data/processed/`) — PASS |
| Forbidden-pattern sweeps over `data/validation/*.py,*.json` (`fit(`/`fit_transform`; `data/` literals / `400` / `exact_match…true`) | **zero hits** both — PASS |
| Suite length probe | **9** — PASS |
| `run_raw_validation` call sites in `preprocess.py` | exactly **1**, ordered load (210) → gate (219) → clean (222) — PASS |

## Commits

| Task | Message | Hash |
|---|---|---|
| Tracer — gate slice + suite + wiring | `feat(01-01): end-to-end GX 1.x validation gate slice plus suite JSON plus main wiring` | `d7bf95c` |
| Negative-path proof + sweep fix | `fix(01-01): remove data-path literal from validate.py docstring after forbidden-pattern sweep` | `0ea71ef` |

Staged per commit with `git add` on plan files only (never `-A`). No changes to `STATE.md`, `ROADMAP.md`, or `notebooks/`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Script-mode `ModuleNotFoundError: No module named 'src'`**
- **Found during:** Tracer task, first runner invocation.
- **Issue:** The plan's literal verify command (`venv/python.exe data/validation/validate.py`) runs the file as a script, so `sys.path[0]` is `data/validation/` and the `src.*` imports fail from any cwd.
- **Fix:** Repo-root-anchored bootstrap at top of `validate.py`: `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))` — file-location anchored, not cwd-dependent, no hard-coded path.
- **Commit:** `d7bf95c`.

**2. [Rule 1 — Bug] `ExpectationSuite` built before any GX context exists**
- **Found during:** Tracer task, second runner invocation (`RAW VALIDATION FAILED`, "requires an active data context").
- **Issue:** Runner built the `ExpectationSuite` before calling `gx.get_context()`; GX 1.23.1 requires the context to be active first (confirmed by isolated smoke probe).
- **Fix:** Reordered `run_raw_validation` to `gx.get_context()` first, then build suite. GX 1.x-only flow unchanged.
- **Commit:** `d7bf95c`.

**3. [Rule 2 — Correctness] Docstring contained a `data/` path literal**
- **Found during:** Task 2 forbidden-pattern sweep.
- **Issue:** Module docstring quoted the invocation as ``python data/validation/validate.py`` — a `data/` literal that a naive path-grep (e.g. plan 01-03) would flag.
- **Fix:** Reworded to "invoking this runner as a script" (one-line change, no behavior delta).
- **Commit:** `0ea71ef`.

**Notes (not deviations):** PowerShell form `.\venv\python.exe` used throughout (same file as plan's `venv/python.exe`). The "byte-identical via git diff" acceptance check was established by construction instead: `src/preprocessing/preprocess.py` had no committed baseline (untracked), the single scoped `Edit` touched only `main()`, and the 4-test suite (which covers split/fit/save behavior) stayed green. Probe scripts lived in `%TEMP%` and were deleted; `data/validation/__pycache__` removed; full `main()` good-path run wrote only to gitignored `data/processed/`.

## Threat flags

None — no new surface beyond the plan's threat model. T-1-01 mitigated (fail-fast `SystemExit` before `clean_raw`, negative-path proven); T-1-02 mitigated (all paths via `load_config` + `PROJECT_ROOT` anchoring, sweep-verified zero literals); T-1-03 accepted per plan (own-pipeline joblib only); T-1-SC holds (no new packages installed).

## Known stubs

None.

## Self-Check: PASSED

- `data/validation/ckd_suite.json`, `data/validation/validate.py` exist; `src/preprocessing/preprocess.py` gate block present (lines 210–222).
- `d7bf95c`, `0ea71ef` both present in `git log`.
- Working tree contains no executor-created files outside the plan's scope (remaining `??` entries are pre-existing untracked repo files).
