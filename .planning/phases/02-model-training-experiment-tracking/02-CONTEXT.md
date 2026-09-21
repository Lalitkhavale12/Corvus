# Phase 2: Model Training + Experiment Tracking - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

## Phase Boundary

Train 9 model configs (LR, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM, MLP×3 activations) on the 279-row training split, log metrics + artifacts to MLflow, select the winner by test ROC-AUC, and register models in the MLflow Registry. Training MUST consume the `*_raw.csv` splits through `preprocessing_pipeline.joblib` as the input step (Claim 2 contract locked in Phase 1 fixes) — never train directly on the transformed CSVs.

## Implementation Decisions

### Model lineup + tuning
- **D-01:** Train the full slate: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM, plus MLP with Sigmoid / Tanh / ReLU as three separate runs (9 configs total).
- **D-02:** Hyperparameters are library defaults with fixed seeds (`random_state=42` family) plus one documented rationale per choice. No grid search — at n=279, grids mostly fit noise.

### Best-model criterion
- **D-03:** Winner = highest test-split ROC-AUC, strict ranking, no tie-break logic. Exactly as FR-2.4 scopes.

### MLP configuration
- **D-04:** Single small hidden layer (e.g. 50 units); the three runs differ only in activation. Right-sized for 279 rows so runs stay comparable.
- **D-05:** Fixed `max_iter` budget with seeded runs; no early stopping (the 40-row val split is too noisy a stopping signal, and it avoids val-set peeking).

### Registry promotion
- **D-06:** Every training run registers its model as a new version; the winner is registered to **Staging**. Promotion to Production is a separate explicit step (supports the FR-3.3 promote/demote story and gives a human approval gate).
- **D-07:** Superseded versions move to Archived as new winners arrive (FR-9.4 retention habit starts here).

### the agent's Discretion
None — the user decided every area directly. Planner has flexibility only on code organization (module split between `train.py` / `train_mlp.py` / `evaluate.py`), MLflow run naming, and test design.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements + roadmap
- `.planning/REQUIREMENTS.md` FR-2.1 → FR-2.5, FR-3.1 → FR-3.3 — training/tracking/registry requirements and acceptance tests
- `.planning/ROADMAP.md` Phase 2 section — tasks, deliverables, Claim 2 completion note

### Phase 1 contracts (must not be broken)
- `src/preprocessing/preprocess.py` — `save_outputs()` training-input contract: train from `*_raw.csv` via the pipeline; `__source_row` / `__source_id` are metadata, excluded from features
- `config/config.yaml` — `data.numeric_cols` / `data.categorical_cols`, `split.*`, `mlflow.tracking_uri`, `mlflow.experiment_name`
- `data/processed/train_raw.csv`, `data/processed/val_raw.csv`, `data/processed/test_raw.csv` — Phase 2 training inputs
- `data/processed/preprocessing_pipeline.joblib` — fitted pipeline to log per run (Claim 2)

## Existing Code Insights

### Reusable Assets
- `src/utils/config.py:load_config()` — returns a caller-owned deepcopy; read column lists, split config, and MLflow settings through it
- `src/utils/logger.py:get_logger()` — module-level `log = get_logger()`, Loguru to stderr + rotating file
- `src/validation/validate.py:run_raw_validation()` — gate pattern (fail-closed) if training needs an input sanity check
- `tests/` synthetic-fixture pattern — 40-row CKD-shaped frames, `tmp_path` isolation, never touch real data files

### Established Patterns
- `def main()` + `if __name__ == "__main__"` entry points, invoked as `python -m src.training.train`
- Config-driven everything; no hardcoded paths/ratios/strategies in module bodies
- Immutable DataFrame inputs (`df.copy()`), warning-not-crash on unexpected columns

### Integration Points
- `src/training/train.py` + `src/training/train_mlp.py` read `data/processed/*_raw.csv`, fit the loaded pipeline on train-raw only, log to MLflow experiment `corvus-ckd` under `mlruns/`
- `src/evaluation/evaluate.py` computes accuracy, precision, recall, F1, ROC-AUC per model from MLflow runs or CSV predictions
- `models/` + MLflow Registry (Staging → Production → Archived) receive the winner; Phase 3 API resolves Production from the Registry

## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

## Deferred Ideas

None — discussion stayed within phase scope

---

*Phase: 2-Model Training + Experiment Tracking*
*Context gathered: 2026-09-21*
