---
phase: 07-nhanes-native-retrain
reviewed: 2026-10-15T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - config/config.yaml
  - src/preprocessing/preprocess_nhanes.py
  - src/training/train_nhanes.py
  - src/training/harmonize_v9.py
  - src/evaluation/evaluate_nhanes.py
  - scripts/promote_challenger.py
  - api/schemas.py
  - api/model_loader.py
  - api/app.py
  - api/db.py
  - tests/conftest.py
  - tests/test_nhanes_training.py
  - tests/test_api_v2.py
findings:
  critical: 0
  warning: 12
  info: 9
  total: 21
status: issues-found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-10-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues-found

## Summary

Reviewed all 13 source files created/changed by Phase 7 commits (`a3a4efb` through `ff0b32e`:
tracer native pipeline + quarantine gate, 9-config sweep + CV/CIs, harmonization adapter +
paired comparison + promotion script, v2 schemas/loader/routes/log table + both test suites).
No hardcoded secrets, no injection surfaces (ORM-only logging, Pydantic-validated inputs),
and the quarantine gate direction (allow-list projection, fail-closed `SystemExit`) is sound.
However, the review found 12 warnings: two config keys that are dead or duplicated relative
to the code that must honor them, silent partial-schema training, a latent label-parsing
crash, v1 availability coupled to v2 startup success, an unguarded Production promotion
script, mutate-before-verify registry staging, a broad exception swallow in evaluation, an
ORM/request int-vs-String mismatch on `predictions_v2`, a read-before-check upload guard,
and a vacuous registry-guard test stub. Nine info items cover duplication, missing pins,
and brittle tests. No finding blocks the localhost academic deployment on its own, but
WR-02, WR-05, and WR-07 touch the phase's core safety controls (quarantine, coexistence,
human gate) and should be fixed before the production cutover flip.

## Warnings

### WR-01: Dead config knob `nhanes_cv_folds` — changing it has zero effect

**File:** `src/training/train_nhanes.py:161-167`
**Issue:** `config.yaml` defines `data.nhanes_cv_folds: 5`, but no code reads it.
`run_cv_native` hardcodes its default (`n_splits: int = 5`) and `sweep_native`
(`train_nhanes.py:221-236`) never passes a fold count through. An operator tuning
folds in config would silently get 5 folds forever. (Grep confirms `nhanes_cv_folds`
appears only in `config.yaml` and planning docs.)
**Fix:**
```python
def sweep_native(X_dev, y_dev, numeric_cols, categorical_cols, n_splits=None) -> dict:
    if n_splits is None:
        n_splits = int(load_config()["data"].get("nhanes_cv_folds", 5))
    results = {}
    for name in NATIVE_ESTIMATORS:
        cv = run_cv_native(name, X_dev, y_dev, numeric_cols, categorical_cols, n_splits=n_splits)
        ...
```

### WR-02: Quarantine list has two sources of truth with no equality pin

**File:** `src/preprocessing/preprocess_nhanes.py:29-43`
**Issue:** The safety-critical 11-column ban exists as hardcoded `QUARANTINE_11`
*and* as config `data.nhanes_quarantine_cols`, but `assert_quarantine` reads only
the constant — the config list is never read by any code (grep-verified). The two
lists match today, but a future edit to one without the other silently desynchronizes
the documented contract from the enforced gate, and no test asserts equality.
**Fix:**
```python
def assert_quarantine(df: pd.DataFrame) -> None:
    cfg = load_config()
    configured = set(cfg["data"].get("nhanes_quarantine_cols", []))
    assert configured == set(QUARANTINE_11), (
        f"Quarantine drift: config={sorted(configured)} constant={sorted(QUARANTINE_11)}"
    )
    ...
```
(or derive `QUARANTINE_11` from config at import and delete the duplication).

### WR-03: `load_native_frame` silently trains on a partial schema

