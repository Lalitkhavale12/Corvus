---
phase: 02-model-training-experiment-tracking
reviewed: 2026-09-21T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/training/train.py
  - src/training/train_mlp.py
  - src/evaluation/evaluate.py
  - tests/conftest.py
  - tests/test_training.py
  - tests/test_registry.py
findings:
  critical: 0
  warning: 11
  info: 6
  total: 17
status: issues-found
---

# Phase 02: Code Review Report — Model Training + Experiment Tracking

**Reviewed:** 2026-09-21
**Depth:** standard (per-file, language-aware, with import/call cross-checks)
**Files Reviewed:** 6
**Status:** issues-found

## Summary

Reviewed the full Phase 2 slate (6 classical configs in `train.py`, 3 MLP runs in
`train_mlp.py`, ranking/lifecycle in `evaluate.py`, plus Wave 0 fixtures and both
test modules) against 02-CONTEXT.md decisions D-01..D-07 and the two plan summaries.
No Critical (security) findings: no secrets, no injection sinks, no network, no
`eval`/`exec`. The bulk of the findings are correctness/robustness defects that the
green suite hides: a broken target-coercion fallback branch, order-dependent winner
ties, a fail-open winner-version fallback, non-atomic registry mutation behind a
broad `except`, per-run overwrite of the canonical Phase 1 pipeline artifact, a
Claim-2 test that never calls the code it claims to cover, and two conftest fixtures
that no test consumes. Details with file:line evidence below.

## Threat Model Note

- **Local-only training:** tracking URI resolves under `PROJECT_ROOT / cfg[mlflow][tracking_uri]`
  (`train.py:120`, `train_mlp.py:66`, `evaluate.py:90`); registry transitions go through
  the local file-store `MlflowClient`. No network endpoints, auth paths, or secrets in scope.
- **joblib trust boundary:** scope files only ever `joblib.dump` a freshly fit sklearn
  `Pipeline` to config-resolved `data/processed/preprocessing_pipeline.joblib`
  (`train.py:138-139`, `train_mlp.py:90-91`). No `joblib.load` in scope, so no
  unpickling sink here. Residual risk is downstream: `mlflow.sklearn.log_model(...,
  serialization_format="cloudpickle")` artifacts execute code on load, so the Phase 3
  consumer must load only registry models from this local store, never third-party runs.
- **Shared-file mutation:** see WR-05 — the dump target is also the Phase 1 input artifact,
  so the trust boundary around `data/processed/` is write-weakened on every training run.
- **MLflow filter string** (`evaluate.py:111`) interpolates a module constant, not user
  input — no injection (see IN-06).

## Warnings

### WR-01: Target-coercion fallback branch is dead — string labels crash, NaNs crash, non-binary numerics silently become all-zero

**File:** `src/training/train.py:95-99`
**Issue:** The binary-vs-string detector is `set(pd.to_numeric(y_raw, errors="coerce").dropna().unique()) <= {0, 1}`.
Three failures: (a) all-string targets (`ckd`/`notckd`, the documented fallback case) coerce to
all-NaN, `dropna()` yields the empty set, and `set() <= {0,1}` is `True` — so string input takes
the *binary* branch and `pd.to_numeric(y_raw)` (no `errors="coerce"`) raises `ValueError`;
the `else` fallback is unreachable for its intended input. (b) Binary targets with any missing
value pass the subset check (NaN dropped) then crash at `.astype(int)` with `IntCastingNaNError`.
(c) Non-binary numerics (e.g. `0.5`) fall to the string branch and compare `False` everywhere,
producing an all-zero `y` and a downstream single-class solver error far from the cause.
**Fix:**
```python
codes = pd.to_numeric(y_raw, errors="coerce")
if codes.notna().all() and set(codes.unique()) <= {0, 1}:
    y = codes.astype(int)
elif codes.isna().any() and y_raw.isna().any():
    raise ValueError(f"Missing targets in {path.name}: {(int(y_raw.isna().sum()))} rows")
else:
    y = (y_raw.astype(str).str.strip().str.lower() == positive_label).astype(int)
    if y.nunique() < 2:
        raise ValueError(f"Target encoding produced a single class in {path.name}")
```

### WR-02: Winner selection has an implicit order-dependent tie-break, contradicting D-03 "no tie-break"

