# Phase 3: Prediction API + Containerization - Pattern Map

**Mapped:** 2026-09-23
**Files analyzed:** 12 (9 new, 3 modified)
**Analogs found:** 8 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/app.py` | route/controller | request-response | `src/validation/validate.py` (fail-closed gate + `main() -> int`) | role-match |
| `api/schemas.py` | model (validation) | transform | `src/preprocessing/preprocess.py` (`get_column_lists`, lines 78-83) | role-match |
| `api/model_loader.py` | service | request-response (startup) | `src/evaluation/evaluate.py` (MlflowClient + stage transitions) | exact |
| `api/db.py` | store/model | CRUD | — none (no SQLAlchemy anywhere in repo) | no-analog |
| `scripts/promote_production.py` | script/utility | batch (one-shot) | `src/evaluation/evaluate.py` (`apply_registry_stages` + `main`) | exact |
| `docker/Dockerfile` | config | file-I/O (build) | — none (no Docker files in repo) | no-analog |
| `docker/docker-compose.yml` | config | file-I/O (orchestration) | — none | no-analog |
| `frontend/app.py` | component (client) | request-response | — none (no Streamlit/httpx client in repo) | no-analog |
| `tests/test_api.py` | test | request-response | `tests/test_registry.py` + `tests/conftest.py` | exact |
| `config/config.yaml` (modify) | config | file-I/O | itself (extend `mlflow.*` pattern, lines 35-37) | exact |
| `requirements.txt` (modify) | config | file-I/O | itself (phase-labeled sections, lines 23-26) | exact |
| `tests/conftest.py` (modify) | test | batch (fixtures) | itself (`synthetic_ckd_df` + `tmp_mlflow_store`) | exact |

**Tracked-source gate:** every analog below was verified git-tracked via `git ls-files -- src tests`
(`src/evaluation/evaluate.py`, `src/preprocessing/preprocess.py`, `src/training/train.py`,
`src/validation/validate.py`, `src/utils/config.py`, `src/utils/logger.py`,
`src/ingestion/load_data.py`, `tests/conftest.py`, `tests/test_registry.py`,
`tests/test_training.py` all listed). `api/`, `docker/`, `frontend/` are untracked/empty —
no analog is emitted from them. `config/config.yaml` and `requirements.txt` are
modify-targets, not analogs.

## Pattern Assignments

### `api/app.py` (route/controller, request-response)

**Analog:** `src/validation/validate.py` — fail-closed gate + `main() -> int` entry contract

**Imports pattern** (`src/validation/validate.py`, lines 19-35):
```python
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
# ...
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()
```
Copy: module-level `log = get_logger()` (same in `train.py:39`, `evaluate.py:27`,
`preprocess.py:57`, `load_data.py:26`). Every new `api/*.py` module opens with this.

**Fail-closed pattern** (`src/validation/validate.py`, lines 121-123):
```python
    except Exception as exc:
        log.warning(f"Raw-data validation failed: {type(exc).__name__}: {exc}")
        return SimpleNamespace(success=False)
```
Copy: catch-all → `log.warning` with `{type(exc).__name__}: {exc}` → degraded-but-typed
return, never a raw traceback. In `api/app.py` this maps to: unexpected inference
failure → log + 500 JSON, never a stack trace to the client. Pydantic 422s need no
try/except (automatic, per RESEARCH).

**Entry-point pattern** (`src/validation/validate.py`, lines 126-140;
also `src/ingestion/load_data.py:67-100`):
```python
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
Copy: `def main() -> int` returning 0/1 with `sys.exit(main())`. The uvicorn launch
(`uvicorn api.app:app`) replaces `python -m`, but any `api/` runnable helper keeps
this shape. Note `load_data.main()` raises `SystemExit(...)` on gate failure
(lines 75-77) — same fail-closed instinct the D-06 422 path mirrors.

**Warn-on-extras pattern** (`src/training/train.py`, lines 89-93):
```python
        unexpected = set(df.columns) - set(
            get_column_lists()[0] + get_column_lists()[1]
        ) - {target_col, LINEAGE_ROW_COL, LINEAGE_ID_COL}
        if unexpected:
            log.warning(f"Unexpected columns in {path.name}: {unexpected}")
```
Copy verbatim logic for `/batch_predict` CSV column handling (Pitfall 4): drop
`{target, __source_row, __source_id}`, `log.warning` on anything else, never feed
extras to the pipeline.

---

### `api/schemas.py` (model/validation, transform)

**Analog:** `src/preprocessing/preprocess.py` — config-driven column lists + lineage constants

**Single-source-of-truth pattern** (`src/preprocessing/preprocess.py`, lines 74-83):
```python
LINEAGE_ROW_COL = "__source_row"
LINEAGE_ID_COL = "__source_id"


def get_column_lists() -> tuple[list[str], list[str]]:
    """Config-driven column groups (single source of truth)."""
    cfg = load_config()
    numeric = cfg["data"].get("numeric_cols") or list(_DEFAULT_NUMERIC_COLS)
    categorical = cfg["data"].get("categorical_cols") or list(_DEFAULT_CATEGORICAL_COLS)
    return list(numeric), list(categorical)
```
Copy: `CKDRequest` fields derive from `config.yaml data.numeric_cols` /
`data.categorical_cols` — never a second hard-coded 24-field list drifting from
config. Import `LINEAGE_ROW_COL`/`LINEAGE_ID_COL` from `preprocess.py` for the
batch-CSV drop set; do not redefine the strings.

**Fallback-alias anti-pattern to avoid** (same file, lines 59-72): `_DEFAULT_*` +
deprecated `NUMERIC_COLS`/`CATEGORICAL_COLS` aliases exist only for backward
compat — new `api/` code calls `get_column_lists()`, never the aliases.

---

### `api/model_loader.py` (service, request-response at startup)

**Analog:** `src/evaluation/evaluate.py` — MlflowClient usage, run_id linkage, file-store gate

**File-store gate** (`src/evaluation/evaluate.py`, lines 29-31; identical in
`src/training/train.py:41-43`, `src/training/train_mlp.py:41-43`):
```python
# MLflow 3.x file store is maintenance-mode-gated: opt in explicitly since
# the locked architecture for this phase is the local mlruns/ file store.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
```
Copy verbatim at the top of `model_loader.py` (Pitfall 2: container process needs
this too — plus the Dockerfile/compose env var).

**Tracking-URI + client pattern** (`src/evaluation/evaluate.py`, lines 89-91):
```python
    cfg = load_config()
    mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))
    client = MlflowClient()
```
Copy: `load_config()` → `PROJECT_ROOT / cfg[...]` → `MlflowClient()`. New `api.*`
config section follows the same shape (env-overridable tracking URI for Pitfall 3).

**run_id linkage pattern** (`src/evaluation/evaluate.py`, lines 54-65):
```python
def resolve_winner_version(versions: list, winner_run_id: str):
    """Map the winning run to its registered version via run_id linkage. ..."""
    for v in versions:
        if v.run_id == winner_run_id:
            return v.version
    return max(v.version for v in versions)
```
Copy: `client.get_model_version("corvus-ckd", version).run_id` → download the
`preprocessing` artifact from that run. Never a latest-version heuristic
(DEPRECATED per RESEARCH State of the Art).

**Artifact-path constants** (`src/training/train.py`, lines 144-150):
```python
        mlflow.log_artifact(str(pipeline_path), artifact_path="preprocessing")
        mlflow.sklearn.log_model(
            estimator,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME,
            serialization_format="cloudpickle",  # pin: 3.x default is skops (Pitfall 3)
        )
```
Copy: artifact paths are verbatim `"preprocessing"` + `"model"`, model name verbatim
`"corvus-ckd"` (also `evaluate.py:33`), loader is `mlflow.sklearn.load_model` on the
`models:/corvus-ckd/<version>` URI (cloudpickle pin removes flavor ambiguity).

**Registered-name constant** (`src/evaluation/evaluate.py`, line 33;
`src/training/train.py:45`):
```python
REGISTERED_MODEL_NAME = "corvus-ckd"
```
Copy: one module-level constant, imported — never re-typed per call site.

---

### `scripts/promote_production.py` (script, batch one-shot)

**Analog:** `src/evaluation/evaluate.py` — `apply_registry_stages` + `main() -> int`

**Stage-transition pattern** (`src/evaluation/evaluate.py`, lines 68-84):
```python
def apply_registry_stages(client: MlflowClient, model_name: str, winner_version: str,
                          superseded_versions: list) -> None:
    """Winner to Staging, superseded to Archived. Never Production (D-06)."""
    # TECH DEBT (Pitfall 2): model-registry stages are deprecated since ...
    client.transition_model_version_stage(
        name=model_name,
        version=winner_version,
        stage="Staging",
        archive_existing_versions=True,
    )
    for version in superseded_versions:
        client.transition_model_version_stage(
            name=model_name, version=version, stage="Archived"
        )
```
Copy: same `client.transition_model_version_stage(...)` call shape for the D-01
v9 Staging→Production promotion (`stage="Production"`, `archive_existing_versions=True`).
Note the tech-debt comment convention (lines 71-74) — carry a matching comment.

**Result-print + exit-code pattern** (`src/evaluation/evaluate.py`, lines 127-139):
```python
def main() -> int:
    try:
        result = run_evaluation()
    except Exception as exc:
        print(f"EVALUATION ERROR: {exc}")
        return 1
    if result.success:
        print(f"WINNER {result.winner['run_name']} "
              f"roc_auc={result.winner['metrics']['roc_auc']:.4f} "
              f"version={result.version} stage={result.stage}")
        return 0
    print("EVALUATION FAILED — see log for details")
    return 1
```
Copy: `PROMOTION ERROR` / `PROMOTED corvus-ckd version=9 stage=Production` prints,
`-> int`, `sys.exit(main())`. Invoked as `python -m scripts.promote_production`
(mirrors `python -m src.evaluation.evaluate`, `evaluate.py:8`).

---

### `tests/test_api.py` (test, request-response)

**Analogs:** `tests/test_registry.py` (MagicMock client assertions) + `tests/conftest.py`
(isolation fixtures)

**Mock-client assertion pattern** (`tests/test_registry.py`, lines 21-30):
```python
def test_stage_transitions():
    client = MagicMock()
    eval_mod.apply_registry_stages(client, "corvus-ckd", "3", ["1", "2"])
    calls = {
        (c.kwargs["version"], c.kwargs["stage"]): c.kwargs
        for c in client.transition_model_version_stage.call_args_list
    }
    assert calls["3", "Staging"]["archive_existing_versions"] is True
```
Copy: `MagicMock()` SQLAlchemy session → assert `session.add` row shape carries all
24 fields + `prediction` + `probability` + `model_version`, assert single `commit`
(D-08 all-or-nothing: one commit after all rows, never per-row).

**Negative-assertion pattern** (`tests/test_registry.py`, lines 69-77):
```python
def test_no_production_transition():
    ...
    assert "Production" not in stages  # D-06: separate explicit step
```
Copy style: `assert <forbidden> not in <observed>` with the decision ID in a comment
(e.g. lineage cols not in served features; transformed-CSV reads not in loader paths —
see `test_training.py:56-72` spy pattern below).

**Read-spy pattern** (`tests/test_training.py`, lines 56-72):
```python
def test_loader_reads_raw_only(monkeypatch):
    import src.training.train as tm
    seen = []
    real_read_csv = pd.read_csv

    def spy(path, *a, **k):
        seen.append(str(path))
        return real_read_csv(path, *a, **k)

    monkeypatch.setattr(tm.pd, "read_csv", spy)
    tm.load_raw_splits()
    assert seen, "loader read no files"
    assert all(p.endswith("_raw.csv") for p in seen), seen
```
Copy: `monkeypatch.setattr` spy to prove the API never touches real `mlruns/` or real
Postgres in tests (with `tmp_mlflow_store` + mocked session).

**Isolation-fixture pattern** (`tests/conftest.py`, lines 15-37):
```python
@pytest.fixture
def synthetic_ckd_df():
    n = 40
    data = {col: [float(i % 5) for i in range(n)] for col in NUMERIC_COLS}
    ...
    df.loc[0, NUMERIC_COLS[0]] = None   # null numeric → imputer path
    df.loc[1, CATEGORICAL_COLS[0]] = None
    return df


@pytest.fixture
def tmp_mlflow_store(tmp_path, monkeypatch):
    """Point the MLflow tracking URI at tmp_path (never real mlruns/)."""
    uri = str(tmp_path / "mlruns")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    mlflow.set_tracking_uri(uri)
    yield uri
    mlflow.set_tracking_uri(uri)
```
Copy: new `synthetic_ckd_request` dict fixture extends this file (24 fields, one
`None` numeric, valid Literal categoricals — per RESEARCH Wave 0 gaps). `TestClient`
MUST use `with TestClient(app) as client:` or lifespan never runs (RESEARCH
Pattern 1). `test_raw.csv` rows minus lineage/target are the realistic fixture
source (CONTEXT Canonical References).

---

### `config/config.yaml` (modify: + `api.*` / `db.*`)

**Analog:** itself — section-per-concern shape (lines 31-37):
```yaml
logging:
  level: "INFO"
  log_dir: "logs"

mlflow:
  tracking_uri: "mlruns"
  experiment_name: "corvus-ckd"
```
Copy: append `api:` (model name, pinned version, tracking URI env override) and
`db:` (`DATABASE_URL`, unset default) sections in the same flat style. Extend
`load_config()` — never a second config mechanism (CONTEXT Reusable Assets).

---

### `requirements.txt` (modify: + 3 packages, fix label)

**Analog:** itself — phase-labeled sections (lines 23-26, 35):
```
# --- API (Phase 4) ---
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.6
...
# streamlit>=1.32         # Phase 4/9: frontend
```
Copy: fix the `Phase 4` mislabel to Phase 3 while touching it (RESEARCH §Installation),
append `psycopg2-binary`, `streamlit>=1.32`, `python-multipart` in the same
`pkg>=ver` + `# Phase N: purpose` style. Install command:
`.\venv\python.exe -m pip install "psycopg2-binary" "streamlit>=1.32" "python-multipart"` —
each gated by `checkpoint:human-verify` (all three flagged SUS in RESEARCH Package
Legitimacy Audit; seam-metadata gaps, not adverse signals).

---

### `tests/conftest.py` (modify: + `synthetic_ckd_request`)

**Analog:** itself — see `tests/test_api.py` section above (`synthetic_ckd_df` lines
15-27). New fixture mirrors that builder but emits a single 24-field request dict
(one `None` numeric for the D-05 imputer path, valid Literal categoricals from the
RESEARCH §Code Examples table — vocabularies verified over the 400-row raw source,
never the 81-row test split).

## Shared Patterns

### Logging
**Source:** `src/utils/logger.py` (lines 1-27)
**Apply to:** every new `api/*.py`, `scripts/promote_production.py`
```python
from src.utils.logger import get_logger

log = get_logger()
```
Module-level `log`, configured once via `config.yaml logging.*`. Never `print` except
in `main()` result lines; never log `DATABASE_URL`.

### Config access
**Source:** `src/utils/config.py` (lines 17-27)
**Apply to:** `api/app.py`, `api/model_loader.py`, `api/db.py`
```python
def load_config(path: Path = CONFIG_PATH) -> dict:
    """Return a fresh, caller-owned copy with data paths resolved to absolute. ..."""
    cfg = deepcopy(_read_config_file(str(path)))
```
Caller-owned deepcopy — mutate freely, never poison other callers. `load_config.cache_clear()`
(line 31) stays working for tests that reset config state.

### Fail-closed gates
**Source:** `src/validation/validate.py` (`run_raw_validation` lines 86-123, `main` 126-140);
`src/preprocessing/preprocess.py:284-288` (`raise SystemExit` on gate failure);
`src/ingestion/load_data.py:73-77` (same gate in standalone runs)
**Apply to:** `/predict` + `/batch_predict` handlers, lifespan startup
Pydantic rejects before inference (422); batch validates ALL rows first, 422 with the
first offending row number, single commit after (D-08); startup asserts
`pipeline.transform(one_row).shape[1] == estimator.n_features_in_` before serving
(RESEARCH Pitfall 1); `DATABASE_URL` unset → planner's chosen loud branch (suggested
fail-closed 503, RESEARCH Open Question 1) — never silent no-log serving, never SQLite.

### MLflow registry access
**Source:** `src/evaluation/evaluate.py` (lines 29-33, 89-91, 94-96, 111)
**Apply to:** `scripts/promote_production.py`, `api/model_loader.py`
```python
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
cfg = load_config()
mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))
client = MlflowClient()
mlflow_runs = client.search_runs(
    [experiment.experiment_id], filter_string="status = 'FINISHED'"
)
```
Plus `search_model_versions(f"name='{model_name}'")` (line 111) for version listing.
Stages are exact strings `"Staging"` / `"Archived"` / `"Production"`
(`test_registry.py:77` pins this).

### Test isolation
**Source:** `tests/conftest.py` + `tests/test_registry.py:33-54` (tmp-store 9-version test)
**Apply to:** `tests/test_api.py`, `tests/conftest.py`
Synthetic fixtures + `tmp_path` + `monkeypatch` + mocked DB session; never real
`data/`, real `mlruns/`, or real Postgres. Per-task: `pytest tests/test_api.py -x -q`;
per-wave: full `pytest tests/ -q`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `api/db.py` | store/model | CRUD | No SQLAlchemy in repo — planner uses RESEARCH §Code Examples "Prediction logging" (`DeclarativeBase` + `with Session(engine)`) verbatim |
| `docker/Dockerfile` | config | file-I/O | No Docker files in repo — planner uses RESEARCH §Code Examples Dockerfile (`python:3.11-slim`, venv is 3.11.0) |
| `docker/docker-compose.yml` | config | file-I/O | No compose files in repo — planner uses RESEARCH §Code Examples compose (`pg_isready` + `service_healthy`) |
| `frontend/app.py` | component | request-response | No Streamlit client in repo — planner uses RESEARCH Assumption A2 (`st.form` + httpx POST, `API_URL` env, localhost default) |

## Metadata

**Analog search scope:** `src/**/*.py`, `tests/**/*.py`, `config/config.yaml`, `requirements.txt`
(tracked files only, verified via `git ls-files`); `api/`, `docker/`, `frontend/`
confirmed untracked/empty — no analogs emitted from them.
**Files scanned:** 18 (13 src + 7 tests + config + requirements, minus `__init__.py` shims)
**Pattern extraction date:** 2026-09-23