**File:** `src/training/train_nhanes.py:133-135`
**Issue:** Config column lists are filtered to `df.columns` with no warning and no
abort when expected native columns are absent:
`numeric_cols = [c for c in numeric_cols if c in df.columns]`. If the derived CSV
drifts (renamed/dropped column), training proceeds on fewer features with only the
*unexpected*-columns warning (which covers extras, not missing). The quarantine
direction is correct (allow-list projection), but schema shrinkage should fail loud.
**Fix:**
```python
missing = (set(numeric_cols) | set(categorical_cols)) - set(df.columns)
if missing:
    raise SystemExit(f"NATIVE SCHEMA DRIFT — expected columns absent: {sorted(missing)}")
```

### WR-04: Label-parsing branch misroutes all-string (and NaN-bearing) labels into a crash

**File:** `src/training/train_nhanes.py:149-156`
**Issue:** The numeric-label detector is
`set(pd.to_numeric(y_raw, errors="coerce").dropna().unique()) <= {0, 1}`. For an
all-string label column, coercion yields all-NaN, `dropna()` yields the empty set,
and `set() <= {0, 1}` is `True` — so string labels take the *numeric* branch, where
`pd.to_numeric(y_raw)` (no `errors=` → raise) throws `ValueError`. Latent today
(real `ckd` is 0/1 numeric), but the string-label fallback path is dead code that
crashes if ever taken. Related: a numeric label column containing NaN passes the
subset check, then `.astype(int)` on NaN raises.
**Fix:**
```python
coerced = pd.to_numeric(y_raw, errors="coerce")
if coerced.notna().all() and set(coerced.unique()) <= {0, 1}:
    y = coerced.astype(int)
else:
    y = (y_raw.astype(str).str.strip().str.lower()
         == str(positive_label).strip().lower()).astype(int)
```

### WR-05: v2 load failure at startup takes down healthy v1 serving

**File:** `api/app.py:77-96`
**Issue:** `lifespan` calls `load_v2_artifacts(v2_version)` with no `try/except`.
Any v2 failure — bad pin, missing `preprocessing_pipeline_nhanes.joblib` artifact
(the exact failure already seen live in `ff0b32e`), unreachable registry — propagates
out of lifespan and the whole API never starts, including the untouched v1 routes.
This breaks the v1/v2 coexistence guarantee (D-05/D-06): a v2 misconfiguration is a
v1 outage.
**Fix:**
```python
v2_version = model_loader.resolve_v2_version()
if v2_version:
    try:
        v2_model, v2_pipeline, v2_run_id, v2_version = (
            model_loader.load_v2_artifacts(v2_version)
        )
        ...
    except Exception as exc:
        log.warning(f"v2 slot failed to load ({type(exc).__name__}: {exc}) — /v2 will 503, v1 serving on")
        app.state.v2_model_version = ""
        app.state.v2_model = None
        ...
```

### WR-06: `resolve_v2_version` treats null/whitespace pin as configured

**File:** `api/model_loader.py:133-143`
**Issue:** `str(cfg["api"].get("v2_pinned_version", ""))` maps a YAML null to the
truthy string `"None"`, and a whitespace string is likewise truthy — so lifespan
attempts `load_v2_artifacts("None")`, which raises and (via WR-05) kills startup
instead of taking the designed unconfigured-503 path.
**Fix:**
```python
def resolve_v2_version() -> str:
    override = os.environ.get("MODEL_VERSION_V2")
    if override and override.strip() and override.strip().lower() != "none":
        return override.strip()
    cfg = load_config()
    raw = cfg["api"].get("v2_pinned_version", "") or ""
    return str(raw).strip() if str(raw).strip().lower() != "none" else ""
```

### WR-07: Promotion script enforces none of the human-gate protocol