**File:** `src/evaluation/evaluate.py:49-51`
**Issue:** `max(runs, key=...)` returns the *first* maximal element, so ties resolve by the order
`search_runs` happens to return — which MLflow does not guarantee. Ties are plausible here, not
theoretical: the tracer reported LR at `roc_auc=1.0` and the canonical pass crowned `mlp-relu`
at `roc_auc=1.0`. A tie silently promotes whichever run the store lists first, and
`tests/test_registry.py:18` even memorializes "first max wins" in a comment while the fixture
contains no tie to pin the behavior.
**Fix:** Make the tie policy explicit and deterministic per D-03's intent, e.g. lowest run start
time wins, or fail loudly on exact ties:
```python
def select_winner(runs: list) -> dict:
    if not runs:
        raise ValueError("select_winner received no runs")
    best = max(r["metrics"]["roc_auc"] for r in runs)
    tied = [r for r in runs if r["metrics"]["roc_auc"] == best]
    if len(tied) > 1:
        raise ValueError(f"ROC-AUC tie at {best}: {[r['run_id'] for r in tied]} — resolve per D-03")
    return tied[0]
```
(If ties should instead be broken deterministically, sort by `(roc_auc, run_id)` explicitly and
document it as the tie-break, updating 02-CONTEXT.md D-03.)

### WR-03: Winner-version fallback silently promotes the wrong model, and string-`max` breaks at v10+

**File:** `src/evaluation/evaluate.py:54-65`
**Issue:** Two defects in `resolve_winner_version`. (a) On `run_id` miss it falls back to
`max(v.version for v in versions)` with no log/exception — a missed linkage (e.g. winner run
failed to register) then promotes an unrelated version to Staging, and Phase 3 serves it via
`models:/corvus-ckd/Staging`. Fail-open promotion must be fail-closed. (b) `version` values are
strings, so the fallback is lexicographic: once v10 exists, `max` returns `"9"`. The test at
`tests/test_registry.py:66` pins the fallback (`"missing" -> "3"`) instead of flagging it.
**Fix:**
```python
def resolve_winner_version(versions: list, winner_run_id: str):
    for v in versions:
        if v.run_id == winner_run_id:
            return v.version
    raise ValueError(f"No registered version links to winner run {winner_run_id!r}")
```
(If a fallback is genuinely required, use `max(int(v.version) for v in versions)` and `log.error`.)

### WR-04: Broad `except Exception` hides partial registry mutation — half-applied stages reported as plain failure

**File:** `src/evaluation/evaluate.py:87-124`
**Issue:** `apply_registry_stages` performs up to 9 sequential `transition_model_version_stage`
calls with no atomicity; if call 4 of 9 raises, versions 1–3 are already Archived/Staged and the
`except Exception` at line 122 collapses it to `log.warning(...)` + `success=False` with no record
of which transitions landed. Re-running then operates on a half-mutated registry. The broad catch
also swallows programming errors (e.g. `AttributeError` when the experiment name is missing and
`experiment` is `None` at line 94) indistinguishably from MLflow outages.
**Fix:** Narrow the catch to `(MlflowException, OSError)`, and make stage application resumable/
idempotent — e.g. re-read stages after failure and include applied-vs-pending in the log and the
returned namespace:
```python
except MlflowException as exc:
    log.error(f"Evaluation failed mid-lifecycle: {type(exc).__name__}: {exc}")
    return SimpleNamespace(success=False, winner=None, applied=getattr(locals(), "applied", []))
```

### WR-05: Every training run overwrites the canonical Phase 1 pipeline artifact in place

**File:** `src/training/train.py:138-139` (same pattern `src/training/train_mlp.py:90-91`)
**Issue:** `joblib.dump(pipeline, pipeline_path)` writes to the shared, versioned input
`data/processed/preprocessing_pipeline.joblib` — 9 times per full pass (6× classical + 3× MLP),
plus a `train.py`/`train_mlp.py` race if both entry points ever run concurrently. A crash between
`dump` and `log_artifact` leaves a corrupted committed artifact; a future column-list change
silently rewrites Phase 1's output as a training side effect. Claim 2 only requires the pipeline
be *logged* per run, not that the source file be re-dumped per run.
**Fix:** Dump to a temp file and log that, leaving the committed artifact untouched:
```python
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    tmp_pipe = Path(tmp) / "preprocessing_pipeline.joblib"
    joblib.dump(pipeline, tmp_pipe)
    mlflow.log_artifact(str(tmp_pipe), artifact_path="preprocessing")
```
(Or dump once to a run-scoped filename and assert byte-equality with the committed artifact.)

### WR-06: `main()` has no per-run isolation — one failing config aborts the remaining slate

