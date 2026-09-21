---
status: testing
phase: 02-model-training-experiment-tracking
source: [02-VERIFICATION.md]
started: 2026-09-21
updated: 2026-09-21
---

## Current Test

number: 1
name: MLflow UI — 9 runs with metrics + artifacts
expected: |
  Experiment `corvus-ckd` shows all 9 configs (lr, decision-tree, random-forest,
  gradient-boosting, xgboost, lightgbm, mlp-sigmoid, mlp-tanh, mlp-relu), each run
  with accuracy/precision/recall/f1/roc_auc metrics plus the preprocessing-pipeline
  artifact and the linked model.
awaiting: user response

## Tests

### 1. MLflow UI — 9 runs with metrics + artifacts
expected: Run `mlflow ui --backend-store-uri mlruns` (or open the tracking UI) on experiment `corvus-ckd`; all 9 runs visible, each with the 5 metrics and both artifacts (preprocessing pipeline + model).
result: [pending]

### 2. Registry Models tab — v9 Staging
expected: Registered model `corvus-ckd` shows v9 (mlp-relu) in Staging, v1–v8 Archived, nothing in Production.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
