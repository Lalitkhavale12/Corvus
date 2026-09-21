# Phase 2: Model Training + Experiment Tracking - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-21
**Phase:** 2-Model Training + Experiment Tracking
**Areas discussed:** Model lineup + tuning, Best-model criterion, MLP configuration, Registry promotion

---

## Model lineup + tuning

| Option | Description | Selected |
|--------|-------------|----------|
| Full slate, 9 configs | LR, Decision Tree, Random Forest, Gradient Boosting, XGBoost, LightGBM + MLP×3 as ROADMAP scopes. Broadest comparison story for the academic write-up. | ✓ |
| Trimmed, 7 configs | Drop Decision Tree + Gradient Boosting — Random Forest, XGBoost and LightGBM already cover tree ensembles. 7 configs, less redundancy. | |
| You decide | You decide the final slate during planning. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Defaults + seeds | Fixed seeds, library defaults, one documented rationale per choice. Fastest, reproducible, defensible on 279 rows where grids mostly fit noise. | ✓ |
| Light manual grid | Small hand-picked grids with val-set selection. More code, more runs, marginal gain at this n. | |
| You decide | You decide tuning depth during planning. | |

**User's choice:** Full slate, 9 configs; Defaults + seeds
**Notes:** None

---

## Best-model criterion

| Option | Description | Selected |
|--------|-------------|----------|
| Pure ROC-AUC | Winner = highest ROC-AUC, exactly as ROADMAP/FR-2.4 scopes. Simplest story, matches requirements verbatim. | ✓ |
| ROC-AUC + recall floor | Winner = highest ROC-AUC among models with recall >= 0.85. Clinically defensible — a CKD screen that misses cases is a failed screen. | |
| You decide | You decide the selection rule during planning. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Strict ranking | Highest ROC-AUC wins outright; others ranked behind. Deterministic, no judgment calls in code. | ✓ |
| Epsilon tie-break | If top models are within 0.01 ROC-AUC, prefer the simpler one. Production-grade tie-break. | |
| You decide | You decide tie-breaking during planning. | |

**User's choice:** Pure ROC-AUC; Strict ranking
**Notes:** None

---

## MLP configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Single layer, 3 activations | One small hidden layer (e.g. 50 units), three runs differing only in activation. Right-sized for 279 rows; each run stays comparable. | ✓ |
| Two layers | Two-layer network (e.g. 100→50) × 3 activations. More capacity than 279 rows can justify — overfit risk. | |
| You decide | You decide the architecture during planning. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed budget, no early stop | Fixed max_iter with a set seed and StandardScaler already in the pipeline. Deterministic, reproducible, no val-set peeking. | ✓ |
| Early stopping on val | Stop on the 40-row val split. Noisy signal at n=40 — stopping point is mostly luck. | |

**User's choice:** Single layer, 3 activations; Fixed budget, no early stop
**Notes:** None

---

## Registry promotion

| Option | Description | Selected |
|--------|-------------|----------|
| Staging + explicit promote | Winner registered to Staging; a separate explicit step promotes to Production. Real MLOps gate, human approval point, matches FR-3.3 story. | ✓ |
| Auto-promote to Production | Winner goes straight to Production in the training script. Simpler, but no approval gate and a weaker registry story. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Version every run | Each training run registers its model version; superseded versions move to Archived. Full version history visible in the Registry. | ✓ |
| Register winner only | Only the winning model is registered. Cleaner registry, but losing-run versions vanish. | |

**User's choice:** Staging + explicit promote; Version every run
**Notes:** None

---

## the agent's Discretion

None — user decided every area directly.

## Deferred Ideas

None.