**File:** `scripts/promote_challenger.py:38-68`
**Issue:** D-04's entire Production safety ("no auto-promote, ever", promote only the
qualified challenger) is procedural — the script accepts *any* `--version` with no
check that the version is in Staging, no check that `compare_challenger` qualified
it, and no confirmation prompt. A typo (`--version 10` for `11`) promotes the
superseded tracer to Production while `archive_existing_versions=True` demotes the
real winner. `MLFLOW_TRACKING_URI` env override additionally lets it act on a
different tracking store than the local `mlruns/`.
**Fix:**
```python
details = client.get_model_version(REGISTERED_MODEL_NAME, str(args.version))
assert details.current_stage == "Staging", f"refusing: version {args.version} is {details.current_stage}, not Staging"
answer = input(f"Promote {REGISTERED_MODEL_NAME} v{args.version} to Production, archiving current Production? [yes/NO] ")
if answer.strip().lower() != "yes":
    print("ABORTED — registry untouched"); return 1
```

### WR-08: `apply_challenger_stages` mutates the registry before verifying the guard

**File:** `src/evaluation/evaluate_nhanes.py:107-129`
**Issue:** The winner→Staging transition (with `archive_existing_versions=True`)
executes at lines 115-120, and the Production-integrity check (`before/after ==
"Production"`) runs only at lines 125-129 with no rollback. A guard trip raises
*after* the mutation has landed. Benign under current MLflow semantics (archiving
applies to the target stage, verified live), but verify-after-mutate is the wrong
shape for a safety guard.
**Fix:** perform the `before` read, run all transitions, and on guard failure
attempt compensating transitions back (or at minimum re-read and report the full
post-state); better, query which versions occupy Staging *before* transitioning.

### WR-09: `run_evaluation` swallows guard trips and bugs into one generic warning

**File:** `src/evaluation/evaluate_nhanes.py:200-202`
**Issue:** Bare `except Exception` converts everything — including WR-08's
`RuntimeError("Production guard tripped")` and the staging `ValueError` — into
`log.warning(...)` + `success=False`. A tripped Production guard is
indistinguishable from a transient artifact-download failure in logs and exit
status, delaying investigation of the most serious failure this module can produce.
**Fix:**
```python
except (RuntimeError, ValueError) as exc:
    log.error(f"Native evaluation SAFETY FAILURE: {type(exc).__name__}: {exc}")
    raise
except Exception as exc:
    log.warning(f"Native evaluation failed: {type(exc).__name__}: {exc}")
    return SimpleNamespace(success=False, winner=None)
```

### WR-10: `PredictionLogV2` declares categoricals `String(16)` but is fed int codes

**File:** `api/db.py:105-109` and `api/app.py:277-297`
**Issue:** Request validation keeps NHANES codes as ints (`Literal[1, 2]` etc. in
`api/schemas.py:86-90`), and `_log_predictions_v2` passes them straight through
(`**row`) into `String(16)` columns. Works on Postgres/SQLite via implicit
assignment casts (already noted as a watch item in 07-03-SUMMARY), but the ORM
contract and the writer contract disagree at the module boundary, and a strict
store rejects the INSERT — losing the Claim-4 audit row for a successful prediction.
**Fix:** stringify at the boundary —
`{k: (str(v) if k in COLUMN_ORDER_V2[16:] and v is not None else v) ...}` in
`_log_predictions_v2` — or change the five columns to `Integer`.

### WR-11: Batch 413 guards run after the full upload is already in memory

**File:** `api/app.py:326-336` (v2; v1 pattern at `api/app.py:191-201`)
**Issue:** `raw = file.file.read()` materializes the entire upload before the
`MAX_BATCH_BYTES` check. The size cap therefore bounds what is *parsed*, not what
is *held* — a multi-GB upload exhausts memory before the 413 fires. (Starlette
spools to disk past 1 MB, but `read()` pulls it all back into RAM.)
**Fix:** stream with a cap, e.g. read in chunks and abort past the limit:
```python
raw = b""
while chunk := file.file.read(65536):
    raw += chunk
    if len(raw) > MAX_BATCH_BYTES:
        raise HTTPException(status_code=413, detail="batch upload exceeds size limit")
```

### WR-12: Registry-guard test stub makes the Production assertion vacuous

