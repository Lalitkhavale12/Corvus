# Phase 1 Plan 02: Read-only EDA Notebook Summary

**Phase:** 1-data-pipeline — **Plan:** 02 — **Status:** complete
**Date:** 2026-09-19 — **Requirements:** FR-1.2

## One-liner

Read-only CKD EDA notebook profiling the real raw CSV through `load_raw_data`/`summarize`/`clean_raw` — distributions, masked correlation heatmap, missingness bar plus heatmap, committed with cleared outputs.

## What was built

`notebooks/01_eda_ckd.ipynb` (11 cells: 4 markdown, 7 code), executable end-to-end via
`venv/python.exe -m jupyter nbconvert --to notebook --execute`:

- **Imports cell:** `sys.path.insert(0, "..")` shim, then `load_raw_data`/`summarize` from
  `src.ingestion.load_data` and `NUMERIC_COLS`/`CATEGORICAL_COLS`/`clean_raw` from
  `src.preprocessing.preprocess`. Root-aware `FIG_DIR` (`reports/figures/`) works whether the
  kernel cwd is `notebooks/` or the repo root.
- **Load + summarize:** `eda_df = load_raw_data()` (no args — configured raw path),
  `summary = summarize(eda_df)` displayed as the single source of truth for missingness.
- **Missingness:** horizontal missing-% bar chart (`missingness_bar.png`) and boolean-mask
  heatmap (`missingness_heatmap.png`), both `bbox_inches="tight"`.
- **Distributions:** `plot_df = clean_raw(load_raw_data())` (no manual label recoding), hemo KDE
  displot by class (`hemo_kde_by_class.png`), rbc countplot by class (`rbc_count_by_class.png`).
- **Correlation:** `pd.to_numeric(errors="coerce")` over `NUMERIC_COLS`, `corr(numeric_only=True)`,
  `np.triu` mask, `annot=True fmt=".2f" cmap="vlag" center=0 vmin=-1 vmax=1 square=True`
  (`correlation_heatmap.png`).
- **Takeaways (plain text):** highest missingness `rbc` 38.00% > `rc` 32.75% > `wc` 26.50%;
  strongest numeric pair hemo–pcv Pearson r ~0.90.

Notebook committed with **zero stored outputs**; figures are runtime-only under `reports/figures/`
(gitignored, not committed). Installed `jupyter` + `nbconvert` into `venv` (both confirmed absent
beforehand; official Jupyter packages per threat T-1-SC accept).

## Verification results

| Check | Result |
|---|---|
| Cell count (`len(nb['cells'])`) | 5 after task 1, 11 final — PASS |
| `nbconvert --execute` exit code + output file | exit 0, `eda_exec_check.ipynb` written (warnings only, no Error/Traceback) — PASS |
| Forbidden-logic scan (`.fit(`, `fit_transform`, `get_dummies`, `os.system` in non-comment code) | `violations: []` — PASS |
| Stored outputs / tracebacks in committed file | 0 / 0 — PASS |
| Figures under `reports/figures/` | 5 PNGs present — PASS |

## Commits

| Task | Message | Hash |
|---|---|---|
| 1 — skeleton + missingness | `feat(01-02): notebook skeleton plus missingness analysis over summarize()` | `1a58870` |
| 2 — distributions + correlation | `feat(01-02): distributions plus correlation heatmap plus executed-and-cleared notebook` | `f04d986` |

Only `notebooks/01_eda_ckd.ipynb` staged per commit (`git add` on the single file, never `-A`).
No changes to `STATE.md`, `ROADMAP.md`, `data/validation/`, or `src/`.

## Deviations from Plan

None — plan executed exactly as written. (Environment note, not a deviation: `jupyter`/`nbconvert`
install was required and plan-authorized; figures landed in `reports/figures/` which is gitignored
via `reports/*`, matching the plan's "runtime outputs, not committed" contract.)

## Self-Check: PASSED

- `notebooks/01_eda_ckd.ipynb` exists and parses as JSON (verified via both verify commands).
- Commits `1a58870` and `f04d986` exist on `main` (`git log`).
- No stub patterns: no empty placeholders, TODOs, or unwired data sources — every number is
  computed live from the real CSV at execution time.
- No threat-model regressions: cleared outputs (T-1-04), no fit/encode/quirk-regex (T-1-05),
  no shell cells or `os` import (T-1-06).
