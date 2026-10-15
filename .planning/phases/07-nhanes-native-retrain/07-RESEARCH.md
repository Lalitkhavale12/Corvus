# Phase 7: NHANES Native Retrain - Research

**Researched:** 2026-10-15
**Domain:** Cross-schema clinical ML retrain — sklearn pipelines, stratified CV + bootstrap CIs, MLflow champion/challenger registry, FastAPI schema evolution
**Confidence:** HIGH (in-repo patterns + live CSV/XPT verification + sklearn/MLflow/CDC official docs)

## Summary

Phase 7 retrains all 9 Phase-2 configs (6 classical + MLP×3) on NHANES-native features from `data/nhanes/nhanes_ckd_derived.csv` (verified live: **5,343 rows × 177 cols**, CKD rate **17.31%**, n_pos=925), validates with stratified 5-fold CV + bootstrapped CIs + one locked 20% holdout scored once, registers challengers as `corvus-ckd` v10+, and promotes to Production only on strict holdout ROC-AUC superiority over v9 at a human gate. The winner serves on new `/v2` endpoints; v1 keeps serving v9.

Two findings dominate planning. **First, D-01's feature list does not exist in the CSV.** The derived CSV contains labs + demographics only — no BMI, no blood pressure, no diabetes/hypertension flags. Those live in unmerged XPT files on disk (`BMX_L`, `BPXO_L`, `DIQ_L`, `MCQ_L`, all SEQN-keyed, all read-verified). The planner must gate on a human decision: extend the derivation by SEQN merge (needs explicit user approval — the protocol bans casual re-derivation) or train on CSV-present features only. **Second, the cross-schema comparison protocol (D-03's open item) resolves to a paired harmonized-holdout design**: score v9 and the challenger on the *same* locked NHANES holdout rows against the *same* derived labels, with v9 reading through a fixed harmonization adapter (9 shared numeric fields mapped, its 10 categorical fields mode-filled, documented handicap). The tempting alternative — comparing the challenger against v9's recorded ~1.0 UCI test AUC — is invalid and must never be implemented: cross-dataset AUC comparison cannot dethrone anything.

**Primary recommendation:** Lock the holdout first; run CV on the 80% dev split with per-fold pipeline re-fit; refit the winning config on full dev; score both models on the identical locked holdout via the harmonization adapter; promote iff challenger AUC strictly exceeds v9 AUC with the paired-bootstrap difference CI shown to the human gate; serve on `/v2` with a second model-loader slot and a separate predictions log table.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Full mapped set: 14 labs/vitals (BUN, glucose, Na/K/Ca/P, bicarbonate, HGB, HCT, WBC, RBC, BP, BMI, age) + sex/ethnicity/income/education + diabetes/hypertension flags. Quarantine (creatinine/eGFR/ACR + 7 derived columns) stays banned.
- **D-02:** Survey weights ignored in training (ML convention; model serves individuals).
- **D-03:** Challenger dethrones v9 iff its holdout ROC-AUC strictly exceeds v9's under the same protocol. Open protocol detail for planning: v9 cannot natively read NHANES rows (10 absent fields), so the comparison protocol (e.g. v9 on imputed-harmonized holdout vs challenger native, or vs v9's recorded 1.0 with documented handicap) must be designed by research/planning — not assumed.
- **D-04:** Human gate approves any Production promotion. No auto-promote, ever.
- **D-05:** New `/v2/predict` + `/v2/batch_predict` on the native schema; v1 untouched until promotion, then explicit traffic move.
- **D-06:** Hard cutover at promotion (pin flips). No shadow/canary machinery.
- **D-07:** Stratified 5-fold CV with bootstrapped CIs on all 5,343 rows + one locked 20% holdout scored once. Internal-only; reported as such.
- **D-08:** Derived labels are disclosed as derived next to every metric, forever. Never presented as diagnosed truth.

