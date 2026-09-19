# Conventions — Corvus

> Last mapped: 2026-09-19

## Code Style

### Python Version Features
- **Python 3.11+** — uses PEP 604 union types (`str | None`) and PEP 585 generics (`list[str]`) in type hints
- No type checker configured (no `mypy.ini`, `pyproject.toml [tool.mypy]`, or `pyrightconfig.json`)
- Type hints are used in function signatures but not exhaustively

### Naming Conventions
- **Modules**: `snake_case` (e.g., `load_data.py`, `preprocess.py`)
- **Functions**: `snake_case` (e.g., `load_raw_data()`, `clean_raw()`, `fit_transform_split()`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `NUMERIC_COLS`, `CATEGORICAL_COLS`, `PROJECT_ROOT`)
- **Private functions**: Single underscore prefix (e.g., `_clean_target()`, `_to_dataframe()`)
- **Module-level logger**: `log = get_logger()` — consistent across all modules

### Docstrings
- Module-level docstrings: **Present and thorough** — multi-paragraph descriptions explaining purpose, design rationale, and dataset-specific quirks
- Function-level docstrings: **Mixed** — some functions have docstrings (e.g., `summarize()`, `build_pipeline()`), others rely on the module docstring for context
- Style: Google-ish (no formal format like numpy/sphinx, but readable)

### Imports
- Standard library first, then third-party, then internal (`src.`) — follows PEP 8 ordering
- Internal imports use absolute paths: `from src.utils.config import load_config, PROJECT_ROOT`
- No `__all__` exports in `__init__.py` files (all empty)

## Architectural Patterns

### Configuration Pattern
```python
# Every module that needs config:
from src.utils.config import load_config, PROJECT_ROOT
cfg = load_config()  # cached via @lru_cache(maxsize=1)
path = cfg["data"]["raw_path"]
```
- Single YAML file, single load function, LRU-cached
- Paths resolved relative to `PROJECT_ROOT` at load time
- No environment variable overrides, no `.env` loading, no config merging

### Logging Pattern
```python
from src.utils.logger import get_logger
log = get_logger()
log.info(f"Loaded raw data: {df.shape[0]} rows x {df.shape[1]} cols from {path}")
```
- Loguru (not stdlib `logging`)
- Configured once on first `get_logger()` call via module-level `_configured` flag
- Dual sink: `sys.stderr` + `logs/corvus.log` (5 MB rotation, 5 file retention)

### Entry Point Pattern
```python
def main():
    # orchestrate the module's pipeline steps
    ...

if __name__ == "__main__":
    main()
```
- Modules invoked as: `python -m src.ingestion.load_data`
- `main()` function is the public entry point; all logic in named functions above it

### Error Handling Pattern
- `FileNotFoundError` with helpful messages pointing to config
- `ValueError` for config-data mismatches (e.g., positive label not found)
- `log.warning()` for non-fatal issues (e.g., unclassified columns)
- No custom exception classes

### Data Transformation Pattern
- **Immutable input**: functions take a DataFrame and return a new one (`df = df.copy()`)
- **Config-driven**: column lists, strategies, split ratios all from `config.yaml`
- **Leak-safe**: split happens before any fitting; pipeline fitted on train only
- **Artifact output**: fitted pipeline serialized as `.joblib`; transformed data as `.csv`

## File Organization

### Source Modules (`src/`)
- One primary Python file per module (e.g., `load_data.py`, `preprocess.py`)
- `__init__.py` files are empty — no re-exports
- Cross-module dependency: `preprocess.py` → `ingestion.load_data`

### Tests (`tests/`)
- Pytest-based
- Fixtures create synthetic data shaped like UCI CKD (no dependency on real dataset)
- Test names describe what they assert: `test_split_before_fit_no_overlap`, `test_pipeline_is_single_sklearn_object`

### Documentation
- `README.md` — quick-start + folder overview
- `CORVUS_FINAL_GUIDE.md` — comprehensive dev guide with patent tracking, timeline, risk register
- `dataset_analysis.md` — analysis of 11 candidate dataset files

## What's NOT Established Yet

- **No linter/formatter config** (no `ruff.toml`, `.flake8`, `black` in requirements)
- **No pre-commit hooks** (no `.pre-commit-config.yaml`)
- **No CI pipeline** (no `.github/workflows/`)
- **No Makefile or task runner** (no `Makefile`, `invoke`, `nox`, `tox`)
- **No dependency locking** (no `requirements-lock.txt`, `poetry.lock`, `uv.lock`)
