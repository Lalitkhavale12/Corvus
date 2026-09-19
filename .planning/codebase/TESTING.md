# Testing — Corvus

> Last mapped: 2026-09-19

## Testing Framework

| Item | Value |
|---|---|
| Framework | **pytest** ≥ 8.0 |
| Test location | `tests/` (single directory, flat) |
| Test files | 1: `test_preprocessing.py` |
| Total tests | **4** |
| Fixtures | 1: `synthetic_df` — 40-row synthetic UCI CKD-shaped DataFrame |

## Test Inventory

| # | Test Name | What It Asserts | Category |
|---|---|---|---|
| 1 | `test_clean_raw_no_missing_target` | Target column has no NaN after cleaning; values are binary (0/1) | Data integrity |
| 2 | `test_split_before_fit_no_overlap` | Train/val/test index sets are mutually disjoint — no data leakage through shared rows | **Leakage safety** |
| 3 | `test_pipeline_is_single_sklearn_object` | Fitted preprocessing output is an `sklearn.Pipeline` instance; `.transform()` works without `NotFittedError` | **Patent Claim 2** |
| 4 | `test_fit_only_on_train_not_val_or_test` | All three splits have correct row counts; no NaN values survive transformation | Transform completeness |

## Test Design Patterns

### Synthetic Data Strategy
Tests use a **synthetic DataFrame** that mimics UCI CKD structure (14 numeric + 10 categorical columns + target) with 40 rows. This means:
- ✅ Tests don't require the real `kidney_disease.csv` file
- ✅ Tests are fast (no I/O to data directory)
- ✅ Tests are reproducible (deterministic fixture)
- ⚠️ Synthetic data doesn't exercise all UCI-CKD quirks (no `?` markers, no `ckd\t` labels)

### What's Tested vs. Not Tested

| Module | Tested? | Notes |
|---|---|---|
| `src/preprocessing/preprocess.py` | ✅ 4 tests | Core preprocessing pipeline |
| `src/ingestion/load_data.py` | ❌ | No tests for `load_raw_data()`, `summarize()`, or `main()` |
| `src/utils/config.py` | ❌ | No tests for `load_config()` or path resolution |
| `src/utils/logger.py` | ❌ | No tests for logger setup |

### Functions Tested vs. Not Tested

| Function | Tested? |
|---|---|
| `clean_raw()` | ✅ (via `test_clean_raw_no_missing_target`) |
| `split_raw()` | ✅ (via `test_split_before_fit_no_overlap`) |
| `build_pipeline()` | ✅ (indirectly via `test_pipeline_is_single_sklearn_object`) |
| `fit_transform_split()` | ✅ (via tests 3 and 4) |
| `save_outputs()` | ❌ (no I/O test for CSV/joblib writing) |
| `_clean_target()` | ❌ (no direct test for label normalization) |
| `_to_dataframe()` | ❌ (no direct test for sparse matrix conversion) |
| `load_raw_data()` | ❌ |
| `summarize()` | ❌ |

## Test Execution

```bash
# From project root with venv activated:
python -m pytest tests/ -v
```

No custom `pytest.ini`, `conftest.py`, or `pyproject.toml [tool.pytest]` configuration. Tests use default pytest discovery.

## Coverage Analysis

### Estimated Coverage
- **`preprocess.py`**: ~60% line coverage (core happy path tested; edge cases, error paths, and `save_outputs` not tested)
- **`load_data.py`**: 0% (no test file)
- **`config.py`**: 0% direct (exercised indirectly by preprocessing tests calling `load_config()`)
- **`logger.py`**: 0% direct (exercised indirectly)

### Notable Gaps

1. **No integration test** — no test runs the full `main()` pipeline end-to-end with real or realistic data
2. **No negative tests** — no test for missing file errors, invalid config values, empty DataFrames, or column name mismatches
3. **No I/O tests** — `save_outputs()` writes CSVs and joblib but is never tested
4. **No ingestion tests** — `load_raw_data()` handles UCI quirks ("?" replacement, whitespace stripping) but has no dedicated tests
5. **No `conftest.py`** — fixtures are local to `test_preprocessing.py`; will need refactoring when more test files are added

## Recommendations for Phase 2+

1. Add `conftest.py` with shared fixtures (synthetic data, temp directories)
2. Add ingestion tests (UCI quirk handling, missing file error)
3. Add `save_outputs()` integration test (write to temp dir, read back, verify)
4. Consider `pytest-cov` for coverage reporting
5. Add property-based tests with `hypothesis` for preprocessing edge cases
