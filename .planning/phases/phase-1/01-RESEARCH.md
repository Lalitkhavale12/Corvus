# Phase 1: Data Pipeline - Research (FORCE-REFRESH)

**Researched:** 2026-09-19 (refresh — overwrites prior research of same date)
**Domain:** Tabular clinical data pipeline — ingestion, EDA, validation, leak-safe preprocessing, pytest
**Confidence:** HIGH

## Summary

Phase 1 core is built and green: quirk-tolerant ingestion (`src/ingestion/load_data.py`), per-column quality summary (`summarize()`), leak-safe split-first preprocessing producing a single fitted `sklearn.Pipeline` artifact (`src/preprocessing/preprocess.py`), config-driven paths/splits/strategies (`config/config.yaml`), and Loguru logging [VERIFIED: src/ingestion/load_data.py:29-64, src/preprocessing/preprocess.py:105-206, config/config.yaml:1-29]. Remaining work is three bounded items: (1) an EDA notebook in the empty `notebooks/` directory, (2) a Great Expectations validation suite under `data/validation/` (currently only `.gitkeep`), and (3) additional pytest coverage (ingestion tests, `save_outputs()` integration test, validation-gate tests).

**What changed vs prior research:** the two flagged environment risks are now RESOLVED with fresh tool evidence. The project interpreter is `venv/python.exe` = **Python 3.11.0** [VERIFIED: venv/python.exe --version], and it already has **every Phase 1 dependency installed** — pandas 3.0.6, sklearn 1.9.1, matplotlib 3.11.2, seaborn 0.13.2, pytest 9.1.1, **great-expectations 1.23.1** [VERIFIED: venv import probe this session]. The 4 existing tests pass on it [VERIFIED: `4 passed in 3.72s`]. System Python 3.14.6 is therefore **irrelevant** — all work must use `venv/python.exe`, where GX 1.23.1 on Python 3.11 sits inside GX's documented 3.10–3.13 support window [CITED: docs.greatexpectations.io/docs/core/run_validations/run_a_validation_definition]. Consequence: the GX-version branch in prior Plan 01-01 is now unnecessary — **prescribe the GX 1.x API only**, and the hand-rolled fallback is demoted from likely to contingency-only.

The non-negotiable constraints are unchanged: split-before-fit ordering must not regress [VERIFIED: src/preprocessing/preprocess.py:105-127,176], and the single `sklearn.Pipeline` artifact (Patent Claim 2) must be preserved [VERIFIED: src/preprocessing/preprocess.py:130-158]. The EDA notebook is read-only: it imports `load_raw_data`/`summarize`/`clean_raw` rather than duplicating quirk-handling logic.