### Agent's Discretion
None — the user decided every area directly. Planner has flexibility only on module layout, run naming, and test design.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FR-2.1 | Train LR, RF, XGB, LGBM, MLP (3 activations) + DT/GB (established 9-config set) | Standard Stack (reuse `ESTIMATORS` + `ACTIVATIONS` verbatim); native pipeline builder |
| FR-2.2 | Log accuracy, precision, recall, F1, ROC-AUC per run | `compute_metrics` reuse; + CV mean±SD and bootstrap CI logging |
| FR-2.3 | Log pipeline + model in same MLflow run (Claim 2) | `run_experiment` shape generalized to native schema; co-logged native pipeline |
| FR-2.4 | Compare all models; best by ROC-AUC | Strict-max `select_winner` on CV-mean AUC; final rank on locked holdout |
| FR-2.5 | Register best model to registry | Challenger versions append under `corvus-ckd` (v10+); winner → Staging |
| FR-3.1 | Registry with Staging/Production/Archived | `transition_model_version_stage` (still functional in mlflow 3.16.1); human gate → Production |
| FR-3.2 | Version tracking | run_id→version linkage via `resolve_winner_version`; schema tags on runs |
| FR-3.3 | Promote/demote between stages | Existing `scripts/promote_production.py` pattern; no auto-promote (D-04) |
| FR-4.1 | `/v2/predict`, `/v2/batch_predict` (+ existing `/health`, `/model_info`) | api/app.py route patterns; second serving slot; v1 routes untouched |
| FR-4.2 | Pydantic validation of native schema | New `CKDRequestNative` mirroring `CKDRequest` strictness; 422 fail-closed |
| FR-4.3 | Log `model_version` per prediction | Separate v2 log table (do not alter v1 `predictions` table) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Native pipeline + estimator training | API / Backend (offline `src/training`) | — | Same tier as Phase 2; no client involvement |
| CV / bootstrap / holdout evaluation | API / Backend (offline `src/evaluation`) | — | Extends `evaluate.py`; runs against local mlruns |
| Harmonization adapter (NHANES→UCI-24) | API / Backend (offline eval script) | — | Comparison-only shim; must never leak into serving |
| Challenger registry versions | MLflow tracking store (file) | — | `corvus-ckd` v10+ append; stages preserved |
| `/v2` prediction serving | API / Backend (FastAPI) | — | Second loader slot; v1 slot untouched |
| Prediction logging (v2) | Database / Storage (Postgres) | — | Separate table; v1 table schema frozen |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.9.1 [VERIFIED: venv import] | `StratifiedKFold`, `train_test_split`, `Pipeline`/`ColumnTransformer`, all 9 estimators | Installed; Phase 2 proven; `cross_val_predict` docs confirm StratifiedKFold default for classifiers [CITED: scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_predict.html] |
| mlflow | 3.16.1 [VERIFIED: venv import] | Experiment tracking, `corvus-ckd` registry, stage transitions | Installed; `transition_model_version_stage` pattern proven in `src/evaluation/evaluate.py:80-89`; file store via `MLFLOW_ALLOW_FILE_STORE` |
| xgboost, lightgbm | installed (Phase-2 pinned) | 2 of the 9 configs | Reuse `ESTIMATORS` dict verbatim — no re-spec |
| numpy | 2.4.6 [VERIFIED: venv import] | Stratified bootstrap resampling (`np.random.default_rng(42)`) | No new dependency for CIs |
| pandas | 3.0.6 [VERIFIED: venv import] | CSV I/O, SEQN merge if approved | Already the frame layer |
| fastapi + pydantic | installed (Phase-3 pinned) | `/v2` routes + `CKDRequestNative` | Mirror `api/app.py` + `api/schemas.py` patterns |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.17.1 [VERIFIED: venv import] | Already present; *not* needed (no DeLong — bootstrap instead) | Only if planner adds a test needing stats helpers |
| joblib | installed | Native pipeline artifact dump | Same `preprocessing_pipeline.joblib` pattern per run |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Paired bootstrap difference-CI | DeLong test for paired AUCs | DeLong is valid for non-nested same-test-set comparison but needs hand-rolled variance code; Demler et al. document widespread misuse [CITED: pubmed.ncbi.nlm.nih.gov/22415937]. Bootstrap is dependency-free and auditable — use bootstrap |
| Stage transitions | MLflow aliases (`champion`/`challenger`) | Aliases are the current MLflow recommendation [CITED: mlflow.org/docs/latest/ml/model-registry] but FR-3.1 mandates stages, installed 3.16.1 still supports them, and the whole serving path pins numeric versions. Migration is out of scope; keep stages + numeric pins |
| Same `corvus-ckd` experiment | Successor experiment (e.g. `corvus-ckd-nhanes`) | Planner's call (CONTEXT allows either); registry continuity is preserved either way since versions append under one registered model. Recommendation: successor experiment + same registered model — separates UCI/CV histories while keeping the champion line intact |

**Installation:**
```bash
# No new packages. All required libraries are installed in ./venv (verified above).
```

**Version verification:** `cmd /c venv\python.exe -c "import sklearn, mlflow, numpy, scipy, pandas"` → sklearn 1.9.1, mlflow 3.16.1, numpy 2.4.6, scipy 1.17.1, pandas 3.0.6 [VERIFIED: venv import 2026-10-15]. Test suite: 45 passed [VERIFIED: pytest run 2026-10-15].

## Package Legitimacy Audit

