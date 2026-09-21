# Phase 2: Model Training + Experiment Tracking - Pattern Map

**Mapped:** 2026-09-21
**Files analyzed:** 6 (3 new source, 3 new test)
**Analogs found:** 5 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/training/train.py` | service | batch | `src/preprocessing/preprocess.py` | role-match |
| `src/training/train_mlp.py` | service | batch | `src/preprocessing/preprocess.py` | role-match |
| `src/evaluation/evaluate.py` | service | batch | `src/validation/validate.py` | role-match |
| `tests/test_training.py` | test | batch | `tests/test_preprocessing.py` | exact |
| `tests/test_evaluation.py` | test | batch | `tests/test_preprocessing.py` | role-match |
| `tests/conftest.py` | config | batch | — (none exists) | no-analog |

`config/config.yaml` needs no structural change (mlflow keys already present, lines 35-37) — referenced, not modified. No `pip install` step: all deps pre-installed in `./venv`.

## Pattern Assignments

### `src/training/train.py` (service, batch)

**Analog:** `src/preprocessing/preprocess.py` (git-tracked ✓)

**Imports pattern** (lines 43-57):
```python
from pathlib import Path
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
# ...
from src.ingestion.load_data import load_raw_data
from src.utils.config import load_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.validation.validate import run_raw_validation

log = get_logger()
```

**Config-driven entry pattern** (lines 78-83, 284-302): every function calls `load_config()` for column lists/paths/thresholds; no hardcoded paths in module bodies. Entry is `def main()` + `if __name__ == "__main__": main()`, invoked as `python -m src.training.train`. Fail-closed gate at top of `main()`: `run_raw_validation()` → `raise SystemExit(...)` on failure (lines 285-288).

**Immutable-input + warning-not-crash pattern** (lines 100-123): `df = df.copy()` on entry; unexpected columns produce `log.warning(...)` and are dropped, never crash. Copy this for dropping `[LINEAGE_ROW_COL, LINEAGE_ID_COL, target]` from X after loading `*_raw.csv`.

**Claim 2 input shape** (lines 220-238): fresh pipeline via `build_pipeline(numeric_cols, categorical_cols)`, `pipeline.fit(X_train)` on train-only, then `transform` val/test. Training must re-fit a fresh pipeline on train-raw (joblib.load the artifact shape or rebuild via `build_pipeline`); never read transformed `train.csv`.

---

### `src/training/train_mlp.py` (service, batch)

**Analog:** `src/preprocessing/preprocess.py` (git-tracked ✓) — same file as `train.py`.

Same three excerpts as `train.py` above (imports lines 43-57, config-driven `main()` lines 284-306, immutable-input lines 100-123). Per RESEARCH anti-patterns, `train_mlp.py` is a thin variant differing only in the estimator factory — do NOT duplicate the run loop into a god-function:

```python
# RESEARCH-verified (sklearn 1.9.1 ACTIVATIONS keys; "sigmoid" is NOT valid)
from sklearn.neural_network import MLPClassifier
ACTIVATIONS = {"sigmoid": "logistic", "tanh": "tanh", "relu": "relu"}
model = MLPClassifier(hidden_layer_sizes=(50,), activation=ACTIVATIONS["sigmoid"],
                      max_iter=500, random_state=42)