**Primary recommendation:** Use `venv/python.exe` for everything; build a read-only EDA notebook on existing `load_raw_data`/`summarize` functions (install `jupyter`/`nbconvert` into the venv first — confirmed absent); add a GX 1.x-style expectation suite + thin runner under `data/validation/` validating the *raw* CSV with range-based (never exact-count) expectations; extend pytest with ingestion-quirk tests plus `tmp_path`-based `save_outputs` and gate tests — all without touching split ordering or the single-Pipeline artifact.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FR-1.1 | Ingest raw CSV with automatic handling of UCI CKD quirks ("?" markers, whitespace, dtype coercion) | Implemented [VERIFIED: src/ingestion/load_data.py:40-50]; research adds ingestion-quirk test patterns (§ Validation Architecture, Wave 0 gaps) |
| FR-1.2 | Per-column data quality summary (dtype, missing count, missing %, unique values) | Implemented via `summarize()` [VERIFIED: src/ingestion/load_data.py:54-64]; EDA notebook Pattern N1 reuses it |
| FR-1.3 | Clean target labels, drop rows with no label, drop ID column | Implemented via `clean_raw`/`_clean_target` [VERIFIED: src/preprocessing/preprocess.py:53-102]; no new research needed |
| FR-1.4 | Split train/val/test (70/10/20) before any fitting (leak-safe) | Implemented via `split_raw` [VERIFIED: src/preprocessing/preprocess.py:105-127]; research forbids regression (§ Don't Hand-Roll, Pitfall 1) |
| FR-1.5 | Single `sklearn.Pipeline` (imputer + scaler + encoder) fitted on train only | Implemented via `build_pipeline`/`fit_transform_split` [VERIFIED: src/preprocessing/preprocess.py:130-185]; Patent Claim 2 constraint preserved |
| FR-1.6 | Save pipeline artifact as `.joblib` and transformed splits as CSV | Implemented via `save_outputs` [VERIFIED: src/preprocessing/preprocess.py:188-206]; research adds `tmp_path` integration-test pattern |
| FR-1.7 | All paths, split ratios, strategies configurable via `config/config.yaml` | Config keys verified [VERIFIED: config/config.yaml:3-29]; GX suite and notebook must read the same keys, never hard-code paths |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Raw CSV ingestion + quirk normalization | API / Backend (`src/ingestion/`) | — | Deterministic server-side data loading; no client involvement |
| EDA notebook (distributions, correlations, missingness) | Database / Storage (observational read) | — | Read-only analysis over `data/raw/`; figures to `reports/figures/`, never mutates pipeline outputs |
| Data validation (GX 1.x suite + thin runner) | API / Backend (`data/validation/`) | — | Gate running before preprocessing in DAG order; fails fast on bad raw drops |
| Preprocessing Pipeline artifact | API / Backend (`src/preprocessing/`) | — | Single fitted object for Phase 2 training and Phase 3 inference; Patent Claim 2 owner |
| Processed splits + `.joblib` persistence | Database / Storage (`data/processed/`) | — | File artifacts on disk; written only by `save_outputs` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.6 installed in venv (floor `>=2.0` [VERIFIED: requirements.txt:2]) | Ingestion, `summarize()`, EDA frames | Project standard; `df.isna()`, `value_counts`, `corr(numeric_only=True)` cover all EDA needs [VERIFIED: venv import probe] |
| scikit-learn | 1.9.1 installed (floor `>=1.3` [VERIFIED: requirements.txt:4]) | `Pipeline`, `ColumnTransformer`, imputers, `OneHotEncoder(handle_unknown="ignore", drop="first")` | Implemented; `get_feature_names_out()` used for transformed columns [VERIFIED: src/preprocessing/preprocess.py:161-168] |
| great-expectations | **1.23.1 installed** (floor `>=0.18` [VERIFIED: requirements.txt:21]) | Raw-CSV expectation suite + runner under `data/validation/` | GX 1.x API prescribed (§ Pattern V1); all six needed `gx.expectations` class names verified present on the installed package [VERIFIED: venv probe — ExpectColumnValuesToBeInSet, ExpectTableRowCountToBeBetween, ExpectColumnValuesToNotBeNull, ExpectTableColumnsToMatchSet, ExpectColumnValuesToBeBetween, ExpectColumnProportionOfNonNullValuesToBeBetween all True] |
| matplotlib | 3.11.2 installed (floor `>=3.7` [VERIFIED: requirements.txt:10]) | EDA figure rendering | Standard backend for all notebook plots [VERIFIED: venv import probe] |
| seaborn | 0.13.2 installed (floor `>=0.12` [VERIFIED: requirements.txt:11]) | `heatmap`, `histplot`/`displot`, `countplot` | `heatmap` signature confirmed vs official API docs [CITED: seaborn.pydata.org/archive/0.12/generated/seaborn.heatmap.html]; `displot(hue, multiple="dodge")` idioms [CITED: seaborn.pydata.org/tutorial/distributions.html] |
| pytest | 9.1.1 installed (floor `>=8.0` [VERIFIED: requirements.txt:29]) | Ingestion tests, `save_outputs` integration test, gate tests | 4 existing tests pass on venv pytest [VERIFIED: `4 passed in 3.72s`]; synthetic-frame + `tmp_path` precedent in repo [VERIFIED: tests/test_preprocessing.py:17-27] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| joblib | per requirements floor `>=1.3` [VERIFIED: requirements.txt:5] | Persist fitted Pipeline | Used in `save_outputs` [VERIFIED: src/preprocessing/preprocess.py:200-201]; never pickle manually |
| pyyaml | floor `>=6.0` [VERIFIED: requirements.txt:6] | `load_config()` | Notebook and GX runner reuse `load_config`, never re-parse YAML [VERIFIED: src/utils/config.py:10-20] |
| loguru | floor `>=0.7` [VERIFIED: requirements.txt:7] | Logging to stderr + rotating file | `get_logger()` singleton [VERIFIED: src/utils/logger.py:11-27] |
| numpy | floor `>=1.24` [VERIFIED: requirements.txt:3] | Correlation mask (`np.triu`) in notebook | EDA only; no new dependency |
| jupyter + nbconvert | **NOT installed in venv** [VERIFIED: `ModuleNotFoundError: No module named 'jupyter'`] | Execute notebook headlessly for the plan verify step | Install into venv (`venv/python.exe -m pip install jupyter nbconvert`) before Plan 01-02 task 2; official Project Jupyter packages [ASSUMED — planner pins versions at install time] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GX 1.x suite | Pandera schemas or hand-rolled `validate_raw()` | Pandera is lighter but a new unplanned dependency; hand-rolled checks are contingency-only now that GX 1.23.1 is confirmed installed and importable — prior fallback concern retired |
| GX 0.18-fluent idiom (`context.sources.pandas_default...`) | — | REJECTED: installed GX is 1.23.1; 0.18-shaped code will fail. Use 1.x `add_pandas` / BatchDefinition / ValidationDefinition only |
| Jupyter notebook EDA | Plain `.py` script | Notebook explicitly required by roadmap; script output not an acceptable substitute |
| seaborn heatmaps | `missingno` nullity plots | New dependency for one plot; `sns.heatmap(df.isna())` covers it with zero new installs |

**Installation (all via the project interpreter — never system Python):**
```bash
venv/python.exe -m pip install -r requirements.txt   # reconcile venv with floors
venv/python.exe -m pip install jupyter nbconvert     # notebook execution only
venv/python.exe -c "import great_expectations as gx; print(gx.__version__)"  # expect 1.23.1
venv/python.exe -m pytest tests/ -q                  # expect 4 passed
```

**Version verification:** Installed versions observed via `venv/python.exe` import probe this session (pandas 3.0.6, sklearn 1.9.1, matplotlib 3.11.2, seaborn 0.13.2, pytest 9.1.1, GX 1.23.1) on Python 3.11.0. System Python (3.14.6) has pandas/sklearn but NO pytest and NO great-expectations [VERIFIED: ModuleNotFoundError + pip-show-not-found] — it must not be used.

## Package Legitimacy Audit

> The `package-legitimacy` seam query could not be run in this Windows PowerShell environment (seam is bash-distributed). All Phase 1 libraries are already pinned in `requirements.txt`; the only new installs are the official Jupyter packages. No obscure/new/small packages are recommended.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| jupyter | PyPI (official Project Jupyter metapackage) [ASSUMED] | long-standing [ASSUMED] | — | github.com/jupyter/jupyter [ASSUMED] | OK (provisional) | Approved — planner pins version at install |
| nbconvert | PyPI (official Jupyter subproject) [ASSUMED] | long-standing [ASSUMED] | — | github.com/jupyter/nbconvert [ASSUMED] | OK (provisional) | Approved — planner pins version at install |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
data/raw/kidney_disease.csv (48KB) + ckd-dataset-v2.csv (34KB, alternate/future drop)
        │  config.data.raw_path -> kidney_disease.csv [VERIFIED: config/config.yaml:4]
        ▼
┌──────────────────┐   "?"→NaN, strip ws      ┌───────────────────┐
│  load_raw_data() │ ─────────────────────────▶ │ summarize() →     │
│ src/ingestion/   │   (leak-safe, fit-free)    │ reports/*.csv     │
└──────────────────┘                            └───────────────────┘
        │                                                  ▲
        │ raw frame                                        │ reads same frame
        ▼                                                  │
┌──────────────────┐  GX 1.x SUITE           ┌──────────────┴────┐
│ GX validation    │  (data/validation/)     │  EDA notebook     │
│ runner (NEW)     │ ── gate: pass/fail ───  │  (NEW, read-only) │
└──────────────────┘                         └───────────────────┘
        │ pass
        ▼
┌──────────────────┐  drop id, clean target ┌──────────────────┐
│   clean_raw()    │ ───────────────────────▶ │   split_raw()    │
│  (fit-free only) │                          │ 70/10/20 strat.  │
└──────────────────┘                          └──────────────────┘
                                                        │
                                                        ▼ (X_train only → fit)
                                              ┌──────────────────┐
                                              │ build_pipeline + │
                                              │ fit_transform_   │
                                              │ split → save_    │
                                              │ outputs (.joblib │
                                              │ + 3 CSVs)        │
                                              └──────────────────┘
```

GX gate failure aborts `preprocess.main()` before `clean_raw` (fail-fast). The notebook sits off the critical path — it never gates or mutates pipeline outputs.

### Recommended Project Structure
```
notebooks/
└── 01_eda_ckd.ipynb      # NEW — read-only; imports src.*, figures to reports/figures/
data/
├── raw/kidney_disease.csv + ckd-dataset-v2.csv  # present [VERIFIED: dir listing]
├── processed/            # only .gitkeep [VERIFIED] — save_outputs target
└── validation/           # only .gitkeep [VERIFIED] — NEW content below
    ├── ckd_suite.json    # persisted suite definition (auditable, diffable)
    └── validate.py       # thin runner: load raw → validate → exit non-zero on failure
src/ingestion/load_data.py      # UNCHANGED — notebook imports from here
src/preprocessing/preprocess.py # UNCHANGED except: gate call in main() (planner decides)
tests/
├── test_preprocessing.py  # exists, 4 tests green on venv [VERIFIED]
├── test_ingestion.py      # NEW — quirk-handling tests
├── test_save_outputs.py   # NEW — tmp_path integration test
└── test_validation.py     # NEW — gate accept/reject tests
```

### Pattern N1: Read-only EDA notebook over pipeline functions
**What:** Notebook imports `load_raw_data`, `summarize`, `clean_raw`, `NUMERIC_COLS`, `CATEGORICAL_COLS` from `src.*` and performs only observational plotting: per-column distributions, numeric correlation matrix, boolean missingness heatmap. Figures saved to `reports/figures/`; notebook committed with cleared outputs.
**When to use:** Always for this phase — missingness numbers match `summarize()` by construction.
**Example:**
```python
# seaborn heatmap + distributions [CITED: seaborn.pydata.org/.../seaborn.heatmap.html]
# [CITED: seaborn.pydata.org/tutorial/distributions.html]
import sys; sys.path.insert(0, "..")
from src.ingestion.load_data import load_raw_data, summarize
from src.preprocessing.preprocess import NUMERIC_COLS, CATEGORICAL_COLS

df = load_raw_data()          # quirks already normalized — never re-implement here
summary = summarize(df)       # single source of truth for missingness table

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 1. Missing-value heatmap (boolean mask is the standard idiom)
fig, ax = plt.subplots(figsize=(14, 6))
sns.heatmap(df.isna(), cbar_kws={"label": "missing"}, yticklabels=False, ax=ax)
ax.set_title("Missing-value map (white = missing)")
fig.savefig("../reports/figures/missingness_heatmap.png", bbox_inches="tight")

# 2. Correlation matrix, fixed [-1,1] scale + masked upper triangle
num = df[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")
corr = num.corr(numeric_only=True)
mask = np.triu(np.ones_like(corr, dtype=bool))
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="vlag",
            center=0, vmin=-1, vmax=1, square=True, ax=ax)
ax.set_title("Numeric feature correlations (Pearson)")
```

### Pattern V1: GX 1.x suite (Data Source → Data Asset → BatchDefinition → ValidationDefinition)
**What:** GX 1.x pure-Python flow against the installed 1.23.1 package — no CLI/YAML scaffold, no 0.18 `context.sources.pandas_default` idiom. Validate the raw frame right after `load_raw_data()` (quirk-normalized but uncleaned), so expectations describe the raw contract.
**When to use:** This phase — validates every future raw file drop without re-running the pipeline.
**Example:**
```python
# GX 1.x flow per official docs (v1.22.0, current for installed 1.23.1)
# [CITED: docs.greatexpectations.io/docs/core/introduction/try_gx]
# [CITED: docs.greatexpectations.io/docs/core/run_validations/run_a_validation_definition]
import great_expectations as gx

context = gx.get_context()  # ephemeral unless a project context is configured [CITED]
data_source = context.data_sources.add_pandas("ckd_pandas")  # [CITED: try_gx]
data_asset = data_source.add_dataframe_asset(name="ckd_raw")  # [CITED: try_gx]
batch_definition = data_asset.add_batch_definition_whole_dataframe("ckd_batch")  # [CITED: try_gx]

# Expectation classes verified present on installed gx.expectations [VERIFIED: venv probe]:
suite = gx.ExpectationSuite(name="ckd_raw_suite")
suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(
    column_set=["age", "bp", "classification", ...], exact_match=False))
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
    column="classification", value_set=["ckd", "notckd"]))  # post-strip domain
suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="classification"))
suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=300, max_value=500))

# Option A (simplest, per try_gx): validate a Batch directly —
batch = batch_definition.get_batch(batch_parameters={"dataframe": df})  # [CITED]
result = batch.validate(suite)  # [CITED: try_gx step 6 pattern]
# Option B (persisted/re-runnable): ValidationDefinition(name, data, suite).run(batch_parameters={"dataframe": df}) [CITED]
assert result.success, "Raw data failed validation gate"
```
> Constructor/kwarg spellings above (`ExpectationSuite(name=...)`, `add_expectation`, `batch.validate(suite)`) follow the official 1.x guides but were not executed this session — treat exact call shapes as [ASSUMED] and confirm with one smoke run against the installed 1.23.1 before freezing the runner. Robustness rules are version-independent: NO exact row counts (see Pitfall 3).

### Pattern T1: Ingestion-quirk tests on synthetic frames + `tmp_path` integration test
**What:** Follow the existing synthetic-frame precedent [VERIFIED: tests/test_preprocessing.py:17-27] — tiny DataFrames/CSVs containing literal `"?"`, padded whitespace (`" yes"`, `"\tno"`), numeric-as-string cells; assert normalization via the real `load_raw_data`; `save_outputs` round-trip via pytest's `tmp_path` with `load_config` monkeypatched (defeating the `lru_cache` [VERIFIED: src/utils/config.py:10-11] with `cache_clear`).
**When to use:** All new Phase 1 tests — suite stays independent of the real CSV (NFR-3).
**Example:**
```python
# tmp_path/monkeypatch idiom from training knowledge [ASSUMED] (long-stable pytest APIs)
import pandas as pd
from src.preprocessing.preprocess import clean_raw, save_outputs

def test_ingestion_normalizes_quirks(tmp_path):
    raw = tmp_path / "quirky.csv"
    raw.write_text("age,rbc,classification\n 25 , ? ,\tckd \n30,yes,notckd\n")
    # load via load_raw_data(str(raw)); assert "?" became NA, whitespace stripped
```

### Anti-Patterns to Avoid
- **Fitting anything in the notebook:** `.fit()`/`fit_transform` in EDA cells creates a shadow preprocessing path diverging from the Claim 2 artifact. Observation only.
- **0.18-shaped GX code** (`context.sources.pandas_default`, `add_or_update_checkpoint`, YAML checkpoints): will `AttributeError` on installed 1.23.1. Use Pattern V1 only.
- **Full `great_expectations init` scaffold:** ~30-file tree for a one-suite need. Suite JSON + thin runner under `data/validation/` only.
- **`expect_table_row_count_to_equal(400)`:** bakes sample size into the contract. Use `to_be_between` ranges.
- **Duplicating quirk logic in tests/notebook:** the canonical `"?"` regex lives at [VERIFIED: src/ingestion/load_data.py:45]. Tests call the real function; never copy the regex.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Missing-value / correlation visualization | Custom matplotlib matrix loops | `sns.heatmap(df.isna())`, `sns.heatmap(corr, mask=...)` | NaN masking, diverging-scale centering, triangular masks handled [CITED: seaborn heatmap API docs] |
| Train/val/test splitting | Manual index arithmetic | `train_test_split` twice (already in `split_raw`) | Stratification + `random_state` on 400 rows is subtle [VERIFIED: src/preprocessing/preprocess.py:112-127] |
| Categorical encoding at inference | `pd.get_dummies` + manual column alignment | Fitted `OneHotEncoder(handle_unknown="ignore")` in the single Pipeline | Unseen categories / column-order drift crash naive alignment [VERIFIED: src/preprocessing/preprocess.py:142-149] |
| Config loading | Per-module YAML parsing with relative paths | `load_config()` (`lru_cache`, root-anchored) | CWD-independent resolution solved [VERIFIED: src/utils/config.py:10-20] |
| Data-quality contract checks | Ad-hoc `assert df.shape == (...)` in `main()` | GX 1.x suite persisted as JSON + thin runner | Ad-hoc asserts are undiffable and report-free; GX gives named, re-runnable expectations [CITED: GX 1.x run-validations docs] |

**Key insight:** Every deceptively-simple piece of this phase already has a committed implementation or standard idiom. New code only *calls* these — EDA observes, GX gates, tests assert.

## Common Pitfalls

### Pitfall 1: Leakage regression via "quick" full-frame imputation in EDA or validation
**What goes wrong:** Whole-frame `fillna` in the notebook gets copied into `preprocess.py`, reintroducing the leak the refactor fixed.
**Why it happens:** `df.fillna(df.median())` looks harmless on 400 rows.
**How to avoid:** Working copies named `eda_df`/`plot_df`; `fit_transform_split` keeps `pipeline.fit(X_train)`-only [VERIFIED: src/preprocessing/preprocess.py:176]; re-run the 4 existing tests after any edit.
**Warning signs:** Any `.fit(` or `fit_transform` in `notebooks/` or `data/validation/validate.py`.

### Pitfall 2 (RETIRED — was: GX version mismatch / Python 3.14 risk)
Prior research gated GX work on a 0.18-vs-1.x branch and a 3.14-compat spike. Fresh evidence retires both: the project interpreter is Python 3.11.0 with GX 1.23.1 installed and importable [VERIFIED: venv probes], inside GX's documented 3.10–3.13 window [CITED]. **Planner action:** delete the version-branch from Plan 01-01; prescribe Pattern V1 (1.x) directly. Remaining (small) risk is exact constructor/kwarg spelling — covered by a single smoke run, not a fallback build.

### Pitfall 3: Fragile expectations (exact row counts, exact column order, pre-strip label strings)
**What goes wrong:** Suite passes today, fails on the next valid drop (401 rows, reordered columns, `"ckd\t"` variant), training the team to ignore the gate.
**Why it happens:** Profiler output pasted as expectations without asking which invariants are contractual.
**How to avoid:** Ranges not equals (`ExpectTableRowCountToBeBetween(300, 500)`); `exact_match=False`; validate the *stripped/lowered* label domain produced by `load_raw_data`; missingness as upper bounds from `summarize()` output, not exact percentages.
**Warning signs:** Any `== 400`, `exact_match=True`, or raw `"?"` literals in `value_set`.

### Pitfall 4: Notebook as second source of truth
**What goes wrong:** Notebook re-implements `"?"`→NaN with different regex; numbers disagree with `summarize()`.
**Why it happens:** Notebook authorship feels standalone; `src.*` import needs the `sys.path` shim.
**How to avoid:** First code cell is `sys.path.insert(0, "..")` + `from src.ingestion.load_data import load_raw_data, summarize`; forbid local quirk regex (canonical copy [VERIFIED: src/ingestion/load_data.py:45]).
**Warning signs:** `df.replace` with `"?"` anywhere under `notebooks/`.

### Pitfall 5: `save_outputs` test writing into the real `data/processed/`
**What goes wrong:** Integration test overwrites real artifacts / pollutes git status.
**Why it happens:** `save_outputs` resolves output dir from global config [VERIFIED: src/preprocessing/preprocess.py:189-192].
**How to avoid:** Redirect config (`monkeypatch` on `load_config` + `cache_clear` for the `lru_cache`) to `tmp_path`; assert 3 CSVs + `.joblib` there with row-count conservation; never assert against real `data/processed/`.
**Warning signs:** `git status` shows modified files under `data/processed/` after a test run.

### Pitfall 6 (NEW): Using system Python instead of the venv
**What goes wrong:** `pytest`/`great_expectations` ModuleNotFoundError, or silently different pandas/sklearn behavior.
**Why it happens:** System Python 3.14.6 is first on PATH and *looks* usable (has pandas 3.0.1 + sklearn 1.8.0 [VERIFIED: system pip show]).
**How to avoid:** Every plan command uses `venv/python.exe -m ...` explicitly (e.g., `venv/python.exe -m pytest tests/ -q`). Never bare `python`/`pytest`/`pip`.
**Warning signs:** `pytest: command not found` or `ModuleNotFoundError: No module named 'pytest'` on system python [VERIFIED this session].

## Code Examples

### Missingness bar + heatmap pair (standard EDA duo)
```python
# heatmap API [CITED: seaborn.pydata.org/.../seaborn.heatmap.html]; summary idiom [ASSUMED] (stable pandas 2.x/3.x APIs)
miss = df.isna().mean().mul(100).sort_values(ascending=False)
fig, axes = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={"width_ratios": [1, 2]})
miss.plot.barh(ax=axes[0], color="steelblue")
axes[0].set_xlabel("missing %"); axes[0].set_title("Per-column missingness")
sns.heatmap(df.isna(), cbar_kws={"label": "missing"}, yticklabels=False, ax=axes[1])
axes[1].set_title("Missing-value map")
```

### Target-aware distributions (CKD class separation is the EDA payoff)
```python
# hue/dodge + discrete idioms [CITED: seaborn.pydata.org/tutorial/distributions.html]
plot_df = clean_raw(load_raw_data())  # reuse pipeline cleaning — never recode labels [VERIFIED: src/preprocessing/preprocess.py:61-102]
sns.displot(plot_df, x="hemo", hue="classification", kind="kde", fill=True)
sns.countplot(data=plot_df, x="rbc", hue="classification")
```

### GX 1.x gate wired into pipeline entry (fail-fast ordering)
```python
# Wiring idiom [ASSUMED]; GX calls [CITED: GX 1.x try_gx + run_a_validation_definition]
def main():
    df = load_raw_data()
    from data.validation.validate import run_raw_validation
    result = run_raw_validation(df)   # success bool; False on bad drop
    if not result.success:
        raise SystemExit("Raw-data validation failed — aborting before clean/split.")
    df = clean_raw(df)
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GX CLI + YAML scaffold (`great_expectations init`, `checkpoints/*.yml`) | Pure-Python 1.x: `gx.get_context()` + Data Source → Asset → BatchDefinition → `batch.validate()` / `ValidationDefinition.run()` | GX 1.0 (2024–2025) [CITED: GX 1.22 docs] | `data/validation/` needs only suite JSON + runner `.py` |
| `df.corr()` on mixed frames | `corr(numeric_only=True)` on `pd.to_numeric(errors="coerce")` subset | pandas 2.x | Notebook mirrors `clean_raw` coercion [VERIFIED: src/preprocessing/preprocess.py:89-90] |
| `OneHotEncoder(sparse=True)` default | Sparse handled in `_to_dataframe` via `.toarray()` | sklearn 1.2+ | Already handled [VERIFIED: src/preprocessing/preprocess.py:161-168] — no action |

**Deprecated/outdated:**
- GX 0.13/0.14 V2 API (`DataContext.create`, `BatchRequest` + YAML datasources) and the 0.18 fluent `context.sources.pandas_default` idiom: do not copy either against installed 1.23.1 [CITED: GX 1.x docs; 0.18 shape from prior research, now superseded].
- `seaborn.distplot`: removed; use `histplot`/`displot`/`kdeplot` [CITED: seaborn distributions tutorial].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact GX 1.x call shapes (`ExpectationSuite(name=...)`, `suite.add_expectation(...)`, `batch.validate(suite)`) match installed 1.23.1 | Pattern V1 / Code Examples | LOW–MEDIUM — one smoke run confirms; official 1.22 docs cited but not executed here |
| A2 | `notebooks/` kernels import `src.*` via `sys.path` shim (`tests/__init__.py` exists [VERIFIED: tests listing]) | Pattern N1 | LOW — fallback: `PYTHONPATH` export or `%pip install -e .` in setup cell |
| A3 | jupyter + nbconvert install cleanly into the venv (Python 3.11) | Standard Stack | LOW — mainstream packages on a supported Python; failure only delays notebook execution proof, not notebook authorship |
| A4 | pytest `tmp_path`/`monkeypatch` semantics match training knowledge | Pattern T1 | LOW — long-stable APIs; smoke test catches drift in seconds |
| A5 | `ckd-dataset-v2.csv` in `data/raw/` is an alternate/future drop, not Phase 1 input (config points at `kidney_disease.csv` [VERIFIED: config/config.yaml:4]) | Architecture diagram | LOW — planner confirms which file the notebook profiles first |
| A6 | `pandas 3.0.6` (venv) keeps `isna/mean/corr(numeric_only=True)`, `str.strip`, `to_numeric(errors="coerce")` semantics used by pipeline + notebook | Code Examples | LOW — pipeline already runs on this pandas (4 tests green); notebook uses the same calls |

## Open Questions

1. **Should the GX gate hard-fail `preprocess.main()` or warn-and-continue?**
   - What we know: Roadmap calls Phase 1's layer a "Data Validation Layer"; ingestion docstring says re-validation should be possible without re-running the pipeline [VERIFIED: src/ingestion/load_data.py:3-8].
   - What's unclear: Desired strictness for M1 (academic demo may prefer warn-mode to avoid demo-day breakage).
   - Recommendation: Default to hard-fail (exit non-zero); flag as user-confirmable in discuss-phase.

2. **Which raw file does the notebook profile first — `kidney_disease.csv`, `ckd-dataset-v2.csv`, or both?**
   - What we know: Config points at `kidney_disease.csv` [VERIFIED: config/config.yaml:4]; both files present (48KB + 34KB [VERIFIED: listing]).
   - What's unclear: Whether v2 is a future Phase 5 drift input or an alternate Phase 1 input.
   - Recommendation: Profile the configured file; add a short v2-comparison section only if cheap (planner asks user).

3. **Do prior Plans 01-01/01-02/01-03 get rewritten or patched?**
   - What we know: All three exist and are structurally sound; 01-01's GX-version branch + fallback build are now stale (this research retires them); 01-02's "pip install nbconvert if absent" is now confirmed-needed; 01-03 is unaffected.
   - What's unclear: Planner workflow preference (regenerate vs amend).
   - Recommendation: Patch 01-01 (drop version branch, prescribe Pattern V1, keep interpreter/record steps as no-op verification); keep 01-02/01-03 as-is.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Project interpreter `venv/python.exe` | Everything | ✓ [VERIFIED: `Python 3.11.0`] | 3.11.0 | — (meets 3.11+ floor [VERIFIED: PROJECT.md tech stack]) |
| pandas / sklearn / matplotlib / seaborn (venv) | Pipeline + EDA | ✓ [VERIFIED: import probe] | 3.0.6 / 1.9.1 / 3.11.2 / 0.13.2 | `venv/python.exe -m pip install -r requirements.txt` |
| pytest (venv) | Validation Architecture | ✓ [VERIFIED: 9.1.1, 4 passed] | 9.1.1 | — |
| great-expectations (venv) | GX suite + runner | ✓ [VERIFIED: 1.23.1, import + 6 class names] | 1.23.1 | Contingency-only: config-driven hand-rolled checks |
| jupyter / nbconvert (venv) | Notebook execution proof | ✗ [VERIFIED: ModuleNotFoundError] | — | Install into venv before Plan 01-02 task 2 |
| System Python 3.14.6 | Nothing — DO NOT USE | ⚠ present but missing pytest + GX | 3.14.6 | N/A — use venv always (Pitfall 6) |
| `data/raw/*.csv` | Notebook + GX suite | ✓ [VERIFIED: listing] | kidney_disease.csv + ckd-dataset-v2.csv | — |
| `notebooks/` dir | EDA notebook | ✓ exists, EMPTY (0 items) [VERIFIED] | — | — |
| `data/validation/` dir | GX suite | ✓ exists, only `.gitkeep` [VERIFIED] | — | — |
| `data/processed/` dir | save_outputs target | ✓ exists, only `.gitkeep` [VERIFIED] | — | — |
| pytest config | Test runs | ✗ absent (no ini/toml — prior finding, unchanged) | — | Run from root; `tests/__init__.py` present [VERIFIED] |

**Missing dependencies with no fallback:**
- None. The venv resolves everything except notebook execution.

**Missing dependencies with fallback / install step:**
- jupyter + nbconvert → `venv/python.exe -m pip install jupyter nbconvert` (Plan 01-02 Wave 0).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 in venv (floor >=8.0 [VERIFIED: requirements.txt:29]) |
| Config file | none — run from repo root so `src.*` imports resolve via `tests/__init__.py` [VERIFIED: tests listing] |
| Quick run command | `venv/python.exe -m pytest tests/test_preprocessing.py -x -q` |
| Full suite command | `venv/python.exe -m pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FR-1.1 | "?" → NA, whitespace stripped, numeric coercion on quirky synthetic CSV | unit | `venv/python.exe -m pytest tests/test_ingestion.py -x -q` | ❌ Wave 0 (new `tests/test_ingestion.py`) |
| FR-1.2 | `summarize()` returns dtype/missing/n_unique sorted by missing_pct | unit | `... tests/test_ingestion.py::test_summarize_columns -x -q` | ❌ Wave 0 |
| FR-1.3 | Target cleaned to {0,1}, no null labels, id dropped | unit | `... tests/test_preprocessing.py::test_clean_raw_no_missing_target -x -q` | ✅ [VERIFIED: tests/test_preprocessing.py:30-33] |
| FR-1.4 | Train/val/test indices mutually disjoint | unit | `... tests/test_preprocessing.py::test_split_before_fit_no_overlap -x -q` | ✅ [VERIFIED: tests/test_preprocessing.py:36-42] |
| FR-1.5 | Single fitted `sklearn.Pipeline`; no-NaN transforms | unit | `... tests/test_preprocessing.py::test_pipeline_is_single_sklearn_object -x -q` | ✅ [VERIFIED: tests/test_preprocessing.py:45-52] |
| FR-1.6 | `save_outputs` writes 3 CSVs + `.joblib` to isolated dir; row counts sum to input | integration (`tmp_path` + config redirect) | `... tests/test_save_outputs.py -x -q` | ❌ Wave 0 |
| FR-1.7 | Ratios/strategies/paths from `config.yaml` (no hard-coded paths) | static (grep) + config-override test | `... tests/ -q` + review: no literal `data/` paths in notebook/runner | ❌ Wave 0 |
| GX gate | Runner rejects bad frames (unknown label, missing target col, tiny rows), accepts good frame | unit (synthetic frames vs real 1.x runner) | `... tests/test_validation.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `venv/python.exe -m pytest tests/test_preprocessing.py -x -q` (regression guard on the 4 existing tests)
- **Per wave merge:** `venv/python.exe -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `venv/python.exe -m pip install jupyter nbconvert` — notebook execution proof (only install needed)
- [ ] `tests/test_ingestion.py` — FR-1.1 quirk tests (bare + padded `" ? "`, whitespace/tab labels, numeric-as-string), FR-1.2 `summarize()` shape test, FR-1.7 config-override test
- [ ] `tests/test_save_outputs.py` — `save_outputs` round-trip under `tmp_path` with config redirect; 3 CSVs + `.joblib`, row-count conservation, reloadable pipeline, real-dir untouched
- [ ] `tests/test_validation.py` — gate accepts good synthetic frame; rejects unknown-label / missing-target-column / 2-row frames
- [ ] `notebooks/01_eda_ckd.ipynb` — distributions, correlation heatmap, missingness heatmap, read-only via `src.*`
- [ ] `data/validation/ckd_suite.json` + `data/validation/validate.py` — GX 1.x suite + runner, wired (or explicitly deferred) into `preprocess.main()`
- [ ] None — interpreter, pytest, GX availability: all RESOLVED (no Wave 0 probing needed beyond the jupyter install)

## Security Domain

> Minimal surface for a local data pipeline — no auth, sessions, network, or crypto. Focus is input validation and safe path handling.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (local scripts, no users) |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | GX 1.x suite (contract) + `pd.to_numeric(errors="coerce")` + `positive_label` membership `ValueError` [VERIFIED: src/preprocessing/preprocess.py:89-99] |
| V6 Cryptography | no | — (no secrets in Phase 1) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed raw CSV silently breaking training | Tampering | GX gate fail-fast before `clean_raw`; actionable `FileNotFoundError` already in `load_raw_data` [VERIFIED: src/ingestion/load_data.py:33-38] |
| Path traversal / CWD-dependent writes via config | Tampering | Root-anchored `PROJECT_ROOT / cfg[...]` [VERIFIED: src/utils/config.py:17-19]; no bare relative `open()` in notebook/runner |
| Notebook arbitrary code on open (stored outputs / malicious cells) | Elevation | Commit with cleared outputs; no `!pip`/`!curl`/`os.system` cells; grep for `!` before merge [ASSUMED policy — standard Jupyter hygiene] |
| `.joblib` artifact risk | Tampering | Own-pipeline artifact only; never load third-party `.joblib` [ASSUMED policy] |
| Wrong-interpreter execution (system 3.14) | Tampering (integrity) | All commands via `venv/python.exe -m ...` (Pitfall 6) |

## Sources

### Primary (HIGH confidence)
- In-repo source of truth read this session: `src/ingestion/load_data.py`, `src/preprocessing/preprocess.py`, `src/utils/config.py`, `src/utils/logger.py`, `tests/test_preprocessing.py`, `config/config.yaml`, `requirements.txt`, `.planning/{PROJECT,REQUIREMENTS,ROADMAP,STATE}.md`, prior `01-01/01-02/01-03-PLAN.md` + prior `01-RESEARCH.md`
- Environment probes run this session on `venv/python.exe`: `--version` (3.11.0), import probe (pandas 3.0.6, sklearn 1.9.1, matplotlib 3.11.2, seaborn 0.13.2, pytest 9.1.1, GX 1.23.1), `gx.get_context` + `ExpectationSuite` import check, 6 `gx.expectations` class-name checks (all True), `pytest tests/ -q` (4 passed in 3.72s), jupyter import (absent), system-python pytest/GX absence
- Directory listings: `notebooks/` empty (0 items), `data/validation/` + `data/processed/` only `.gitkeep`, `tests/` only `test_preprocessing.py` + `__init__.py`, `data/raw/` two CSVs

### Secondary (MEDIUM confidence)
- [CITED: docs.greatexpectations.io/docs/core/introduction/try_gx] — 1.x `gx.get_context()` → `add_pandas` → `add_dataframe_asset` → `add_batch_definition_whole_dataframe` → `get_batch(batch_parameters={"dataframe": df})` → `batch.validate(...)` (v1.22 docs, current for installed 1.23.1)
- [CITED: docs.greatexpectations.io/docs/core/run_validations/run_a_validation_definition] — Python 3.10–3.13 prereq + `ValidationDefinition.run(batch_parameters={"dataframe": df})`
- [CITED: docs.greatexpectations.io/docs/reference/api/validationdefinition_class] — `ValidationDefinition(name, data, suite)`, `run(...)` signature
- [CITED: seaborn.pydata.org/archive/0.12/generated/seaborn.heatmap.html] — `heatmap()` signature
- [CITED: seaborn.pydata.org/tutorial/distributions.html] — `displot`/`histplot`, `hue` + `multiple="dodge"`

### Tertiary (LOW confidence)
- jupyter/nbconvert official-repo claims [ASSUMED]; exact GX constructor/kwarg spellings not executed [ASSUMED pending smoke run]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every installed version observed via venv probe; only jupyter provenance assumed.
- Architecture: HIGH — split-first ordering, single-Pipeline artifact, config keys, quirk regex all read verbatim; GX 1.x flow cited to versioned official docs and class names verified on the installed package.
- Pitfalls: HIGH — Pitfalls 1/3/4/5 grounded in verified code; Pitfall 2 retired with evidence; Pitfall 6 observed directly.

**Research date:** 2026-09-19 (force-refresh)
**Valid until:** ~30 days (stable domain; venv pins versions so GX-doc drift is contained — re-check only if venv is rebuilt at newer versions).