**File:** `src/training/train.py:156-159`
**Issue:** The loop calls `run_experiment(name)` with no try/except, so a single failure
(XGB/LGBM native error, single-class split, MLflow hiccup) kills all subsequent configs and
leaves a partial 9-run store that `evaluate.py` then ranks as if complete. Same shape in
`train_mlp.py:109-112`.
**Fix:**
```python
def main() -> int:
    failed = []
    for name in ESTIMATORS:
        try:
            result = run_experiment(name)
        except Exception as exc:
            log.error(f"Config {name} failed: {exc}")
            failed.append(name)
            continue
        print(f"TRAINED {name} roc_auc={result['metrics']['roc_auc']:.4f}")
    return 1 if failed else 0
```

### WR-07: `roc_auc_score` unguarded against single-class `y_test` in both `compute_metrics` copies

**File:** `src/training/train.py:106-114` and `src/evaluation/evaluate.py:37-46`
**Issue:** `roc_auc_score(y_true, y_proba)` raises `ValueError` when `y_test` holds one class —
possible on the small 279-row split family and fatal inside the MLflow run (params logged, run
left metric-less and later filtered out of ranking by the `all(m in ...)` guard at
`evaluate.py:104`). `precision/recall/f1` already pass `zero_division=0`; ROC-AUC has no equivalent
guard. Compounding it, the `evaluate.py` copy is never called by anyone (verified: no importer),
so the duplication doubles the fix surface for dead code.
**Fix:** Guard at the call site and delete the dead copy:
```python
"roc_auc": roc_auc_score(y_true, y_proba) if len(set(y_true)) == 2 else float("nan"),
```
then remove `evaluate.compute_metrics` (and its now-unused sklearn imports) since
`run_evaluation` only reads stored metrics.

### WR-08: `train_mlp.run_experiment` duplicates the ~40-line Claim 2 run loop despite the "reuse, not duplicated" claim

**File:** `src/training/train_mlp.py:63-106`
**Issue:** Only `load_raw_splits`/`compute_metrics` are imported; the pipeline re-fit, metric
computation, `joblib.dump`, and the entire `mlflow.start_run` block are copy-pasted from
`train.run_experiment`. Any fix (WR-05 temp-file dump, WR-06 isolation, WR-07 guard) must now be
applied twice, and the copies have already conceptually diverged (MLP adds the warnings block).
The 02-02 summary's "reuse, not a duplicated run loop" describes the estimator factory, not the
run body.
**Fix:** Parameterize one shared implementation in `train.py`:
```python
def run_experiment(name: str = "logistic-regression", estimator=None, run_name: str | None = None) -> dict:
    ...
    estimator = estimator if estimator is not None else build_estimator(name)
```
and reduce `train_mlp.run_experiment` to building the MLP estimator plus its ConvergenceWarning
handling, delegating the rest.

### WR-09: Claim-2 test re-implements training inline — it never executes `run_experiment`

**File:** `tests/test_training.py:75-121`
**Issue:** `test_run_logs_pipeline_and_model` hand-rolls pipeline-fit + estimator-fit + MLflow
logging instead of calling `tm.run_experiment("logistic-regression")`. A regression in the actual
unit under test (wrong artifact path, dropped metric, broken registration) still passes. The test
also asserts linkage via real-run plumbing it built itself, so it verifies the test's own code,
not the product's.
**Fix:** Call the real entry point against the tmp store and assert on its outputs:
```python
def test_run_logs_pipeline_and_model(tmp_path, monkeypatch):
    import src.training.train as tm
    monkeypatch.setattr(tm, "PROJECT_ROOT", tmp_path)
    out = tm.run_experiment("logistic-regression")
    client = mlflow.tracking.MlflowClient()
    assert out["run_id"]
    assert set(out["metrics"]) == {"accuracy", "precision", "recall", "f1", "roc_auc"}
```

### WR-10: Both conftest fixtures are dead code — and `tmp_mlflow_store` teardown restores the wrong URI

**File:** `tests/conftest.py:15-37`
**Issue:** Verified by import search: no test requests `synthetic_ckd_df` or `tmp_mlflow_store`;
both test modules roll their own `tmp_path`/`monkeypatch` plumbing instead, so the "Wave 0
fixtures reused by 02-02" narrative is aspirational. Worse, the unused fixture is itself buggy:
teardown does `mlflow.set_tracking_uri(uri)` (re-sets the *tmp* URI instead of restoring the
prior one, leaking tmp state into later tests), and it omits the `MLFLOW_ALLOW_FILE_STORE=true`
opt-in that `test_registry.py:39` had to add manually — any future consumer inherits both bugs.
**Fix:** Either wire the tests to the fixtures and fix teardown, or delete the file:
```python
@pytest.fixture
def tmp_mlflow_store(tmp_path, monkeypatch):
    uri = str(tmp_path / "mlruns")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    mlflow.set_tracking_uri(uri)
    yield uri
    # monkeypatch auto-reverts env; explicitly re-point client at the restored env
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", uri))
```