```

**MLflow per-run shape** (from RESEARCH.md Pattern 1 — no in-repo analog exists, use verbatim):
```python
mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))  # NOT raw "mlruns"
mlflow.set_experiment(cfg["mlflow"]["experiment_name"])  # "corvus-ckd"
with mlflow.start_run(run_name="random-forest"):
    mlflow.log_params({"model": "RandomForestClassifier", "random_state": 42})
    mlflow.log_metrics({"accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "roc_auc": auc})
    mlflow.log_artifact(str(pipeline_path), artifact_path="preprocessing")
    mlflow.sklearn.log_model(model, artifact_path="model",
                             registered_model_name="corvus-ckd",
                             serialization_format="cloudpickle")  # pin: 3.x default is skops
```

---

### `src/evaluation/evaluate.py` (service, batch)

**Analog:** `src/validation/validate.py` (untracked working-tree file, genuine Phase-1 source — not a capability mirror; no `.gsd/` mirror dirs exist in repo)

**Fail-closed gate + int-exit `main()` pattern** (lines 86-140):
```python
def run_raw_validation(df=None):
    cfg = load_config()
    if df is None:
        df = load_raw_data(raw_path=cfg["data"]["raw_path"])
    try:
        # ... compute ...
        return result            # carries .success bool
    except Exception as exc:
        log.warning(f"Raw-data validation failed: {type(exc).__name__}: {exc}")
        return SimpleNamespace(success=False)   # fail closed, never traceback on data failure

def main() -> int:
    try:
        result = run_raw_validation()
    except Exception as exc:
        print(f"RAW VALIDATION ERROR: {exc}")
        return 1
    if result.success:
        print("RAW VALIDATION PASSED")
        return 0
    print("RAW VALIDATION FAILED — see log for failing expectations")
    return 1

if __name__ == "__main__":
    sys.exit(main())
```
Copy this shape: `run_evaluation()` returning a result with `.success`, `main() -> int` with `sys.exit(main())`.

**Metric + ranking snippet** (from RESEARCH.md Code Examples — no in-repo analog, use verbatim):
```python
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
y_proba = model.predict_proba(X_test)[:, 1]  # probas, NOT labels
metrics = {
    "accuracy": accuracy_score(y_test, y_pred),
    "precision": precision_score(y_test, y_pred, zero_division=0),
    "recall": recall_score(y_test, y_pred, zero_division=0),
    "f1": f1_score(y_test, y_pred, zero_division=0),
    "roc_auc": roc_auc_score(y_test, y_proba),
}
winner = max(runs, key=lambda r: r["metrics"]["roc_auc"])  # strict, no tie-break (D-03)
```

**Registry transition snippet** (from RESEARCH.md — `transition_model_version_stage` hasattr-verified on mlflow 3.16.1):
```python
from mlflow.tracking import MlflowClient
client = MlflowClient()
client.transition_model_version_stage(name="corvus-ckd", version=winner_version,
                                      stage="Staging", archive_existing_versions=True)
for v in superseded_versions:
    client.transition_model_version_stage(name="corvus-ckd", version=v, stage="Archived")
# NEVER transition to Production here (D-06: separate explicit step)
```

---

### `tests/test_training.py` (test, batch)

**Analog:** `tests/test_preprocessing.py` (untracked working-tree file, genuine Phase-1 source — not a mirror)

**Synthetic-fixture pattern** (lines 21-34): 40-row CKD-shaped frame, never touches real data:
```python
NUMERIC_COLS, CATEGORICAL_COLS = get_column_lists()

@pytest.fixture
def synthetic_df():
    n = 40
    data = {col: [float(i % 5) for i in range(n)] for col in NUMERIC_COLS}
    for col in CATEGORICAL_COLS:
        data[col] = ["yes" if i % 2 == 0 else "no" for i in range(n)]
    data["classification"] = ["ckd" if i % 3 == 0 else "notckd" for i in range(n)]
    df = pd.DataFrame(data)
    df.loc[0, NUMERIC_COLS[0]] = None
    df.loc[1, CATEGORICAL_COLS[0]] = None
    return df
```

**Config-truth assertion** (lines 37-46): column lists must equal `config.yaml`, legacy aliases covered:
```python
def test_column_lists_come_from_config():
    from src.utils.config import load_config
    cfg = load_config()
    assert NUMERIC_COLS == cfg["data"]["numeric_cols"]
    assert CATEGORICAL_COLS == cfg["data"]["categorical_cols"]
```

**Leakage-proof assertion style** (lines 74-95): assert imputer statistics equal train medians exactly; adapt to assert lineage exclusion (`feature count == 24`, `__source_row`/`__source_id` absent from X) and that the loader never references non-`raw` CSV names.

---

### `tests/test_evaluation.py` (test, batch)

> Alias note: plans implement this scope as `tests/test_registry.py` (registry lifecycle tests) alongside `tests/test_training.py`; the analog substance below applies to both.

**Analog:** `tests/test_preprocessing.py` (same as above) for fixture + assertion style; **plus** `tests/test_save_outputs.py` (git-tracked ✓) for isolation discipline.

**Isolation pattern** (`test_save_outputs.py` lines 52-68, 102-103): redirect persistence via monkeypatched `load_config` into `tmp_path`, snapshot the real dir before/after and assert byte-identical:
```python
override = copy.deepcopy(real_cfg)
override["data"]["processed_dir"] = str(tmp_path)
load_config.cache_clear()
monkeypatch.setattr(preprocess_mod, "load_config", lambda *a, **k: override)
# ...
assert _snapshot_dir(real_processed) == before
```
Apply to MLflow: point `tracking_uri` at `tmp_path` (never real `mlruns/`); mock `MlflowClient` for stage-transition assertions (winner→Staging, superseded→Archived, exact stage strings).

---

## Shared Patterns

### Config access
**Source:** `src/utils/config.py` (lines 7-27; untracked working-tree file, genuine source)
**Apply to:** `train.py`, `train_mlp.py`, `evaluate.py`
```python
from src.utils.config import load_config, PROJECT_ROOT
cfg = load_config()  # caller-owned deepcopy; mutating it never poisons later callers
```
Only `data.raw_path/processed_dir/validation_dir` resolve to absolute — `mlflow.tracking_uri` does NOT, so always `str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"])` (Pitfall 7). Tests resetting config call `load_config.cache_clear()`.

### Logging
**Source:** `src/utils/logger.py` (lines 11-27; untracked working-tree file, genuine source)
**Apply to:** all three source modules
```python
from src.utils.logger import get_logger
log = get_logger()  # module-level; Loguru to stderr + rotating file. Never stdlib logging.
```

### Entry point
**Source:** `src/preprocessing/preprocess.py` lines 284-306 / `src/validation/validate.py` lines 126-140
**Apply to:** all three source modules — `def main()` (+ `-> int` + `sys.exit(main())` for evaluate's gate), invoked as `.\venv\python.exe -m src.training.train` from root.

### Lineage constants
**Source:** `src/preprocessing/preprocess.py` lines 74-75 (git-tracked ✓)
**Apply to:** `train.py`, `train_mlp.py`, test files — import, never re-type:
```python
from src.preprocessing.preprocess import LINEAGE_ROW_COL, LINEAGE_ID_COL  # "__source_row", "__source_id"
```

### Booster / MLP construction gotchas (RESEARCH-verified vs installed venv)
**Apply to:** `train.py`, `train_mlp.py`
```python
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
XGBClassifier(random_state=42)                    # seed hides in **kwargs; verified accepted
LGBMClassifier(random_state=42, verbosity=-1)     # NO `verbose` param in 4.7.0; `verbosity` only
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/conftest.py` | config | batch | No conftest.py exists in repo; planner should follow RESEARCH.md Wave 0 spec (shared 40-row synthetic CKD fixture) plus TESTING.md gap #5 |

## Metadata

**Analog search scope:** `src/**/*.py` (17 files), `tests/**/*.py` (5 files), `config/config.yaml`
**Files scanned:** 23
**Git-tracked analogs:** `src/preprocessing/preprocess.py` ✓, `tests/test_save_outputs.py` ✓ (`git ls-files` confirmed). Remaining analogs (`validate.py`, `config.py`, `logger.py`, `load_data.py`, `test_preprocessing.py`) are uncommitted Phase-1 working-tree source, not capability mirrors (no `.gsd/` mirror dirs exist; `git status` shows them as `??`). No mirror paths emitted.
**Pattern extraction date:** 2026-09-21