No external packages are installed by this phase — every library in the Standard Stack is already vendored in `./venv` and exercised by Phases 1–3. No registry lookups required; no `SLOP`/`SUS` candidates exist.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| scikit-learn 1.9.1 | PyPI (pre-installed) | 18 yrs | ~35M/wk | github.com/scikit-learn/scikit-learn | OK | Approved — reuse |
| mlflow 3.16.1 | PyPI (pre-installed) | 7 yrs | ~4M/wk | github.com/mlflow/mlflow | OK | Approved — reuse |
| numpy 2.4.6 | PyPI (pre-installed) | 19 yrs | ~140M/wk | github.com/numpy/numpy | OK | Approved — reuse |
| xgboost / lightgbm | PyPI (pre-installed) | — | — | established | OK | Approved — reuse |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
data/nhanes/nhanes_ckd_derived.csv (5,343 x 78, FROZEN)
        │
        ▼
┌─ QUARANTINE GATE ─────────────────────────────────┐
│ assert zero overlap with 11 banned cols; abort     │
│ (eGFR, URXUMA, URXUMS, URXUCR, URXCRS, URDACT,     │
│  URDUMALC, URDUCRLC, LBXSCR, LBDSCRSI, ACR)        │
└──────────────────────┬────────────────────────────┘
                       ▼
            LOCKED SPLIT (seed 42, stratify)
            ┌──────────────┬──────────────┐
            │ 80% DEV      │ 20% HOLDOUT  │
            │ (~4,274)     │ (~1,069)     │
            │ CV happens   │ sealed;      │
            │ here only    │ scored ONCE  │
            └──────┬───────┴──────┬───────┘
                   ▼              ▼
   ┌─ 5-fold StratifiedKFold (shuffle, seed 42) ─┐   (holdout waits)
   │ per fold: fresh pipeline fit on fold-train │──► CV mean±SD per config
   │ → fit estimator → fold AUC (9 configs)     │    → select best config
   └──────────────────┬────────────────────────┘
                      ▼
   refit best config on FULL dev (fresh pipeline fit)
   → log Claim-2 run + register challenger (Staging)
                      ▼
   ┌─ PAIRED COMPARISON on locked holdout ───────┐
   │ challenger native ──► AUC_c                  │
   │ v9 via HARMONIZATION ADAPTER ──► AUC_v9      │
   │ (same rows, same derived labels)            │
   │ rule: promote iff AUC_c > AUC_v9 (strict)   │
   │ report: paired-bootstrap CI of (AUC_c-AUC_v9)│
   └──────────────────┬────────────────────────┘
                      ▼ HUMAN GATE (D-04)
        ┌─────────────┴──────────────┐
        │ promote → Production       │ keep v9
        │ /v2 serves challenger      │ /v2 serves nothing new;
        │ v1 untouched either way    │ challenger stays Staging
        └────────────────────────────┘
```

### Recommended Project Structure
```
src/
├── training/
│   ├── train.py / train_mlp.py  # UNTOUCHED (UCI path frozen)
│   ├── train_nhanes.py          # native run_experiment: CSV→quarantine gate→split→pipeline→fit→Claim-2 run (9 configs)
│   └── harmonize_v9.py          # EVAL-ONLY NHANES→UCI-24 adapter (never imported by api/)
├── evaluation/
│   ├── evaluate.py              # UNTOUCHED
│   └── evaluate_nhanes.py       # CV aggregate + paired comparison + stage transitions for challengers
├── preprocessing/
│   └── preprocess_nhanes.py     # native build_pipeline (numeric median + onehot; column lists from config)
api/
├── app.py                       # ADD /v2 routes; v1 code paths byte-identical
├── schemas.py                   # ADD CKDRequestNative (+ batch items); v1 schemas untouched
└── model_loader.py              # ADD second slot: resolve/load native pinned version (api.v2_pinned_version)
config/config.yaml               # ADD data.nhanes_* + api.v2_* keys (extend, never rename existing)
```

### Pattern 1: Lock-holdout-first, CV-inside-dev
**What:** `train_test_split(stratify=y, test_size=0.2, random_state=42)` on the quarantined native frame *before* anything fits; CV (`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`) runs on the 80% dev split only; the holdout is transformed by the final refit pipeline and scored exactly once [CITED: scikit-learn.org nested-vs-non-nested CV — tuning/selection on the same data used for reporting is optimistically biased].
**When to use:** Always in this phase — D-07's "CV on all 5,343 rows + locked holdout" reads as CV over the full cohort *for selection reporting* with the holdout sealed for the promotion decision; the planner must define that CV folds for *selection* come from dev only, never touching holdout rows.
**Example:**
```python
# Source: sklearn docs (StratifiedKFold) + src/training/train.py:135-140 (fit-on-train-only shape)
from sklearn.model_selection import StratifiedKFold, train_test_split
X_dev, X_hold, y_dev, y_hold = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for tr, va in skf.split(X_dev, y_dev):
    pipe = build_native_pipeline().fit(X_dev.iloc[tr])  # fresh fit per fold
    est = build_estimator(name).fit(pipe.transform(X_dev.iloc[tr]), y_dev.iloc[tr])
    fold_auc = roc_auc_score(y_dev.iloc[va], est.predict_proba(pipe.transform(X_dev.iloc[va]))[:, 1])