**File:** `tests/test_nhanes_training.py:273-299`
**Issue:** `_StubRegistryClient.get_model_version` returns `"Production"` for the
pinned version unconditionally — it never reflects transitions. So
`apply_challenger_stages`'s before/after guard (`before != "Production" or after
!= "Production"`) cannot fail under this stub: the test pins the call sequence,
not the invariant. A regression that breaks the guard logic would still pass.
**Fix:** model stage state in the stub:
```python
def __init__(self, production_version="9"):
    self.calls = []
    self.stages = {"9": "Production", "10": "None", "11": "None"}
def get_model_version(self, name, version):
    return SimpleNamespace(current_stage=self.stages.get(str(version), "None"))
def transition_model_version_stage(self, name, version, stage, archive_existing_versions=False):
    self.calls.append((str(version), stage))
    self.stages[str(version)] = stage
    if archive_existing_versions:
        for v, s in self.stages.items():
            if v != str(version) and s == stage:
                self.stages[v] = "Archived"
```

## Info

### IN-01: Winner-selection helper is duplicated across training and evaluation

**File:** `src/training/train_nhanes.py:239-241` and `src/evaluation/evaluate_nhanes.py:50-52`
**Issue:** `select_by_cv` and `aggregate_cv` are identical strict-max one-liners in
two modules. Divergent tie behavior later would silently fork the protocol.
**Fix:** keep one (e.g. in `evaluate_nhanes`) and import it in the other.

### IN-02: No dataset hash pin — the "locked" holdout shifts if the CSV is re-derived

**File:** `src/training/train_nhanes.py:119-131`
**Issue:** `load_native_frame` never records a checksum/row-count of
`nhanes_ckd_derived.csv`. Row-id equality between the winner artifact and the
recomputed holdout (evaluate line 147) holds only if the file bytes are unchanged;
a re-derivation with reordered rows silently redefines the "locked" split.
**Fix:** log `sha256` + row count of the CSV into every Claim-2 run and assert it
in `run_evaluation` before comparing.

### IN-03: Exact holdout-size assertion is brittle to fixture/cohort changes

**File:** `tests/test_nhanes_training.py:103`
**Issue:** `len(X_hold) == int(0.2 * len(df))` assumes `train_test_split` yields
exactly `int(0.2*n)`; for n=61, sklearn gives `ceil(12.2)=13`. Passes at n=60 only.
**Fix:** `assert len(X_hold) == math.ceil(0.2 * len(df))` or assert a 0.19–0.21 band.

### IN-04: `"1.0"`-literal scan in tests invites the next false positive

**File:** `tests/test_nhanes_training.py:181-189`
**Issue:** `assert "1.0" not in src` bans a common float literal to enforce the
no-recorded-UCI-AUC rule — after the suite already false-positived once on
"reproducible" (fixed with `\buci\b`). The next legitimate `1.0` threshold breaks
the suite for reasons unrelated to the rule.
**Fix:** scan for the specific banned pattern (e.g. `roc_auc\s*==?\s*1\.0` or
`recorded.*auc`) instead of the bare literal.

### IN-05: Adapter-isolation scans are substring-based and one-directional

**File:** `tests/test_nhanes_training.py:302-312` and `tests/test_api_v2.py:274-282`
**Issue:** Both scans grep for the literal `harmonize_v9` in `api/`. Adequate
against accidental static imports, but evadable via dynamic import (`importlib`)
and trippable by an innocent comment. Consider also asserting at runtime that
`sys.modules` has no `harmonize_v9` after serving a v2 request.
**Fix:** add to the v2 predict test:
`assert "src.training.harmonize_v9" not in sys.modules`.

### IN-06: No v2 readiness signal — v1 `/health` reports the v1 pin only

**File:** `api/app.py:237-241` and `api/app.py:369-378`
**Issue:** Operators can probe v1 readiness via `/health` but v2 exposes only
`/v2/model_info` (which 503s when unconfigured — correct, but it conflates
"unconfigured" with "broken"). A `/v2/health`-style probe would distinguish them.
**Fix:** extend `HealthResponse` or add a v2 health route reporting
`v2_model_version or "unconfigured"`.

### IN-07: Import-time process-env mutation in four modules

**File:** `src/training/train_nhanes.py:55`, `src/training/harmonize_v9.py:32`, `src/evaluation/evaluate_nhanes.py:44`, `api/model_loader.py:19`
**Issue:** `os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")` at import
time mutates global process state as a side effect of importing. Harmless here
(setdefault, localhost file store is the locked architecture) but surprising and
untestable in isolation.
**Fix:** move to the `main()` entry points (and `lifespan` for serving).

