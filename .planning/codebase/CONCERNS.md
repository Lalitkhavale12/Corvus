# Concerns — Corvus

> Last mapped: 2026-09-19

## Critical Concerns

### 1. No Dependency Locking
**Severity: Medium** | **Phase: Now**

`requirements.txt` uses `>=` lower bounds with no upper pins or lockfile. Today's install may produce different package versions next month, potentially breaking the pipeline.

**Evidence**: `pandas>=2.0` could install pandas 3.x; `scikit-learn>=1.3` could install 2.x — both have had breaking API changes in major versions.

**Recommendation**: Generate `requirements-lock.txt` via `pip freeze` or adopt `uv`/`pip-tools`. Keep `requirements.txt` as the loose spec and lock for reproducibility.

---

### 2. LRU Cache on `load_config()` Prevents Runtime Config Changes
**Severity: Low (now) → Medium (Phase 4+)** | **Phase: Now**

`load_config()` uses `@lru_cache(maxsize=1)`, which means config is loaded exactly once per process. This is fine for batch scripts but becomes a problem when:
- FastAPI (Phase 4) needs config changes without restarting
- Tests need to override config values

**Evidence**: `src/utils/config.py:10` — `@lru_cache(maxsize=1)` on `load_config()`.

**Recommendation**: Consider adding a `load_config.cache_clear()` call in test fixtures, or switching to a config object that supports reloading.

---

### 3. Hardcoded Column Lists in `preprocess.py`
**Severity: Low** | **Phase: Now**

`NUMERIC_COLS` and `CATEGORICAL_COLS` are hardcoded module-level constants in `preprocess.py`. If the dataset changes, these must be manually updated. The docstring acknowledges this, but it's easy to miss.

**Evidence**: `src/preprocessing/preprocess.py:44-50`.

**Recommendation**: Move column lists to `config.yaml` under a `columns:` section, or auto-detect from dtype analysis in `clean_raw()`.

---

### 4. No Input Validation on Config Values
**Severity: Low** | **Phase: Now**

`load_config()` returns a raw dict with no schema validation. A typo in `config.yaml` (e.g., `taret_column` instead of `target_column`) would surface as a `KeyError` deep in processing code rather than at load time.

**Evidence**: `config.py` does `cfg["data"]["raw_path"]` without checking keys exist.

**Recommendation**: Add a `pydantic.BaseModel` or `dataclass` config schema (pydantic is already in `requirements.txt` for Phase 4).

---

## Moderate Concerns

### 5. Logger Module-Level State (`_configured` Flag)
**Severity: Low** | **Phase: Testing**

`logger.py` uses a module-level `_configured` boolean to prevent reconfiguration. This makes testing logger behavior difficult (can't reset between tests) and could cause issues if `get_logger()` is called before the import system is fully loaded.

**Evidence**: `src/utils/logger.py:8` — `_configured = False` at module level.

---

### 6. No `.gitkeep` Files in Some Empty Directories
**Severity: Low** | **Phase: Now**

`api/`, `frontend/`, `docker/`, `airflow/`, `notebooks/` are empty directories that will be lost if cloned fresh (git doesn't track empty dirs). `models/` has a `.gitkeep`, but others don't.

**Recommendation**: Add `.gitkeep` to all empty placeholder directories.

---

### 7. Small Dataset Implications
**Severity: Medium** | **Phase: 2–9**

The primary dataset (UCI CKD) has only **400 rows**. This creates downstream challenges:
- Model evaluation metrics will have high variance
- Cross-validation may produce unstable results
- Drift detection (Phase 8) may trigger false positives or negatives
- Auto-retraining (Phase 9) needs simulated data streams

**Mitigation (already planned)**: UCI-857 (200 rows, Bangladeshi cohort) will be used as simulated incoming batch for drift detection. Dataset analysis (`dataset_analysis.md`) has already evaluated and rejected several synthetic alternatives.

---

### 8. `preprocess.py` Imports from `ingestion` — Tight Coupling
**Severity: Low** | **Phase: Refactoring**

`preprocess.py` directly imports `load_raw_data` from `src.ingestion.load_data`. This couples preprocessing to the ingestion module. If preprocessing needs to run on data from a different source (e.g., API request, Airflow task), this import becomes an obstacle.

**Recommendation**: `main()` in `preprocess.py` should accept a DataFrame parameter, making the ingestion import optional (only needed for CLI execution).

---

## Technical Debt Tracker

| Item | Severity | Phase Introduced | Blocks Phase | Notes |
|---|---|---|---|---|
| No lockfile | Medium | 1 | Any rebuild | `pip freeze` would take 30 seconds |
| No linter/formatter | Low | 1 | — | Code is clean but not enforced |
| No pre-commit hooks | Low | 1 | Phase 6 (CI) | CI should match local checks |
| No `conftest.py` | Low | 1 | Phase 2 (more tests) | Shared fixtures needed |
| Empty `__init__.py` files | None | 1 | — | By design for namespace packages |
| No `src/visualization/` | Medium | 1 | Component 102 | Patent requirement, tracked in guide |
| Matplotlib/seaborn installed but unused | None | 1 | — | Pre-installed for Phase 2 EDA |

## Security Considerations

1. **No secrets management** — `.env` is gitignored but no dotenv loading exists. Phase 4+ (database, MLflow server, API auth) will need environment variable handling.
2. **No input sanitization for API** — not relevant yet (Phase 4), but FastAPI + Pydantic will handle this naturally.
3. **Raw data in gitignore** — good practice, data doesn't leak into version control.
4. **No authentication/authorization** — not relevant until Phase 4 (API) and Phase 7 (Grafana).

## Performance Considerations

1. **400-row dataset** — performance is not a concern for Phase 1. Pipeline runs in under a second.
2. **LRU cache on config** — good practice, prevents redundant YAML parsing.
3. **No lazy imports** — all imports are eager. Fine for current codebase size but may slow startup as dependencies grow (especially MLflow, Airflow).
4. **OneHotEncoder can produce sparse matrices** — `_to_dataframe()` handles `.toarray()` conversion, but for larger datasets this could be a memory concern.