```

### Pattern 2: Paired harmonized-holdout comparison (D-03 resolution)
**What:** Both models score the *identical* holdout rows against the *identical* derived labels. v9 reads holdout rows through `harmonize_v9.py`: map shared numerics (age, BUN→bu, glucose→bgr, Na→sod, K→pot, HGB→hemo, HCT→pcv, WBC→wc, RBC-count→rc) [ASSUMED — see A1], fill v9's 10 categorical inputs (rbc, pc, pcc, ba, htn, dm, cad, appet, pe, ane [VERIFIED: config/config.yaml:12]) with the fitted UCI pipeline's own most-frequent imputations, and pass through v9's *frozen, already-fitted* UCI pipeline + estimator — never refit v9 on NHANES. Challenger reads the same rows natively. Promotion iff `AUC_challenger > AUC_v9` strictly; paired stratified bootstrap (B=2000, `default_rng(42)`, resample holdout indices once and score both models per resample) yields the CI of the *difference* for the human gate [CITED: pROC ci.auc — 95% CI with 2000 stratified bootstrap replicates is the field standard].
**When to use:** This is the *only* valid promotion comparison in the phase.
**Anti-design (must never be built):** comparing challenger holdout AUC against v9's recorded UCI test AUC (~1.0 on a tiny, famously separable UCI split) — cross-dataset, cross-label comparison that the challenger can never win and that proves nothing.

### Pattern 3: Claim-2 run per challenger with schema tags
**What:** Generalize `run_experiment` (`src/training/train.py:124-160`): same shape (params + 5 metrics + pipeline artifact + cloudpickle model + registered_model_name=`corvus-ckd`), plus `mlflow.set_tag("schema", "nhanes-native")`, quarantine-attestation tag, CV-mean/CI metrics alongside holdout metrics. Register → version v10+ → immediate transition to Staging (challenger posture), never Production without the gate.

### Anti-Patterns to Avoid
- **Refitting v9 on NHANES data:** destroys the champion baseline; v9 artifacts are read-only in this phase.
- **Importing the harmonization adapter in serving code:** the adapter is eval-only; `/v2` serves the native pipeline exclusively. Enforce with a test asserting `api/` never imports `harmonize_v9`.
- **CV pooling via `cross_val_predict` into one AUC:** sklearn documents this "may not be a valid way to measure generalization performance" [CITED: sklearn cross_val_predict docs]. Report per-fold mean±SD for selection; bootstrap CI only on the locked holdout.
- **Auto-promotion on strict-max:** D-04 forbids it — the strict-max rule *qualifies* a challenger; a human *promotes* it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fold splitting | Custom index math | `StratifiedKFold(shuffle=True, random_state=42)` | Guarantees ~17.3% positive rate per fold (~185 positives/fold); hand-rolled splits risk all-positive-free folds and undefined AUC [CITED: sklearn stratification docs] |
| AUC confidence intervals | DeLong variance by hand | Stratified bootstrap, B=2000, `np.random.default_rng(42)` | DeLong misuse is a documented trap (Demler et al.); bootstrap is auditable, seed-fixed, dependency-free |
| Model comparison test | Custom paired test | Bootstrap CI of the paired AUC difference on identical rows | Same resample indices for both models = paired by construction |
| Registry promotion | Custom version bookkeeping | `transition_model_version_stage` + `resolve_winner_version` pattern (`src/evaluation/evaluate.py:56-89`) | Proven against mlflow 3.16.1; append-only versions |
| Native imputation/scaling/encoding | Custom transformers | `build_pipeline` generalization (median + StandardScaler + OneHotEncoder, config-driven) | Phase-1 leak-safe contract carries over; Claim-2 needs a single Pipeline object |
| Survey inference correction | Weight-rail logic in training | Nothing — D-02 locks weights out; disclose unweighted/internal-only (D-07/D-08) | CDC requires MEC weights (`WTMEC2YR`) for population estimates [CITED: wwwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx]; ML-for-individuals convention ignores them, but the SaML 2026 review flags undisclosed ignoring as an inference-validity violation [CITED: proceedings.mlr.press/v333/oh26a.html] — disclosure is the mitigation |

**Key insight:** Every hard problem in this phase (leak-safe CV, paired comparison, registry lifecycle, fail-closed serving) already has a proven in-repo implementation from Phases 1–3. The only genuinely new code is the native column lists, the quarantine gate, the harmonization adapter, and the paired-bootstrap comparison — everything else is generalization, not invention.

## Common Pitfalls

### Pitfall 1: D-01's vitals/comorbidities are not in the CSV
**What goes wrong:** Planner writes tasks assuming BP/BMI/diabetes columns exist; executor KeyErrors on day one.
**Why it happens:** D-01 lists "BP, BMI" + "diabetes/hypertension flags" but the locked CSV (verified: full 78-column dump) has no `BMXBMI`, no `BPX*`, no `DIQ*`/`MCQ*` columns.
**How to avoid:** Wave 0 task 1 = human decision: (a) approve SEQN-merge extension from `BMX_L` (has `BMXBMI` [VERIFIED: read_sas shape (8860,22)]), `BPXO_L` (`BPXOSY1/BPXODI1` [VERIFIED: (7801,12)]), `DIQ_L`/`MCQ_L` (diabetes/hypertension items [VERIFIED: files present; item semantics ASSUMED — A2]) with re-run of the 3 audit gates, or (b) lock the native set to CSV-present labs + demographics. Default to (b) if approval is not given.
**Warning signs:** Any plan referencing `BMXBMI` without a merge task and a protocol-amendment approval.

### Pitfall 2: Comparing against v9's recorded ~1.0
**What goes wrong:** Challenger (honest AUC ~0.75–0.85 on derived labels) can never beat a cross-dataset 1.0; phase dead-ends at the gate.
**Why it happens:** v9's UCI test split is tiny and UCI-CKD is famously near-separable; 1.0 measures dataset easiness, not model superiority.
**How to avoid:** Forbid Option B in PLAN.md; implement only the paired harmonized-holdout protocol (Pattern 2).

### Pitfall 3: Leakage via full-frame pipeline fit or holdout peeking
**What goes wrong:** Fitting the native pipeline on all 5,343 rows before splitting, or re-running the holdout after seeing its score, inflates the promotion metric.
**Why it happens:** Convenience (`fit_transform` on the whole CSV) and iteration pressure at the gate.
**How to avoid:** Pipeline `.fit()` only on fold-train or dev splits (Pattern 1); holdout scoring lives in a separate script run once; test asserts holdout indices never appear in any fit call (index-disjointness test, cf. `test_split_before_fit_no_overlap`).

### Pitfall 4: Quarantine breach through innocent-looking columns
**What goes wrong:** A merged or engineered feature reintroduces creatinine/eGFR/ACR signal (e.g. a "kidney panel" composite, or `LBDSCRSI` sneaking in via a wildcard column list).
**Why it happens:** The CSV has 177 columns (v2 re-derivation); allow-listing by wildcard is one typo from circularity.
**How to avoid:** Hard gate: explicit native-column allow-list in config + `assert not (set(frame) & QUARANTINE_11)` aborting training; the 11 banned names are `eGFR, URXUMA, URXUMS, URXUCR, URXCRS, URDACT, URDUMALC, URDUCRLC, LBXSCR, LBDSCRSI, ACR` [VERIFIED: data/nhanes/NHANES_PROTOCOL.md:26-31]. Circularity audit (protocol gate 1) re-run if features change.

### Pitfall 5: MLP non-convergence treated as failure
**What goes wrong:** `ConvergenceWarning` at `max_iter=500` crashes the 9-config sweep.
**Why it happens:** Larger n (4,274 dev rows) changes convergence behavior vs Phase 2's 279 rows.
**How to avoid:** Keep the established warning-not-crash pattern (`src/training/train_mlp.py:79-85`); log warnings, never raise. Do not add early stopping without a human decision (val-split noise rationale still holds).

### Pitfall 6: v1 predictions-table schema drift
**What goes wrong:** v2 predictions (native fields) written into the 24-field `predictions` table corrupt FR-5.2 logging or break v1 reads.
**Why it happens:** Reusing the v1 log call site for a different schema.
**How to avoid:** Separate v2 log table (planner's schema decision); v1 `db.py` paths byte-identical; test asserts v1 table columns unchanged.

### Pitfall 7: 100%-missing and heavy-missing columns silently entering the pipeline
**What goes wrong:** Columns like `RIDAGEMN`/`RIDEXAGM` (100% missing [VERIFIED: live missingness probe]) or `LBXSLDSI` (25.6% missing) degrade or break the native pipeline.
**Why it happens:** Copying "all labs" into the allow-list without the missingness audit.
**How to avoid:** Drop 100%-missing household/provenance columns at load; median imputation covers the rest (matches `numeric_impute_strategy: median`); log per-column missingness next to CV metrics.

## Code Examples

### Stratified bootstrap CI for holdout AUC + paired difference
```python
# Source: pROC convention (2000 stratified replicates) + numpy Generator API
import numpy as np
from sklearn.metrics import roc_auc_score

