# Phase 2: Model Training + Experiment Tracking - Research

**Researched:** 2026-09-21
**Domain:** scikit-learn classification training + MLflow tracking/registry (file-store)
**Confidence:** HIGH (core APIs verified against the installed venv this session; registry deprecation cross-checked with official MLflow docs)

## Summary

Phase 2 trains 9 model configs on the 279-row training split and tracks everything in MLflow. The single most important constraint is the **Claim 2 contract from Phase 1**: training MUST consume `data/processed/{train,val,test}_raw.csv` through `preprocessing_pipeline.joblib` as the input step (re-fit the pipeline on train-raw only, transform val/test), and each MLflow run MUST log `preprocessing_pipeline.joblib` + the model as artifacts in the **same run** (FR-2.3 acceptance: run has both artifacts). Never train on the transformed `train/val/test.csv` files — they are audit outputs.

The environment is fully provisioned: venv has sklearn 1.9.1, mlflow 3.16.1, xgboost 3.2.0, lightgbm 4.7.0 — so **no new packages are needed** and no `pip install` step belongs in the plan. Two version-driven gotchas dominate planning: (1) installed MLflow is **3.16.1** while `requirements.txt` says `>=2.10` — model-registry **stages are deprecated since MLflow 2.9** (still functional in 3.16.1, which FR-3.1 mandates, but the deprecation must be recorded); (2) `mlflow.sklearn.log_model` in 3.x defaults to `serialization_format='skops'`, so the plan must pin the serialization format explicitly and verify the load path. All 9 estimators expose `predict_proba`, so ROC-AUC-based winner selection is uniform.

**Primary recommendation:** Implement `src/training/train.py` (6 classical configs) + `src/training/train_mlp.py` (3 MLP activations) sharing one `run_experiment()` helper shape, log params/metrics/pipeline+model per run to experiment `corvus-ckd`, compute all 5 metrics in `src/evaluation/evaluate.py`, rank strictly by test ROC-AUC, register every version and transition winner→Staging / superseded→Archived via `MlflowClient.transition_model_version_stage` (still present in 3.16.1).

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Train the full slate: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM, plus MLP with Sigmoid / Tanh / ReLU as three separate runs (9 configs total).
- **D-02:** Hyperparameters are library defaults with fixed seeds (`random_state=42` family) plus one documented rationale per choice. No grid search — at n=279, grids mostly fit noise.
- **D-03:** Winner = highest test-split ROC-AUC, strict ranking, no tie-break logic. Exactly as FR-2.4 scopes.
- **D-04:** Single small hidden layer (e.g. 50 units); the three runs differ only in activation. Right-sized for 279 rows so runs stay comparable.
- **D-05:** Fixed `max_iter` budget with seeded runs; no early stopping (the 40-row val split is too noisy a stopping signal, and it avoids val-set peeking).
- **D-06:** Every training run registers its model as a new version; the winner is registered to **Staging**. Promotion to Production is a separate explicit step (supports the FR-3.3 promote/demote story and gives a human approval gate).
- **D-07:** Superseded versions move to Archived as new winners arrive (FR-9.4 retention habit starts here).

### the agent's Discretion
None — the user decided every area directly. Planner has flexibility only on code organization (module split between `train.py` / `train_mlp.py` / `evaluate.py`), MLflow run naming, and test design.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FR-2.1 | Train LR, RF, XGBoost, LightGBM, MLP (Sigmoid/Tanh/ReLU as separate runs) — plus per D-01 Decision Tree + Gradient Boosting | Standard Stack (all estimators verified installed); activation map `logistic/tanh/relu` verified in sklearn 1.9.1 |
| FR-2.2 | Log accuracy, precision, recall, F1, ROC-AUC per run | `sklearn.metrics` imports verified; all 9 configs expose `predict_proba` (verified) |
| FR-2.3 | Log `preprocessing_pipeline.joblib` + model in the same MLflow run (Claim 2) | `mlflow.log_artifact` + `mlflow.sklearn.log_model` pattern; acceptance = both artifacts in one run |
| FR-2.4 | Compare all models; best by ROC-AUC | Strict `max(roc_auc)` ranking, no tie-break (D-03) |
| FR-2.5 | Register best model to MLflow Registry | `registered_model_name` in `log_model` or `mlflow.register_model`; versions auto-increment |
| FR-3.1 | Registry with Staging / Production / Archived stages | `transition_model_version_stage` verified present in 3.16.1; stages deprecated-but-functional (CITED docs) |
| FR-3.2 | Version tracking for all registered models | Every run registers → new version per run (D-06) |
| FR-3.3 | Promote/demote between stages | `transition_model_version_stage(..., stage="Staging"/"Archived"/"Production"/"None")`; Production promotion stays a separate explicit step (D-06) |

## Project Constraints (from AGENTS.md)