### IN-08: `main()` loads and splits twice; correctness rests on seed determinism

**File:** `src/training/train_nhanes.py:318-330` and `src/training/train_nhanes.py:244-251`
**Issue:** `main` loads the frame, splits, and sweeps, then `run_experiment_native`
reloads the CSV and re-splits internally. The two splits agree only because both use
seed 42 on identical bytes (see IN-02). Wasteful and fragile in combination.
**Fix:** pass the already-loaded `(X_dev, X_hold, y_dev, y_hold)` into
`run_experiment_native` instead of reloading.

### IN-09: Plan acceptance criterion for width-mismatch has no direct unit test

**File:** `tests/test_api_v2.py` (whole file) covering `api/model_loader.py:146-184`
**Issue:** 07-03-PLAN required "`load_v2_artifacts` against a width-mismatched stub
raises RuntimeError". The suite pins the artifact-path *constant* and mocks the
*loader* at the route boundary, but never calls `load_v2_artifacts` with a
stub pipeline/estimator whose widths disagree — the RuntimeError path is proven
only by the live probe, not by any test.
**Fix:** add a test monkeypatching `mlflow`/`joblib` (or factoring a
`_assert_width(pipeline, model, version)` pure helper) and assert `RuntimeError`.

## Threat-Model Note

- **Quarantine enforcement.** Direction is correct: allow-list projection in
`load_native_frame` (`train_nhanes.py:133-157`) drops the 11 label-source columns
before `assert_quarantine` gates the training frame fail-closed via `SystemExit`
(`preprocess_nhanes.py:61-80`), and the serving schema (`COLUMN_ORDER_V2`) cannot
express quarantined names at all. Residual risks: the ban is name-based (a renamed
proxy column passes — inherent to the design, flag derived features by lineage if
the threat matters); the ban list lives in two places with no equality pin
(WR-02); missing expected columns train silently on a reduced schema (WR-03).
- **Harmonization adapter isolation from serving.** Adapter (`harmonize_v9.py`) never
calls `fit`, loads v9 read-only by *version* pin (survives the v9→Archived
transition), and both test suites scan `api/` for the adapter name
(`test_adapter_not_served`, `test_serving_never_imports_harmonization_adapter`).
Residual: scans are substring-based (IN-05); no runtime `sys.modules` assertion.
Eval-only use is otherwise clean — challenger probabilities come from the logged
`holdout_predictions_native.csv` artifact with row-id + label equality enforced
(`evaluate_nhanes.py:146-155`), so the holdout is scored once and never refit.
- **v1/v2 coexistence.** v1 handlers, `PredictionLog`/`predictions`, and the v1
loader are byte-identical; v2 uses a separate loader slot, separate pipeline
artifact filename (drift-pinned by test), and a separate `predictions_v2` table
with version-stamped rows; unconfigured v2 fails closed with 503 naming the key
and no secrets. Residual risks: v2 startup failure kills v1 too (WR-05);
null/whitespace v2 pin misroutes to a load attempt (WR-06); int-vs-String
categorical mismatch on `predictions_v2` writes (WR-10); no v2 health probe (IN-06).
- **Localhost scope.** No authentication on `/v2/*`, the registry, or
`promote_challenger.py` — consistent with the project's localhost academic scope
and the pre-existing v1 posture, but the promotion script is the Production
mutation point and enforces nothing itself (WR-07); the human gate is currently
pure procedure. No secrets in code, no `eval`/deserialization sinks, no
`DATABASE_URL` value logging, upload caps present but post-read (WR-11).

---

_Reviewed: 2026-10-15T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