rng = np.random.default_rng(42)
y, p_c, p_v = y_hold, proba_challenger, proba_v9  # same rows, same labels
pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
diffs = []
for _ in range(2000):
    idx = np.concatenate([rng.choice(pos, len(pos), replace=True),
                          rng.choice(neg, len(neg), replace=True)])
    diffs.append(roc_auc_score(y[idx], p_c[idx]) - roc_auc_score(y[idx], p_v[idx]))
lo, hi = np.percentile(diffs, [2.5, 97.5])  # CI of (AUC_c - AUC_v9) for the gate
```

### Quarantine gate (import in train_nhanes before any split)
```python
# Source: data/nhanes/NHANES_PROTOCOL.md quarantine list (lines 26-31)
QUARANTINE = {"eGFR", "URXUMA", "URXUMS", "URXUCR", "URXCRS", "URDACT",
              "URDUMALC", "URDUCRLC", "LBXSCR", "LBDSCRSI", "ACR"}
breach = QUARANTINE & set(frame.columns)
if breach:
    raise SystemExit(f"QUARANTINE BREACH — aborting: {sorted(breach)}")
```

### Native serving slot (extends api/model_loader.py pattern)
```python
# Source: api/model_loader.py:53-59 (resolve_pinned_version) generalized
def resolve_v2_version() -> str:
    override = os.environ.get("MODEL_VERSION_V2")
    if override:
        return str(override)
    return str(load_config()["api"]["v2_pinned_version"])  # new config key