No `AGENTS.md` file exists in the project root (verified: only `.planning/codebase/CONVENTIONS.md`, `STACK.md`, `TESTING.md` were provided as project instructions). The operative conventions, carried into this research throughout, are:
- Config-driven everything via `src/utils/config.py:load_config()` (caller-owned deepcopy); no hardcoded paths/ratios/strategies in module bodies.
- Module-level `log = get_logger()` (Loguru, stderr + rotating file); never stdlib `logging`.
- `def main()` + `if __name__ == "__main__"` entry points, invoked as `python -m src.training.train` (venv: `.\venv\python.exe -m ...`).
- Immutable DataFrame inputs (`df.copy()`); `log.warning()` (not crash) on unexpected columns.
- pytest with synthetic CKD-shaped fixtures + `tmp_path` isolation; never touch real data files in tests.
- Python 3.11+, PEP 604/585 type hints; absolute internal imports (`from src.utils.config import ...`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Feature transformation (impute/scale/encode) | Preprocessing pipeline artifact | — | Phase 1 fitted `Pipeline` is the single input step; training never re-implements transforms (Claim 2) |
| Model fitting + metric computation | `src/training/` + `src/evaluation/` | — | Pure sklearn code, driven by `config.yaml` column lists |
| Experiment tracking (params/metrics/artifacts) | MLflow Tracking (file store `mlruns/`) | — | FR-2.2/2.3; local file store, no server needed |
| Versioning + stage lifecycle | MLflow Model Registry | — | FR-3.1–3.3; every run registers, winner→Staging |
| Inference-time model resolution | Phase 3 API (out of scope) | Registry | Phase 2 only guarantees Staging holds the winner |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scikit-learn` [VERIFIED: venv introspection 2026-09-21] | 1.9.1 (installed; requirement `>=1.3`) | LR, DecisionTree, RF, GradientBoosting, MLPClassifier; `accuracy/precision/recall/f1/roc_auc` metrics; Pipeline/ColumnTransformer reuse | Canonical estimator + metrics API; Phase 1 pipeline object is sklearn-native so train-time reuse is exact |
| `mlflow` [VERIFIED: venv introspection 2026-09-21] | 3.16.1 (installed; requirement `>=2.10`) | `set_tracking_uri` / `set_experiment` / `start_run` / `log_param(s)` / `log_metric(s)` / `log_artifact` / `sklearn.log_model` / `MlflowClient.transition_model_version_stage` (all `hasattr`-verified this session) | Only tracker that also provides the FR-3.x Registry; file store needs no server |
| `xgboost` [VERIFIED: venv introspection 2026-09-21] | 3.2.0 (installed; requirement `>=2.0`) | `XGBClassifier` (sklearn-compatible; `random_state=42` kwarg verified accepted) | Required by FR-2.1; sklearn API keeps the per-run loop uniform |
| `lightgbm` [VERIFIED: venv introspection 2026-09-21] | 4.7.0 (installed; requirement `>=4.0`) | `LGBMClassifier(random_state=42, verbosity=-1)` (both kwargs verified accepted) | Required by FR-2.1; `verbosity=-1` silences the per-iteration warning spam at n=279 |
| `joblib` [VERIFIED: venv introspection 2026-09-21] | 1.6.0 (installed; requirement `>=1.3`) | `joblib.load(preprocessing_pipeline.joblib)` at train start; `mlflow.log_artifact` logs the same file per run | Pipeline artifact round-trips through the exact serializer Phase 1 used |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pandas` / `numpy` | installed (requirements `>=2.0` / `>=1.24`) | Read `*_raw.csv`, drop lineage cols, split X/y | Every training/eval module |
| `pyyaml` (via `load_config`) | installed (`>=6.0`) | Column lists, split config, `mlflow.tracking_uri` + `experiment_name` | All modules read config; never hardcode |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| MLflow file store | MLflow server / SQLite backend | Server adds ops cost with zero benefit at 9 runs; file store (`mlruns/`) is the documented default and Phase 3 reads the same Registry. Stay on file store. |
| Registry stages | Model aliases (`@champion`) | Aliases are the future direction, but FR-3.1 explicitly mandates Staging/Production/Archived stages and `transition_model_version_stage` still works in 3.16.1. Use stages; record alias migration as tech debt. |
| `mlflow.sklearn.log_model` per run | Manual pickle + `log_artifact` | Manual pickling loses the Registry link and flavor metadata; `log_model(registered_model_name=...)` creates the version in one call. Always use `log_model`. |

**Installation:** None. Every package Phase 2 needs is already installed in `./venv` (verified this session). The plan must NOT include a `pip install` step; fresh-checkout recovery is just `pip install -r requirements.txt`.

**Version verification:** Done via venv introspection (not the PyPI registry, since installed-version truth beats registry truth here): sklearn 1.9.1, mlflow 3.16.1, xgboost 3.2.0, lightgbm 4.7.0, joblib 1.6.0. Note the skew: `requirements.txt` floors (`sklearn>=1.3`, `mlflow>=2.10`) are far below installed versions — behavior must be validated against the *installed* versions, especially MLflow 3.x (stages deprecation, `skops` default serialization).

## Package Legitimacy Audit

> No external packages are installed by this phase — all dependencies are pre-installed in `./venv` (Phase 1 setup) and `requirements.txt` gains no new lines. The seam check below is reported honestly per protocol; its metadata is degraded (see note).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| scikit-learn | PyPI | — | unknown (seam returned null) | unknown (seam returned null) | SUS (seam: `too-new`, `unknown-downloads`, `no-repository`) | Approved — already installed, no install step; canonical package, sklearn docs cross-checked |
| xgboost | PyPI | — | unknown (seam returned null) | unknown (seam returned null) | SUS (seam: `unknown-downloads`, `no-repository`) | Approved — already installed, no install step |
| lightgbm | PyPI | — | unknown (seam returned null) | unknown (seam returned null) | SUS (seam: `unknown-downloads`, `no-repository`) | Approved — already installed, no install step |
| mlflow | PyPI | — | unknown (seam returned null) | unknown (seam returned null) | SUS (seam: `too-new`, `unknown-downloads`, `no-repository`) | Approved — already installed, no install step |
| joblib | PyPI | — | unknown (seam returned null) | `github.com/joblib/joblib` (seam-confirmed) | SUS (seam: `too-new`, `unknown-downloads`) | Approved — already installed, no install step |
| pandas / numpy | PyPI | — | unknown (seam returned null) | unknown (seam returned null) | SUS (seam: `too-new`, `unknown-downloads`, `no-repository`) | Approved — already installed, no install step |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious (SUS):** all seven above — but the flags are seam-metadata artifacts (`weeklyDownloads: null`, `repoUrl: null` even for packages that unambiguously have repos), and **no package is installed during this phase**, so per protocol the `checkpoint:human-verify` gate has nothing to gate. Planner: do NOT add install tasks; do NOT add verify checkpoints for these. If a future phase adds a genuinely new dependency, re-run the legitimacy gate for that package.

*No package in this phase was discovered via WebSearch/training data and left unverified — every import is already exercised in the venv.*

## Architecture Patterns

### System Architecture Diagram

```
data/processed/{train,val,test}_raw.csv ──┐
data/processed/preprocessing_pipeline.joblib ──┤ (joblib.load, fitted on train in Phase 1;
└─► train.py / train_mlp.py                       re-fit on train-raw only at train time)
        │  1. load raw splits via config paths
        │  2. drop [__source_row, __source_id, <target>] from X
        │  3. pipeline.fit(X_train) → transform X_train/X_val/X_test
        │  4. fit estimator (defaults + random_state=42 family)
        │  5. predict / predict_proba on val + test
        ▼
mlflow.start_run(run_name="<model>-<variant>") ──► log params + 5 metrics (test) +
                                                   log_artifact(pipeline.joblib) +
                                                   sklearn.log_model(model, registered_model_name)
        │
        ▼
evaluate.py ──► read 9 runs (MLFLOW_TRACKING via runs API or local mlruns) ──►
               rank strictly by test ROC-AUC ──► winner
        │
        ▼
MlflowClient ──► winner version → transition to "Staging"
                 superseded versions → transition to "Archived"
                 (Production transition = separate explicit step, D-06)
```

### Recommended Project Structure

```
src/
├── training/
│   ├── __init__.py      # exists (empty); add shared helpers here or _common.py, not re-exports
│   ├── train.py         # 6 classical configs + main(); per-run: load → transform → fit → log
│   └── train_mlp.py     # 3 MLP activation runs + main(); same run shape as train.py
├── evaluation/
│   ├── __init__.py      # exists (empty)
│   └── evaluate.py      # metrics computation + strict ROC-AUC ranking + registry transitions + main()
tests/
├── test_training.py     # NEW (Wave 0): config-driven estimator factory, metric sanity, lineage exclusion
├── test_evaluation.py   # NEW (Wave 0): strict-max ranking, artifact-presence assertions
└── conftest.py          # NEW (Wave 0): shared 40-row synthetic CKD fixture (see TESTING.md gap #5)
```

### Pattern 1: Uniform per-run training loop (Claim 2 shape)
**What:** Every one of the 9 runs executes the identical 5-step shape — load raw splits, re-fit a fresh pipeline on train-raw only, transform, fit estimator, log params + metrics + pipeline artifact + model in one `start_run` block. `train.py` and `train_mlp.py` differ only in the estimator factory.
**When to use:** All 9 configs. The uniformity is what makes FR-2.3 auditable (every run has both artifacts) and keeps `train_mlp.py` a thin variant rather than a second system.
**Example:**
```python
# Source: MLflow docs https://mlflow.org/docs/latest/ml/tracking + Phase 1 contract
import mlflow, mlflow.sklearn, joblib
from src.utils.config import load_config, PROJECT_ROOT

cfg = load_config()
mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))  # NOT raw "mlruns": load_config resolves only data.* paths [VERIFIED: src/utils/config.py:24-26]
mlflow.set_experiment(cfg["mlflow"]["experiment_name"])  # "corvus-ckd" [VERIFIED: config/config.yaml:35-37]

with mlflow.start_run(run_name="random-forest"):
    mlflow.log_params({"model": "RandomForestClassifier", "random_state": 42})
    # ... fit on pipeline-transformed X_train, predict X_test ...
    mlflow.log_metrics({"accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "roc_auc": auc})
    mlflow.log_artifact(str(pipeline_path), artifact_path="preprocessing")  # same run as model (FR-2.3)
    mlflow.sklearn.log_model(model, artifact_path="model",
                             registered_model_name="corvus-ckd-rf",
                             serialization_format="cloudpickle")  # pin format; 3.x default is skops (see Pitfall 3)
```

### Pattern 2: Register-every-version, transition-winner
**What:** Pass `registered_model_name` in each run's `log_model` (auto-creates versions 1..N), then a separate `evaluate.py` step moves the winner's version to `Staging` and demotes superseded versions to `Archived` via `MlflowClient().transition_model_version_stage(name, version, stage)` with `archive_existing_versions=True` on the winner transition.
**When to use:** Always — D-06/D-07 make registration + archival part of every training invocation, not a manual UI click.
**Example:**
```python
# Source: MLflow docs https://mlflow.org/docs/latest/ml/model-registry/workflow.md
from mlflow.tracking import MlflowClient
client = MlflowClient()
client.transition_model_version_stage(name="corvus-ckd-<family>", version=winner_version,
                                      stage="Staging", archive_existing_versions=True)
for v in superseded_versions:
    client.transition_model_version_stage(name="corvus-ckd-<family>", version=v, stage="Archived")
```

### Anti-Patterns to Avoid
- **Training on `train.csv` (transformed):** breaks the Claim 2 contract — the logged pipeline would not be the object that produced the features. Always start from `*_raw.csv`. [VERIFIED: src/preprocessing/preprocess.py:18-23]
- **One mega-script for all 9 configs:** CONTEXT.md locks the `train.py` / `train_mlp.py` / `evaluate.py` split as planner flexibility — keep MLP separate (different input handling: scaling sensitivity, convergence warnings) with a shared helper shape, not a shared god-function.
- **Manual Registry clicks / UI promotion:** D-06/D-07 require registration + Staging + archival to be code in `evaluate.py`, reproducible on every run.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Experiment tracking (params/metrics/artifacts) | Custom CSV/JSON run logger | `mlflow` tracking (file store) | Lineage (run→model version), UI, and Registry linkage come free; FR-2.3 acceptance is defined in MLflow terms |
| Classification metrics | Manual TP/FP counting | `sklearn.metrics.{accuracy,precision,recall,f1,roc_auc}_score` (imports verified) | `zero_division` handling, averaging modes, and proba-vs-label edge cases already settled |
| Model versioning + stage lifecycle | `models/` folder with `v1/`, `v2/` dirs | MLflow Registry (`registered_model_name` + `transition_model_version_stage`) | FR-3.2/3.3 acceptance is Registry-native; folder versioning cannot do promote/demote semantics Phase 3 will query |
| preprocessing reuse | Re-fit imputers/scaler inline in training | `joblib.load(preprocessing_pipeline.joblib)` + re-`fit` on train-raw | Claim 2 requires the *single Pipeline object*; inline re-fitting forks the transform and voids the audit trail [VERIFIED: src/preprocessing/preprocess.py:13-16] |
| Hyperparameter search | Grid/random search over 9 configs | Library defaults + `random_state=42` + one documented rationale each (D-02) | At n=279 train rows, grids fit noise; decision is locked — planner must not add search tasks |

**Key insight:** This phase is a *wiring* phase, not an *invention* phase — sklearn estimators, MLflow tracking, and the Phase 1 pipeline already exist. Every custom-built substitute (hand logger, folder versioning, manual metrics) duplicates a tested tool while voiding a patent-claim acceptance test.

## Common Pitfalls

### Pitfall 1: Training from transformed CSVs instead of raw + pipeline
**What goes wrong:** FR-2.3 acceptance fails — the logged `preprocessing_pipeline.joblib` is not the object that produced the training features, voiding Claim 2.
**Why it happens:** `train.csv` looks like the convenient input (already numeric, no pipeline needed).
**How to avoid:** Training inputs are `train_raw.csv` / `val_raw.csv` / `test_raw.csv` ONLY [VERIFIED: data shapes (279/40/81 × 27) read this session]; re-fit pipeline on train-raw, transform the rest. Add a test asserting the training loader never reads `train.csv`/`val.csv`/`test.csv`.
**Warning signs:** Any training code path referencing `processed_dir / "train.csv"` (non-`raw`).

### Pitfall 2: Registry stages deprecated in installed MLflow 3.16.1
**What goes wrong:** Future MLflow major removes `transition_model_version_stage`; code built only on stages breaks on upgrade. [CITED: https://mlflow.org/docs/latest/ml/model-registry/workflow.md — "Model Stages are deprecated and will be removed in a future major release", deprecated since 2.9.0]
**Why it happens:** `requirements.txt` says `mlflow>=2.10` but venv has 3.16.1 — training-data-era examples assume stages are the blessed path.
**How to avoid:** FR-3.1 mandates stages, and the API is verified present and functional in 3.16.1 — use stages now, and log an explicit tech-debt note (alias migration: `set_registered_model_alias`) for a later phase. Do NOT adopt aliases now: that would contradict FR-3.1 acceptance language.
**Warning signs:** `mlflow` upgrade PRs; deprecation warnings in client logs.

### Pitfall 3: `log_model` default serialization changed to `skops` in MLflow 3.x
**What goes wrong:** Model saved with `skops` cannot be loaded with the `pickle/cloudpickle` path Phase 3 assumes (or vice versa); `mlflow.pyfunc.load_model("models:/.../Staging")` fails at serve time.
**Why it happens:** Installed `mlflow.sklearn.log_model` signature shows `serialization_format='skops'` as the default [VERIFIED: venv signature introspection this session] — MLflow 2.x-era examples assume pickle.
**How to avoid:** Pin `serialization_format` explicitly in every `log_model` call AND add a test that round-trips `load_model` from the logged artifact. Record the chosen format in RESEARCH/PLAN so Phase 3 loads with the matching flavor.
**Warning signs:** `load_model` raising deserialization errors; `MLmodel` file listing `skops` vs `pickle` mismatch.

### Pitfall 4: Lineage columns leak into features
**What goes wrong:** `__source_row` (int index label) becomes a spurious predictive feature; `__source_id` (raw id) memorizes rows — both inflate metrics and break inference (these columns don't exist at predict time).
**Why it happens:** `*_raw.csv` files carry lineage inline next to features [VERIFIED: src/preprocessing/preprocess.py:248-249, 257-273].
**How to avoid:** Drop `[LINEAGE_ROW_COL, LINEAGE_ID_COL, target_column]` from X immediately after load — import the constants from `preprocess.py` (`LINEAGE_ROW_COL = "__source_row"`, `LINEAGE_ID_COL = "__source_id"` [VERIFIED: src/preprocessing/preprocess.py:74-75]) rather than re-typing the strings. Test: assert trained feature count == 24 (14 numeric + 10 categorical).
**Warning signs:** Feature count ≠ 24; feature-importance plots topped by `__source_row`.

### Pitfall 5: Booster seed + verbosity API drift (XGBoost 3.x / LightGBM 4.x)
**What goes wrong:** `XGBClassifier(seed=...)` vs `random_state=...` confusion; LightGBM floods logs with per-iteration warnings (or crashes on removed `verbose` param).
**Why it happens:** `XGBClassifier.__init__` signature is `(self, objective, kwargs)` — seed params hide in `**kwargs` [VERIFIED: venv introspection]; `LGBMClassifier` has NO `verbose` param, only `**kwargs`-passed `verbosity` [VERIFIED: venv introspection].
**How to avoid:** `XGBClassifier(random_state=42)` (verified accepted this session) and `LGBMClassifier(random_state=42, verbosity=-1)` (verified accepted this session). Never pass `verbose=` to LGBMClassifier.
**Warning signs:** `TypeError` on booster construction; hundreds of `[LightGBM] [Warning]` lines per run.

### Pitfall 6: MLP activation names + oversized defaults
**What goes wrong:** `activation="sigmoid"` raises (valid values are `identity/logistic/tanh/relu` [VERIFIED: sklearn 1.9.1 `ACTIVATIONS` keys]); default `hidden_layer_sizes=(100,)` + `max_iter=200` [VERIFIED: venv defaults] overfits/mis-converges at n=279 and breaks run comparability.
**Why it happens:** "Sigmoid" is the textbook name; sklearn calls it `logistic`.
**How to avoid:** Activation map Sigmoid→`logistic`, Tanh→`tanh`, ReLU→`relu`; set `hidden_layer_sizes=(50,)` (D-04), explicit `max_iter` + `random_state=42` (D-02/D-05). Expect `ConvergenceWarning` at fixed budget — suppress-or-log deliberately, never silently ignore (a warning-not-crash policy per CONVENTIONS.md).
**Warning signs:** `ValueError: activation ... not supported`; wildly different MLP scores caused by hidden-size/max_iter drift between the three runs.

### Pitfall 7: Relative `tracking_uri` resolves against CWD, not project root
**What goes wrong:** Running training from any directory other than project root scatters `mlruns/` across the filesystem; runs "disappear".
**Why it happens:** `config.yaml` sets `mlflow.tracking_uri: "mlruns"` (relative) [VERIFIED: config/config.yaml:35-37], and `load_config()` resolves ONLY `data.raw_path/processed_dir/validation_dir` to absolute — it does NOT touch `mlflow.tracking_uri` [VERIFIED: src/utils/config.py:23-27].
**How to avoid:** `mlflow.set_tracking_uri(str(PROJECT_ROOT / cfg["mlflow"]["tracking_uri"]))` at the top of every entry point (pattern in Code Examples). Invoke only via `.\venv\python.exe -m src.training.train` from root.
**Warning signs:** Multiple `mlruns/` directories; empty MLflow UI at the expected path.

### Pitfall 8: ROC-AUC on labels instead of probabilities
**What goes wrong:** `roc_auc_score(y_test, y_pred_labels)` computes a degenerate AUC (single-threshold point), corrupting the D-03 winner ranking.
**Why it happens:** Copy-paste across the 5 metric calls; labels and probas are adjacent variables.
**How to avoid:** `roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])` — all 9 estimators expose `predict_proba` [VERIFIED: venv `hasattr` check this session]. Test with a synthetic perfectly-separated fixture asserting AUC == 1.0.
**Warning signs:** All ROC-AUC values suspiciously close to accuracy; ranking disagrees with eyeball separation.

## Code Examples

Verified patterns (signatures/APIs confirmed against the installed venv this session; registry prose cross-checked with official docs):

### Metric computation (all 5, FR-2.2)
```python
# Source: sklearn.metrics (imports verified in venv: sklearn 1.9.1)
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]  # all 9 configs expose predict_proba (verified)
metrics = {
    "accuracy": accuracy_score(y_test, y_pred),
    "precision": precision_score(y_test, y_pred, zero_division=0),
    "recall": recall_score(y_test, y_pred, zero_division=0),
    "f1": f1_score(y_test, y_pred, zero_division=0),
    "roc_auc": roc_auc_score(y_test, y_proba),  # probas, NOT labels (Pitfall 8)
}
mlflow.log_metrics(metrics)  # `log_metrics` hasattr-verified on installed mlflow 3.16.1
```

### Classical estimator factory (defaults + seeds, D-02)
```python
# Source: sklearn + xgboost + lightgbm (kwargs verified in venv this session)
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

ESTIMATORS = {
    "logistic-regression": LogisticRegression(random_state=42),          # default max_iter=100; raise if ConvergenceWarning
    "decision-tree": DecisionTreeClassifier(random_state=42),
    "random-forest": RandomForestClassifier(random_state=42),            # default n_estimators=100 (verified)
    "gradient-boosting": GradientBoostingClassifier(random_state=42),
    "xgboost": XGBClassifier(random_state=42),                           # **kwargs seed (verified)
    "lightgbm": LGBMClassifier(random_state=42, verbosity=-1),           # NO `verbose` param in 4.7.0 (verified)
}
```

### MLP runs (three activations, D-04/D-05)
```python
# Source: sklearn.neural_network (ACTIVATIONS keys + defaults verified in venv: sklearn 1.9.1)
from sklearn.neural_network import MLPClassifier

ACTIVATIONS = {"sigmoid": "logistic", "tanh": "tanh", "relu": "relu"}  # "sigmoid" is NOT a valid value
model = MLPClassifier(hidden_layer_sizes=(50,), activation=ACTIVATIONS["sigmoid"],
                      max_iter=500, random_state=42)  # fixed budget, seeded, no early stopping (D-05)
```

### Winner selection + registry transitions (D-03/D-06/D-07)
```python
# Source: https://mlflow.org/docs/latest/ml/model-registry/workflow.md (stages API; deprecation noted in Pitfall 2)
from mlflow.tracking import MlflowClient
client = MlflowClient()
winner = max(runs, key=lambda r: r["metrics"]["roc_auc"])  # strict ranking, no tie-break (D-03)
client.transition_model_version_stage(name=winner["model_name"], version=winner["version"],
                                      stage="Staging", archive_existing_versions=True)  # winner → Staging (D-06)
for v in superseded_versions:  # everything else → Archived (D-07)
    client.transition_model_version_stage(name=model_name, version=v, stage="Archived")
# Production promotion is a SEPARATE explicit step (D-06) — evaluate.py must NOT transition to Production.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Registry stages (Staging/Production/Archived) as the blessed lifecycle | Stages deprecated → model aliases (`models:/name@champion`) + tags | Deprecated MLflow 2.9.0; still functional in installed 3.16.1 [CITED: https://mlflow.org/docs/latest/ml/model-registry/workflow.md] | Phase 2 uses stages per FR-3.1; record alias migration as tech debt, don't preempt it |
| `log_model` pickle/cloudpickle default | `serialization_format='skops'` default in MLflow 3.x `mlflow.sklearn` | MLflow 3.x [VERIFIED: installed 3.16.1 signature] | Pin the format explicitly; verify the load round-trip (Pitfall 3) |
| Grid search as default tuning posture | Defaults + seeds at small-n (n=279) | Locked by D-02 | No search tasks in the plan, period |

**Deprecated/outdated:**
- `mlflow.sklearn.log_model(..., artifact_path="model")` without `serialization_format` — works but leaves format to the 3.x default; pin it.
- `LGBMClassifier(verbose=...)` — no such param in LightGBM 4.7.0; use `verbosity=-1`.
- `MLPClassifier(activation="sigmoid")` — never existed; use `"logistic"`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 9 run names / registered-model names are planner's choice (no user lock) | Architecture Patterns | Low — naming only; planner picks convention, tests assert on config not names |
| A2 | `evaluate.py` reads metrics from MLflow runs API (vs. CSV predictions) — CONTEXT.md allows either ("from MLflow runs or CSV predictions") | Architecture Patterns | Low — planner decides; either satisfies FR-2.4 as long as ranking is strict ROC-AUC |
| A3 | `archive_existing_versions=True` on winner transition correctly archives prior Staging versions without touching Archived history | Code Examples | Medium — if semantics differ, D-07 archival needs an explicit loop; executor must verify against MLflow docs before relying on the flag |
| A4 | Default `max_iter=100` for LogisticRegression converges on scaled CKD features; raising only if ConvergenceWarning appears | Code Examples | Low — warning-driven bump is a 1-line change with a seeded rerun |
| A5 | File-store Registry supports `transition_model_version_stage` + `models:/` URIs identically to server mode at this scale | Standard Stack | Low — file store is the documented default; Phase 3 dependency flagged if it diverges |

## Open Questions

1. **Registered model naming: one name per estimator family vs. one name for all?**
   - What we know: D-06 requires every run to register a new version; Registry auto-increments versions per registered-model name. Either `corvus-ckd` (9 versions, winner picked by version) or `corvus-ckd-{rf,xgb,...}` (per-family versions) satisfies FR-3.2.
   - What's unclear: Which shape Phase 3 prefers for Production resolution (single name is simpler for `models:/corvus-ckd/Staging`).
   - Recommendation: Planner picks single-name `corvus-ckd` (simplest Phase 3 URI) unless a reason against emerges; record the choice in PLAN.md.

2. **Does `evaluate.py` re-run inference or read logged metrics?**
   - What we know: CONTEXT.md permits both ("from MLflow runs or CSV predictions").
   - What's unclear: Re-running inference duplicates train.py logic; reading runs couples evaluate to tracking state.
   - Recommendation: Read logged test metrics via `MlflowClient.search_runs` (no re-fit, single source of truth), with a CSV-predictions fallback only if runs are missing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `.\venv\python.exe` (+ sklearn, mlflow, xgboost, lightgbm, joblib, pandas) | All training/eval code | ✓ (verified this session) | py3.11 / sklearn 1.9.1 / mlflow 3.16.1 / xgb 3.2.0 / lgbm 4.7.0 | — |
| `data/processed/{train,val,test}_raw.csv` + `preprocessing_pipeline.joblib` | Training inputs + Claim 2 artifact | ✓ (verified: 279/40/81 rows × 27 cols; 24 features + 2 lineage + target) | — | — |
| `mlruns/` tracking store | MLflow file store | ✓ (exists; auto-created on first `set_tracking_uri` run regardless) | — | — |
| `config/config.yaml` `mlflow.*` keys | Experiment name + tracking URI | ✓ (`tracking_uri: "mlruns"`, `experiment_name: "corvus-ckd"` [VERIFIED: config/config.yaml:35-37]) | — | — |
| Network / GPU / MLflow server | Nothing in this phase | n/a | — | n/a — file store, CPU-only at n=279 |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — proceed with local venv + file store.

## Validation Architecture

`workflow.nyquist_validation` is absent from `.planning/config.json` → validation section required. Framework is pytest (no config file — default discovery; run from root with `.\venv\python.exe -m pytest tests/ -v`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥ 8.0 (installed in venv) |
| Config file | none — see Wave 0 (`tests/conftest.py` for shared fixtures) |
| Quick run command | `.\venv\python.exe -m pytest tests/test_training.py tests/test_evaluation.py -q` |
| Full suite command | `.\venv\python.exe -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FR-2.1 | All 9 estimator configs construct with seeds; MLP activations ∈ {logistic,tanh,relu} | unit | `pytest tests/test_training.py::test_all_nine_configs_construct -q` | ❌ Wave 0 |
| FR-2.2 | All 5 metrics computed; ROC-AUC uses probas (synthetic separable fixture → AUC 1.0) | unit | `pytest tests/test_evaluation.py::test_roc_auc_uses_probas -q` | ❌ Wave 0 |
| FR-2.3 (Claim 2) | Each MLflow run contains both pipeline artifact + model artifact | integration (tmp tracking URI) | `pytest tests/test_training.py::test_run_logs_pipeline_and_model -q` | ❌ Wave 0 |
| FR-2.4 | Strict max-ROC-AUC ranking, no tie-break | unit (synthetic run table) | `pytest tests/test_evaluation.py::test_winner_is_strict_max_roc_auc -q` | ❌ Wave 0 |
| FR-2.5/3.2 | Every run registers a new version (mocked or tmp-store client) | integration | `pytest tests/test_evaluation.py::test_every_run_registers_version -q` | ❌ Wave 0 |
| FR-3.1/3.3 | Winner→Staging, superseded→Archived transitions issued (stage strings exact) | unit (mock MlflowClient) | `pytest tests/test_evaluation.py::test_stage_transitions -q` | ❌ Wave 0 |
| Claim 2 input | Training loader reads `*_raw.csv` only; feature count == 24 (lineage excluded) | unit | `pytest tests/test_training.py::test_lineage_excluded_feature_count_24 -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.\venv\python.exe -m pytest tests/test_training.py tests/test_evaluation.py -q`
- **Per wave merge:** `.\venv\python.exe -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — shared 40-row synthetic CKD fixture (extend TESTING.md pattern; never touch real `data/`)
- [ ] `tests/test_training.py` — estimator factory, lineage exclusion, MLflow run artifact presence (use tmp tracking URI via `tmp_path`, never real `mlruns/`)
- [ ] `tests/test_evaluation.py` — strict-max ranking, stage-transition calls (mock `MlflowClient`), proba-based AUC

## Security Domain

No auth/session/crypto surface in this phase (local file-store training, no network, no secrets). Applicable controls:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — local execution |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes | Drop `__source_row`/`__source_id`/target from X (Pitfall 4); `log.warning()` on unexpected columns per CONVENTIONS.md; never train on unvalidated schemas |
| V6 Cryptography | no | n/a — no secrets; MLflow file store holds metrics/models only |

### Known Threat Patterns for sklearn + MLflow file store

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary-code pickle via untrusted `joblib`/`pickle` model load | Tampering | Load pipeline/models only from our own `data/processed/` + `mlruns/`; pin `serialization_format` (Pitfall 3); never `joblib.load` a third-party file |
| Training-data exfiltration via logged artifacts | Information disclosure | `mlruns/` is gitignored local state; never commit it; lineage IDs stay in artifacts, not in metrics/tags |

## Sources

### Primary (HIGH confidence — tool-verified this session)
- venv introspection (`.\venv\python.exe`): sklearn 1.9.1 (`ACTIVATIONS` keys, MLP/RF defaults, metrics imports, `predict_proba` on all 9), mlflow 3.16.1 (tracking fns + `log_model` signature incl. `serialization_format='skops'` + registry client methods), xgboost 3.2.0 (`random_state` kwarg accepted), lightgbm 4.7.0 (no `verbose` param; `random_state` + `verbosity` accepted), joblib 1.6.0
- In-repo reads with line citations: `config/config.yaml:35-37` (mlflow keys), `:10-12` (column lists), `:19-23` (split), `src/utils/config.py:23-27` (path resolution scope), `src/preprocessing/preprocess.py:18-23` (Claim 2 contract), `:74-75` (lineage constants), `:172-206` (pipeline def), `:241-281` (save_outputs), `requirements.txt` (dependency floors)
- Data probe: `train/val/test_raw.csv` = 279/40/81 rows × 27 cols; target distribution {1: 174, 0: 105} on train

### Secondary (MEDIUM confidence — official docs cross-checked via WebSearch)
- https://mlflow.org/docs/latest/ml/model-registry/workflow.md — stage transitions, accepted stage values, stages-deprecated-since-2.9.0, alias migration path (seam: websearch --verified → MEDIUM)

### Tertiary (LOW confidence)
- gsd-tools `package-legitimacy` seam output — metadata degraded (null downloads/repos for canonical packages); recorded per protocol but not relied upon (all packages pre-installed)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every import, default, and kwarg verified against the installed venv this session
- Architecture: HIGH — module split follows locked CONTEXT.md decisions + existing `src/training/`, `src/evaluation/` scaffold (empty `__init__.py` files verified present)
- Pitfalls: HIGH for version-driven items (signature-level verification), MEDIUM for the stages-deprecation outlook (docs-cited, future-facing)

**Research date:** 2026-09-21
**Valid until:** 2026-10-21 (stable domain; re-verify only if venv packages or `requirements.txt` change)
