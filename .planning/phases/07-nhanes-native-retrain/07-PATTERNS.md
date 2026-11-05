# Phase 7: NHANES Native Retrain - Pattern Map

**Mapped:** 2026-10-15
**Files analyzed:** 11 (4 new modules, 4 modified files, 3 new test files + conftest extension)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/training/train_nhanes.py` (new) | service/script | batch | `src/training/train.py` | exact |
| `src/training/train_mlp.py` reuse for MLP×3 native | service | batch | `src/training/train_mlp.py` | exact |
| `src/preprocessing/preprocess_nhanes.py` (new) | service | transform | `src/preprocessing/preprocess.py` | exact |
| `src/training/harmonize_v9.py` (new, eval-only) | utility | transform | `src/preprocessing/preprocess.py` (`clean_raw` + `get_column_lists`) | role-match |
| `src/evaluation/evaluate_nhanes.py` (new) | service | batch | `src/evaluation/evaluate.py` | exact |
| `scripts/promote_challenger.py` or gate step (new, optional) | script | request-response | `scripts/promote_production.py` | exact |
| `api/schemas.py` (modify: add `CKDRequestNative`) | model/schema | request-response | `api/schemas.py` (`CKDRequest`) | exact |
| `api/model_loader.py` (modify: second slot) | service | request-response | `api/model_loader.py` | exact |
| `api/app.py` (modify: add `/v2/*` routes) | controller/route | request-response | `api/app.py` | exact |
| `api/db.py` (modify: add v2 log table) | model | CRUD | `api/db.py` (`PredictionLog`) | exact |
| `config/config.yaml` (modify: add keys) | config | transform | `config/config.yaml` | exact |
| `tests/test_train_nhanes.py` + `test_evaluate_nhanes.py` + `test_compare.py` + `test_api_v2.py` (new) | test | batch/request-response | `tests/test_training.py` + `tests/test_api.py` + `tests/conftest.py` | exact |

## Pattern Assignments

### `src/training/train_nhanes.py` (service/script, batch)

**Analog:** `src/training/train.py`

**Imports pattern** (lines 11-38):
```python
from pathlib import Path
import joblib
import mlflow
import mlflow.sklearn
import os
import pandas as pd
from sklearn.linear_model import LogisticRegression
# ... ESTIMATORS dict covers 6 classical configs
from src.preprocessing.preprocess import (
    LINEAGE_ID_COL, LINEAGE_ROW_COL, build_pipeline, get_column_lists,
)
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger
log = get_logger()
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
REGISTERED_MODEL_NAME = "corvus-ckd"
```

**Estimator factory pattern** (lines 50-71): reuse `ESTIMATORS` dict verbatim for 6 classical configs + `build_estimator(name)` fresh-instance via `base.__class__(**base.get_params())` — copy for native; MLP×3 reuse `src/training/train_mlp.py:ACTIVATIONS` + `build_estimator` (lines 42-60).

**Core Claim-2 run pattern** (lines 124-160): `run_experiment(name)` shape to generalize — `mlflow.set_tracking_uri(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"])` → `set_experiment` → load splits → `build_pipeline(...).fit(X_train-only)` → `estimator.fit(transform(X_train))` → `compute_metrics` (5 metrics, ROC-AUC from proba col 1, lines 113-121) → `joblib.dump(pipeline)` → single `mlflow.start_run` logging params + metrics + pipeline artifact (`artifact_path="preprocessing"`) + `mlflow.sklearn.log_model(..., registered_model_name="corvus-ckd", serialization_format="cloudpickle")`. Native additions only: quarantine gate before split, `mlflow.set_tag("schema","nhanes-native")` + quarantine-attestation tag, CV-mean/CI metrics alongside holdout metrics.

**Warning-not-crash on unexpected columns** (lines 90-96): compute `unexpected = set(df.columns) - known - {target, lineage...}` → `log.warning(...)`, never raise. Copy for native allow-list extras.

**Entry pattern** (lines 163-170): `def main(): for name in ESTIMATORS: run_experiment(name)` + `if __name__ == "__main__": main()`, invoked as `python -m src.training.train_nhanes`.

**MLP convergence pattern** — from `src/training/train_mlp.py:79-85`:
```python
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always", ConvergenceWarning)
    estimator.fit(pipeline.transform(X_train), y_train)
for warning in caught:
    log.warning(f"MLP ({activation_name}) training notice: {warning.message}")
```
Copy verbatim — log `ConvergenceWarning`, never raise (Pitfall 5: n=4,274 changes convergence vs Phase 2).

---

### `src/preprocessing/preprocess_nhanes.py` (service, transform)

**Analog:** `src/preprocessing/preprocess.py`

**Column-list source of truth** (lines 100-105):
```python
def get_column_lists() -> tuple[list[str], list[str]]:
    cfg = load_config()
    numeric = cfg["data"].get("numeric_cols") or list(_DEFAULT_NUMERIC_COLS)
    categorical = cfg["data"].get("categorical_cols") or list(_DEFAULT_CATEGORICAL_COLS)
    return list(numeric), list(categorical)
```
Native module mirrors this but reads NEW config keys (`data.nhanes_numeric_cols` / `data.nhanes_categorical_cols`); planner decides exact key names — additive keys only.

**Pipeline builder** (lines 201-247): `build_pipeline(numeric_cols, categorical_cols)` returns UNFITTED `Pipeline([("preprocessor", ColumnTransformer)])` with numeric `SimpleImputer(strategy=cfg["preprocessing"]["numeric_impute_strategy"])` [median] + optional `StandardScaler`, categorical `SimpleImputer(most_frequent)` + `OneHotEncoder(handle_unknown="ignore", drop="first")`. Copy verbatim — RESEARCH.md "Don't Hand-Roll" mandates reuse; native builder differs only in column lists passed in.

**Leak-safe fit discipline** (lines 263-269): `pipeline.fit(X_train)` — fit on train/dev/fold-train ONLY, then `.transform()` everything else. Native CV must `build_native_pipeline().fit(fold-train)` fresh per fold (RESEARCH Pattern 1).

**Split pattern** (lines 180-198): `train_test_split(..., random_state=cfg["split"]["random_state"], stratify=...)`. Native locked split: `train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)` for dev/holdout, then `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` on dev only.

**Immutable inputs** (line 127): `df = df.copy()` at top of every cleaning function. Copy.

---

### `src/training/harmonize_v9.py` (utility, transform — EVAL-ONLY)

**Analog:** `src/preprocessing/preprocess.py` (`clean_raw` lines 114-162 + `get_column_lists`)

**What to copy:** the column-mapping + coerce idiom — explicit allow-list, `pd.to_numeric(..., errors="coerce")` per numeric col, warning-not-crash on unclassified columns (lines 134-148). The adapter maps 9 shared numerics (age, BUN→bu, glucose→bgr, Na→sod, K→pot, HGB→hemo, HCT→pcv, WBC→wc, RBC-count→rc — A1 pending CDC verification), fills v9's 10 categoricals (rbc, pc, pcc, ba, htn, dm, cad, appet, pe, ane per `config.yaml:12`) with the FROZEN UCI pipeline's own most-frequent imputations, and passes through v9's frozen fitted pipeline + estimator — never refit.

**Isolation rule (hard):** `api/` must never import this module. Enforce with `tests/test_compare.py::test_adapter_not_served` (import scan). No existing analog for the ban — new test, RESEARCH Pitfall anti-pattern.

---

### `src/evaluation/evaluate_nhanes.py` (service, batch)

**Analog:** `src/evaluation/evaluate.py`

**Imports + registry constants** (lines 11-35):
```python
import mlflow
from mlflow.tracking import MlflowClient
from sklearn.metrics import (accuracy_score, f1_score, precision_score, recall_score, roc_auc_score)
from src.utils.config import PROJECT_ROOT, load_config
from src.utils.logger import get_logger
log = get_logger()
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
REGISTERED_MODEL_NAME = "corvus-ckd"
METRIC_NAMES = ("accuracy", "precision", "recall", "f1", "roc_auc")
```

**Strict-max selection** (lines 50-52): `def select_winner(runs): return max(runs, key=lambda r: r["metrics"]["roc_auc"])` — no tie-break by design. Native: strict-max on CV-mean AUC for selection; final rank on locked holdout.

**Run→version linkage** (lines 55-66): `resolve_winner_version(versions, winner_run_id)` via `v.run_id == winner_run_id`, fallback latest. Copy verbatim for challenger v10+ resolution.

**Stage transitions** (lines 69-89): `apply_registry_stages` — `client.transition_model_version_stage(name, version, stage="Staging", archive_existing_versions=True)`, superseded → `"Archived"`; never Production (D-06/D-04: human gate promotes). Copy verbatim; winner → Staging as challenger posture.

**Evaluation runner shape** (lines 92-130): `run_evaluation()` — set tracking URI, `MlflowClient`, `get_experiment_by_name` → `search_runs` FINISHED → filter complete-metric records → `select_winner` → resolve version → apply stages → `SimpleNamespace(success, winner, version, stage)`; `except Exception: log.warning(...); return SimpleNamespace(success=False, winner=None)` (warning-not-crash). Entry: `def main() -> int` returning 0/1 + `sys.exit(main())` (lines 133-151).

**Native additions (from RESEARCH Code Examples):** paired stratified bootstrap (B=2000, `np.random.default_rng(42)`, resample holdout indices once, score both models per resample, `np.percentile(diffs,[2.5,97.5])` for CI of AUC_c−AUC_v9). No DeLong. Never `cross_val_predict`-pooled AUC.

---

### `scripts/promote_challenger.py` or gate step (script, request-response)

**Analog:** `scripts/promote_production.py` (entire file, 60 lines)

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # lines 15-17: plain-script path fix
mlflow.set_tracking_uri(tracking_uri)  # env MLFLOW_TRACKING_URI wins, else PROJECT_ROOT/mlruns
client = MlflowClient()
client.transition_model_version_stage(name="corvus-ckd", version=PROMOTE_VERSION, stage="Production", archive_existing_versions=True)
def main() -> int: try/except → print PROMOTED/PROMOTION ERROR → return 0/1
if __name__ == "__main__": sys.exit(main())
```
Copy shape; version comes from the human-gate decision (challenger v10+), never auto-computed. No auto-promote (D-04).

---

### `api/schemas.py` — add `CKDRequestNative` (model/schema, request-response)

**Analog:** `api/schemas.py:28-54` (`CKDRequest`)

```python
class CKDRequest(BaseModel):
    age: float | None   # numerics nullable → blanks flow to pipeline imputers (D-05)
    # ... 14 numerics float|None, 10 categoricals as Literal vocabularies
    rbc: Literal["abnormal", "normal"]
    # ... bad values fail fast with automatic 422 before inference (D-06)
```
Copy: numerics `float | None` (null → imputer, never 422); categoricals `Literal[...]` vocabularies verified against NHANES source (fail-closed 422); NO `ge`/`le` range bounds (lines 8-10 rationale: raw extremes wider than any split — range checks false-reject real patients). v1 `CKDRequest` byte-identical — new class only. Response types (`PredictionResponse`, `BatchPredictionResponse`) reused as-is.

---

### `api/model_loader.py` — second serving slot (service, request-response)

**Analog:** `api/model_loader.py` (entire file)

```python
def resolve_pinned_version() -> str:  # lines 53-59
    override = os.environ.get("MODEL_VERSION")
    if override: return str(override)
    return str(load_config()["api"]["pinned_version"])

def resolve_tracking_uri(cfg=None) -> str:  # lines 62-75: MLFLOW_TRACKING_URI env → api.tracking_uri → mlflow.tracking_uri; relative anchors at PROJECT_ROOT
def load_serving_artifacts(version: str):  # lines 78-115
    client.get_model_version(REGISTERED_MODEL_NAME, version) → run_id
    model = mlflow.sklearn.load_model(f"models:/{REGISTERED_MODEL_NAME}/{version}")
    pipe_path = mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path="preprocessing/preprocessing_pipeline.joblib")
    pipeline = joblib.load(pipe_path)
    # width assert: probe frame → pipeline.transform(probe).shape[1] == model.n_features_in_ else RuntimeError
```
Copy: `resolve_v2_version()` reading `MODEL_VERSION_V2` env else NEW `api.v2_pinned_version` config key (RESEARCH Code Examples lines 280-290); second loader fn loading `models:/corvus-ckd/<v2>` + co-logged NATIVE pipeline with the same width assert (native probe categoricals must be native-schema literals). v1 `resolve_pinned_version`/`load_serving_artifacts` byte-identical. `PIPELINE_ARTIFACT_PATH = "preprocessing/preprocessing_pipeline.joblib"` constant reused (line 35).

---

### `api/app.py` — add `/v2/predict` + `/v2/batch_predict` (controller/route, request-response)

**Analog:** `api/app.py`

**Lifespan** (lines 58-71): pin version → `load_serving_artifacts` → `app.state.model_version/model/pipeline/run_id` → `db.get_engine()` + `Session.configure` → `db.create_tables()` → yield. v2 extends with `app.state.v2_*` slots; v1 slot assignments byte-identical.

**Guards** (lines 53-55, 77-83): `MAX_BATCH_BYTES = 5000000`, `MAX_BATCH_ROWS = 10000`; `_require_log_store()` → 503 naming DATABASE_URL when unset (never silent serving, never SQLite).

**Single predict** (lines 86-139): `_frame_from_request` (single-row frame in config column order) → `_predict_frame` (pipeline.transform → predict/proba; `except Exception: log.warning(type name); raise 500 "inference failed"`, lines 91-100) → `_log_predictions` (one row per prediction, single commit all-or-nothing, rollback + 500 on failure, `created_at=datetime.now()` stamp, lines 103-125) → versioned JSON. v2 mirrors with `CKDRequestNative` + `COLUMN_ORDER_V2` + v2 log table + `app.state.v2_*`.

**Batch** (lines 142-194): size/row caps (413) → utf-8 decode (422) → `pd.read_csv` (422) → drop `DROP_COLS` lineage/target via constants → warn-and-ignore unexpected cols → 422 naming missing cols → per-row `CKDRequest(**clean)` validation naming `row {i}` 1-indexed → single commit → `BatchPredictionResponse` with `model_version`. Copy entire shape for v2.

**500 handler** (lines 214-217): `_no_traceback_500` → `{"detail": "internal error"}`, no traceback. Applies to v2 automatically.

---

### `api/db.py` — add v2 log table (model, CRUD)

**Analog:** `api/db.py:29-69` (`PredictionLog`)

```python
class PredictionLog(Base):  # __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    age: Mapped[float | None] = mapped_column(Float, nullable=True)  # numerics nullable
    rbc: Mapped[str] = mapped_column(String(16))  # categoricals String(16)
    prediction: Mapped[int] = mapped_column(Integer)
    probability: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), default=datetime.datetime.now)
Session = sessionmaker()  # unbound; lifespan binds; tests patch wholesale
def get_database_url(): return os.environ.get("DATABASE_URL") or load_config()["db"].get("database_url","") or ""
def get_engine(): None when unset (never log URL value); create_engine(url) otherwise
def create_tables(retries=3): create_all with retries + loud RuntimeError after 3 (lines 97-124)
```
Copy: new `PredictionLogV2` (planner names table — recommendation `predictions_v2`) with NATIVE fields + same outcome/version/timestamp columns; v1 `PredictionLog`/`predictions` byte-identical (D-05/Pitfall 6). `Base.metadata.create_all` picks up the new table with zero changes to `create_tables`.

---

### `config/config.yaml` — additive keys (config, transform)

**Analog:** `config/config.yaml` (48 lines; `load_config()` deepcopy in `src/utils/config.py:18-28`)

```yaml
data: { numeric_cols: [...14], categorical_cols: [...10], target_column, positive_label, ... }
mlflow: { tracking_uri: "mlruns", experiment_name: "corvus-ckd" }
api: { model_name: "corvus-ckd", pinned_version: "9", tracking_uri: "mlruns" }
```
Additive-only: NEW `data.nhanes_*` keys (CSV path, native numeric/categorical lists, target/label, quarantine list) + NEW `api.v2_*` keys (`v2_pinned_version`, optionally v2 tracking/experiment). Never rename existing keys (A5: `load_config` is plain-YAML deepcopy — additive keys safe by construction). Note `load_config` resolves only `data.raw_path/processed_dir/validation_dir` to absolute (lines 25-27) — if `nhanes_csv` needs absolute resolution, handle at read site or extend `load_config` with a parallel line.

---

### Tests — `test_train_nhanes.py`, `test_evaluate_nhanes.py`, `test_compare.py`, `test_api_v2.py`

**Analogs:** `tests/test_training.py`, `tests/test_api.py`, `tests/conftest.py`

**Synthetic-fixture pattern** — from `tests/conftest.py:19-39`:
```python
@pytest.fixture
def synthetic_ckd_df():  # 40-row synthetic frame; never real data/
@pytest.fixture
def tmp_mlflow_store(tmp_path, monkeypatch):  # tracking URI → tmp_path/mlruns; never real mlruns/
```
Native tests need a synthetic NHANES-shaped fixture (labs + demographics + derived-like label; include quarantine cols to test the abort) + `tmp_path`/`tmp_mlflow_store` isolation. Never touch real `mlruns/` or Postgres (locked convention).

**Claim-2 assertion shape** — from `tests/test_training.py:103-126`: log params + 5 metrics in tmp store → `client.list_artifacts(run_id,"")` contains `"preprocessing"` → logged-model linkage via `mlflow.search_logged_models` → all 5 metric names in `client.get_run(run_id).data.metrics`. Copy for `test_claim2_native`.

**API stub pattern** — from `tests/test_api.py:23-56`: `_StubEstimator`/`_StubPipeline` + autouse `_serving_stub` (DATABASE_URL dummy env, `create_tables` no-op, `load_serving_artifacts` monkeypatched, `db.Session` MagicMock). v2 tests mirror with DUAL-slot stub loader; key cases: `/v2` 422 on missing native field, null-numeric passes (imputer path, cf. lines 82-87), batch all-or-nothing naming offender row, v1 table columns unchanged, `api/`-never-imports-`harmonize_v9` scan.

**Config/estimator smoke** — from `tests/test_training.py:14-51`: `ESTIMATORS` exact-set + `random_state==42` per estimator; MLP `ACTIVATIONS` map + `hidden_layer_sizes==(50,)` + `max_iter` + seed; 9-count assertion. Native: same shape over native factories.

## Shared Patterns

### MLflow file-store opt-in
**Source:** `src/training/train.py:44`, `src/training/train_mlp.py:37`, `src/evaluation/evaluate.py:32`, `api/model_loader.py:19`
**Apply to:** every new module touching MLflow (`train_nhanes.py`, `evaluate_nhanes.py`)
```python
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
```

### Entry-point convention
**Source:** `src/training/train.py:163-170`, `src/evaluation/evaluate.py:133-151`, `scripts/promote_production.py:57-60`
**Apply to:** all new runnable modules
```python
def main(): ...
if __name__ == "__main__": main()  # or sys.exit(main()) for int-returning mains
```
Invoked as `python -m <dotted.path>` from project root; plain `scripts/*.py` runs add the `sys.path.insert(0, ...parents[1])` header (promote script lines 15-17).

### Logging
**Source:** `src/utils/logger.py:12-28`
**Apply to:** all new modules
```python
from src.utils.logger import get_logger
log = get_logger()  # loguru, dual sink stderr + rotating logs/corvus.log; use log.warning/log.info
```
Never log `DATABASE_URL` values — only whether a store is configured (`api/db.py:86-94`).

### Config access
**Source:** `src/utils/config.py:18-28`
**Apply to:** all new modules needing config
```python
from src.utils.config import PROJECT_ROOT, load_config
cfg = load_config()  # fresh deepcopy per caller; PROJECT_ROOT anchors relative mlruns paths
```

### Error handling — fail closed, warning-not-crash
**Source:** `api/app.py:91-100` (inference 500 without traceback), `api/app.py:77-83` (503 naming DATABASE_URL), `src/training/train.py:90-96` + `api/app.py:170-173` (unexpected columns → `log.warning`, never fed to pipeline), `src/training/train_mlp.py:79-85` (ConvergenceWarning logged, never raised), `src/evaluation/evaluate.py:128-130` (eval failure → warning + `success=False`)
**Apply to:** training (quarantine breach is the ONE abort case: `raise SystemExit` per RESEARCH snippet — a deliberate fail-closed exception to the warning rule), eval (failures warn + `success=False`), serving (422/503/500 shapes above).

### Test isolation
**Source:** `tests/conftest.py:32-39`, `tests/test_api.py:46-56`
**Apply to:** all new test files — synthetic fixtures, `tmp_path` MLflow store, mocked `db.Session`, never real `data/`, `mlruns/`, or Postgres.

### D-08 disclosure string
**Source:** new this phase (no analog) — every logged/reported metric carries a "derived labels, internal-only, unweighted" disclosure next to the numbers (RESEARCH Security Domain + Pitfall disclosure). Planner must define the exact string once and reuse it in `train_nhanes.py`, `evaluate_nhanes.py`, and any report output.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/training/train_nhanes.py` quarantine-gate block | guard | batch | No abort-gate exists in codebase (closest is `preprocess.py:main` `raise SystemExit` on validation failure, line 335 — use that single line as the idiom). Gate code itself comes from RESEARCH.md (`QUARANTINE` 11-name set + `raise SystemExit(f"QUARANTINE BREACH — aborting: ...")`). |
| Paired-bootstrap difference-CI block | utility | batch | No bootstrap code exists in repo. Use RESEARCH.md Code Examples snippet verbatim (`default_rng(42)`, B=2000, stratified resample, `np.percentile(diffs,[2.5,97.5])`). |
| `predictions_v2` DDL / v2 table shape | model | CRUD | No second table exists. Open Question Q2 — planner decides; `PredictionLog` is the column-idiom analog only. |
| Native lab-code mapping (A1) | — | — | Pending CDC-doc verification task (Wave 0). Do not copy UCI column semantics onto NHANES codes. |

## Metadata

**Analog search scope:** `src/training/`, `src/preprocessing/`, `src/evaluation/`, `src/utils/`, `api/`, `scripts/`, `config/`, `tests/`
**Files scanned:** 15 tracked source files via glob + 9 full reads (no range re-reads; small files read whole)
**Git-tracked gate:** all 15 analog paths verified via `git ls-files` (non-empty = tracked); no mirror/untracked paths emitted
**Pattern extraction date:** 2026-10-15