# Load models:/corvus-ckd/<v2> + co-logged native pipeline; assert
# pipeline width == estimator n_features_in_ (mirror of the v1 assert).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MLflow stage transitions as the promotion API | Aliases (`@champion`) recommended; stages deprecated since 2.9 | MLflow 2.9+ | None this phase: 3.16.1 still honors stages; migration deferred as documented tech debt (`src/evaluation/evaluate.py:76-79`) |
| Single train/test split reporting (Phase 2) | CV mean±SD for selection + locked holdout scored once for promotion | This phase (D-07) | Selection bias (Cawley & Talbot / sklearn nested-CV docs) contained; promotion metric uncontaminated |
| Ignoring NHANES weights silently (common ML practice) | Ignoring weights + mandatory disclosure (internal-only, unweighted) | SaML guideline 2025–2026 | Satisfies D-02 while meeting the disclosure bar the literature now expects |
| Cross-dataset AUC comparison | Paired same-rows/same-labels comparison | This research (D-03 resolution) | Only valid dethroning protocol available given v9's schema blindness |

**Deprecated/outdated:**
- `cross_val_predict`-pooled AUC as a generalization estimate: explicitly discouraged by sklearn docs — do not use.
- DeLong hand-implementation for this comparison: valid in theory for non-nested same-test-set models, but bootstrap dominates on auditability — do not implement.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | NHANES→UCI numeric mapping (BUN→bu, glucose→bgr, Na→sod, K→pot, HGB→hemo, HCT→pcv, WBC→wc, RBC-count→rc) is semantically valid | Pattern 2 | Harmonized v9 scores garbage; comparison invalid — planner must verify each code against CDC docs with a clinician-readable mapping table task |
| A2 | `DIQ_L.DIQ010` = diabetes status, `MCQ_L` hypertension item exists with usable semantics; merge shrinks cohort (BMX 8,860 / BPXO 7,801 vs 5,343 derived) | Pitfall 1 | Merge yields fewer rows or wrong flags — Wave-0 merge-feasibility probe (SEQN overlap count) required before locking D-01's full list |
| A3 | v9's recorded test AUC ≈ 1.0 (Phase-2 tracer: LR roc_auc=1.0; STATE.md) applies to champion mlp-relu v9 similarly | Pattern 2 (Option-B rejection) | If v9's recorded AUC were modest, Option B would look tempting — it is still invalid (cross-dataset); rejection stands regardless |
| A4 | Challenger honest holdout AUC will land ~0.75–0.85 (derived-label task without creatinine) | Summary | If much lower, gate fails and phase still succeeds as evidence (negative result is a valid outcome); plan must frame non-promotion as acceptable |
| A5 | `config.yaml` `data.nhanes_*` / `api.v2_*` key additions don't disturb `load_config()` consumers | Structure | Low — `load_config` is a plain YAML deepcopy; additive keys are safe by construction |