### WR-11: Claim-2 test reads the real committed artifact via a CWD-relative path

**File:** `tests/test_training.py:103-106`
**Issue:** `mlflow.log_artifact("data/processed/preprocessing_pipeline.joblib", ...)` touches the
real `data/` tree (violating conftest's "Never touches real data/" contract) and resolves relative
to CWD, so the test fails when pytest runs from any directory but the project root. It also couples
the test to whatever WR-05's last overwrite left behind.
**Fix:** Resolve through the same config path the product uses, or materialize the artifact from the
in-test pipeline object:
```python
from src.utils.config import load_config
pipe_path = Path(load_config()["data"]["processed_dir"]) / "preprocessing_pipeline.joblib"
```

## Info

### IN-01: `REGISTERED_MODEL_NAME` duplicated as a literal instead of imported

**File:** `src/evaluation/evaluate.py:33`
**Issue:** `train_mlp.py` imports the constant from `train.py`; `evaluate.py` re-declares
`REGISTERED_MODEL_NAME = "corvus-ckd"`. A rename in one place silently splits training from
evaluation (winner ranked under one name, stages applied under another).
**Fix:** `from src.training.train import REGISTERED_MODEL_NAME` (or move to `src/utils/config.py`
/ `config.yaml`).

### IN-02: Redundant second-pass archive after `archive_existing_versions=True`

**File:** `src/evaluation/evaluate.py:75-84`
**Issue:** The winner transition already archives existing versions; the explicit per-version
`Archived` loop then re-transitions each one — 8 redundant registry calls per run. Harmless but
wasteful and it doubles the non-atomic window from WR-04.
**Fix:** Drop the loop, or drop the flag and keep the explicit loop — not both.

### IN-03: Inconsistent result shape on failure; dead try/except in `main()`

**File:** `src/evaluation/evaluate.py:106-108,127-132`
**Issue:** The failure namespace carries only `(success, winner)` while success adds
`version`/`stage` — any caller touching `result.version` without checking `success` gets
`AttributeError`. Conversely, `main()`'s try/except around `run_evaluation()` is unreachable
defense: `run_evaluation` catches everything internally and never raises.
**Fix:** Always return all four keys (`version=None, stage=None` on failure); keep the `main()`
guard but note it covers only unexpected errors.

### IN-04: Import-time process-env mutation in three modules

**File:** `src/training/train.py:43`, `src/training/train_mlp.py:37`, `src/evaluation/evaluate.py:31`
**Issue:** `os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")` executes on import, so merely
importing these modules (as the tests do) mutates the caller's environment. `setdefault` respects
explicit user config, which is the right call — but the side effect belongs in `main()` entry
points, not module top level.
**Fix:** Move into a `_ensure_filestore_opt_in()` called from `main()`/`run_experiment()`.

### IN-05: Validation split loaded from disk, returned, unpacked — and never used

**File:** `src/training/train.py:123`, `src/training/train_mlp.py:69`
**Issue:** Both `run_experiment` bodies unpack `(X_val, y_val)` and never reference it (D-05 forbids
early stopping, so this is deliberate, not accidental). Still, every run pays two wasted CSV reads
and carries an unused variable through the signature, inviting a future val-peeking misuse.
**Fix:** Document with a comment (`# val split intentionally unused: D-05 forbids early stopping`)
or stop returning it.

### IN-06: Minor hardening notes (no action strictly required)

**File:** multiple
**Issue:** (a) `evaluate.py:111` interpolates `model_name` into the `search_model_versions` filter —
safe today (module constant) but prefer a parameterized/validated form if the name ever becomes
config- or caller-driven. (b) `print()` in `train.py:159` / `train_mlp.py:112` bypasses the
project Loguru convention (`log = get_logger()` already exists in both modules). (c) The
`test_loader_reads_raw_only` spy (`test_training.py:62-66`) replaces `pd.read_csv` on the shared
pandas module with a positional-`path` signature — breaks if the loader ever passes the path by
keyword; scope the spy to `tm.pd.read_csv` call args more defensively or assert on `load_config`
paths instead.
**Fix:** Log via `log.info`; validate model names against `^[A-Za-z0-9_.-]+$` if externalized.

---

_Reviewed: 2026-09-21_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