**If this table is empty:** n/a — 5 assumptions need confirmation (A1/A2 at Wave 0, others at planning/gate).

## Open Questions (RESOLVED — decided in plans, see pointers)

1. **BMI/BP/comorbidity merge?** — RESOLVED: user-approved merge-all + re-audit (protocol v2; 07-01 Task 1).
   - What we know: CSV lacks them; XPT sources exist SEQN-keyed; protocol bans casual re-derivation; D-01 lists them as locked.
   - What's unclear: Whether the user approves a protocol amendment + SEQN merge + audit-gate re-run.
   - Recommendation: Wave-0 human checkpoint with the SEQN-overlap counts; default to CSV-present set (labs + demographics) if declined. Planning cannot lock the feature list before this answer.

2. **v2 prediction-log table shape?** — RESOLVED: separate `predictions_v2` table (07-03 Task 2).
   - What we know: v1 `predictions` table holds 24 UCI fields + outcome + version + timestamp; D-05 freezes v1.
   - What's unclear: Separate `predictions_v2` table vs nullable-column migration.
   - Recommendation: Separate table (zero v1 blast radius); planner decides DDL.

3. **Same or successor experiment?** — RESOLVED: successor `corvus-ckd-nhanes`, same registered model (07-01 plan).
   - What we know: CONTEXT permits either; registry continuity holds either way.
   - What's unclear: Team preference for MLflow UI separation.
   - Recommendation: Successor experiment `corvus-ckd-nhanes`, same registered model `corvus-ckd`.

4. **Native lab-code mapping (A1)?** — RESOLVED: CDC-verified mapping table in 07-02 Task 2 with quarantine re-check.
   - What we know: Candidate SI-unit columns present (LBDSBUSI, LBDSGLSI, LBXSNASI, LBXSKSI, LBDSCASI, … [VERIFIED: column dump]).
   - What's unclear: Code-level semantics per CDC lab docs.
   - Recommendation: Planner adds a mapping-verification task against CDC documentation before pipeline lock, with quarantine re-check.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| venv Python 3.11 | Everything | ✓ | 3.11 (wheels cp311 per STACK.md) | — |
| sklearn / mlflow / numpy / scipy / pandas | Training + eval | ✓ | 1.9.1 / 3.16.1 / 2.4.6 / 1.17.1 / 3.0.6 | — |
| xgboost / lightgbm | 2 of 9 configs | ✓ (Phase-2 proven) | Phase-2 pins | — |
| fastapi / pydantic / uvicorn | `/v2` serving | ✓ (Phase-3 proven) | Phase-3 pins | — |
| pytest | Validation | ✓ (45 passed) | ≥8.0 | — |
| mlruns file store | Tracking/registry | ✓ | `MLFLOW_ALLOW_FILE_STORE=true` pattern | — |
| Postgres | v2 log table (runtime) | ✓ (Phase-3 compose proven) | — | Tests mock the session (established pattern) |
| `data/nhanes/*.xpt` sources | Optional merge (Q1) | ✓ on disk | 2021–2023 cycle | CSV-only set if merge declined |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — all green.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥ 8.0 |
| Config file | none (default discovery) |
| Quick run command | `cmd /c venv\python.exe -m pytest tests/ -q` |
| Full suite command | `cmd /c venv\python.exe -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FR-2.1 | 9 native configs train on synthetic NHANES-shaped frame | unit (synthetic) | `pytest tests/test_train_nhanes.py -x` | ❌ Wave 0 |
| FR-2.3 | Challenger run co-logs native pipeline + model (Claim 2) | unit (tmp MLflow store) | `pytest tests/test_train_nhanes.py::test_claim2_native -x` | ❌ Wave 0 |
| FR-2.4 | Strict-max selects highest CV-mean AUC; holdout scored once | unit | `pytest tests/test_evaluate_nhanes.py -x` | ❌ Wave 0 |
| D-03 | Paired comparison: same rows both models; Option-B path absent | unit | `pytest tests/test_compare.py::test_same_rows_same_labels -x` | ❌ Wave 0 |
| Quarantine | Any of 11 banned cols aborts before split | unit | `pytest tests/test_train_nhanes.py::test_quarantine_aborts -x` | ❌ Wave 0 |
| FR-4.2 | `/v2` 422 on missing native field; v1 schemas unchanged | unit (mocked loader) | `pytest tests/test_api_v2.py -x` | ❌ Wave 0 |
| Adapter isolation | `api/` never imports `harmonize_v9` | unit (import scan) | `pytest tests/test_compare.py::test_adapter_not_served -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** quick run command
- **Per wave merge:** full suite (`-v`), must stay 45+ green
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_train_nhanes.py` — synthetic NHANES-native fixture (labs + demographics + derived-like label, quarantine cols present to test the abort), 9-config smoke
- [ ] `tests/test_evaluate_nhanes.py` — CV aggregation, strict-max, paired-bootstrap determinism (seed 42 → identical CI reruns)
- [ ] `tests/test_compare.py` — harmonization adapter mapping, same-rows enforcement, adapter-import ban
- [ ] `tests/test_api_v2.py` — native schemas + `/v2` routes with mocked dual-slot loader, `tmp_path` isolation (never real `mlruns/` or Postgres — established convention)
- [ ] Human checkpoint: Q1 merge decision with SEQN-overlap counts before feature-list lock

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Local research API; no auth layer in scope (unchanged from v1) |
| V3 Session Management | No | Stateless prediction endpoints |
| V4 Access Control | No | No multi-tenant paths |
| V5 Input Validation | Yes | Pydantic-strict `CKDRequestNative` (mirror v1 422 fail-closed); allow-listed native columns; quarantine hard-abort |
| V6 Cryptography | No | No secrets in scope; `DATABASE_URL` never logged (established `db.py` rule carries to v2) |

### Known Threat Patterns for sklearn/FastAPI/MLflow-file-store

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Label-signal leakage via quarantine cols | Tampering (integrity) | Allow-list + abort gate (Pitfall 4); circularity audit on feature change |
| Training-serving skew (native vs harmonized) | Tampering | Adapter is eval-only, import-banned from `api/`; width assert on native pipeline at v2 startup |
| Silent metric misrepresentation | Repudiation | D-08 disclosure string attached to every logged/reported metric; unweighted/internal-only labels |

## Project Constraints (from codebase docs; no AGENTS.md found)

- `def main()` + `if __name__ == "__main__"`, invoked as `python -m ...` (CONVENTIONS.md)
- Config-driven via `load_config()` deepcopy — additive `data.nhanes_*` / `api.v2_*` keys only (CONVENTIONS.md)
- Loguru via `get_logger()`; dual sink stderr + rotating file (CONVENTIONS.md)
- Fail closed everywhere (422/503/500 patterns); immutable inputs (`df.copy()`); warning-not-crash on unexpected columns (CONVENTIONS.md + api/app.py)
- Synthetic-data pytest, `tmp_path` isolation; never touch real `mlruns/` or Postgres in tests (TESTING.md + CONTEXT.md)
- No new dependencies without need — venv already holds the full stack (STACK.md)

## Sources

### Primary (HIGH confidence)
- In-repo source read this session: `src/training/train.py`, `src/training/train_mlp.py`, `src/evaluation/evaluate.py`, `src/preprocessing/preprocess.py` (partial), `api/app.py` (partial), `api/model_loader.py` (partial), `config/config.yaml`, `data/nhanes/NHANES_PROTOCOL.md`, `.planning/*` docs
- Live CSV/XPT probes this session: 78-column dump, 5,343×78 shape, 17.31% CKD rate, missingness profile, quarantine-column presence, BMX/BPXO/DIQ/MCQ shapes via `read_sas`
- venv import probe: sklearn 1.9.1, mlflow 3.16.1, numpy 2.4.6, scipy 1.17.1, pandas 3.0.6; pytest 45 passed
- sklearn `cross_val_predict` + stratification docs — scikit-learn.org/stable
- MLflow Model Registry (aliases, champion pattern) — mlflow.org/docs/latest/ml/model-registry

### Secondary (MEDIUM confidence)
- CDC NHANES Weighting Tutorial (MEC weight requirement) — wwwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx
- SaML 2026 scoping review (survey-aware ML disclosure bar) — proceedings.mlr.press/v333/oh26a.html
- pROC `ci.auc` convention (2000 stratified bootstraps) — search.r-project.org/CRAN/refmans/pROC
- Demler et al. 2012 (DeLong misuse for nested models) — pubmed.ncbi.nlm.nih.gov/22415937
- Williams et al. 2020 (NHANES-III ML precedent ignoring weights) — ww2.amstat.org proceedings

### Tertiary (LOW confidence)
- NHANES item-code semantics (DIQ010, MCQ035, BMXBMI, BPXOSY1) — assumed from training knowledge, flagged A1/A2 for CDC-doc verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all versions import-verified in venv; zero new installs
- Architecture: HIGH - generalizes proven Phase 1–3 modules; only 4 genuinely new components
- Pitfalls: HIGH - CSV/XPT reality probed live; D-01 gap and Option-B trap are evidence-backed
- Comparison protocol: MEDIUM - paired harmonized design is sound and standard, but A1 mapping verification is pending

**Research date:** 2026-10-15
**Valid until:** 2026-11-14 (stable domain; sklearn/MLflow APIs pinned in venv)
