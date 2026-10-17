---
status: passed
phase: 07-nhanes-native-retrain
source: [07-VERIFICATION.md]
started: 2026-10-10
updated: 2026-10-17
---

## Current Test

number: 1
name: Live /v2 prediction (deployed env)
expected: |
  Against a deployed stack with Postgres: POST a native NHANES row to
  /v2/predict with MODEL_VERSION_V2=11 — expect 200, model_version "11",
  and one row in predictions_v2.
awaiting: user response

## Tests

### 1. Live /v2 prediction (deployed env)
expected: /v2/predict returns version-stamped prediction and logs to predictions_v2 in a deployed environment.
result: [passed] POST /v2/predict → 200 {"prediction":1,"probability":0.892,"model_version":"11"} on deployed stack with MODEL_VERSION_V2=11

### 2. Registry Models tab
expected: Models tab shows v11 Production, v9 (+v1–v8, v10) Archived — 11 versions total, zero deletions.
result: [passed] MLflow API: v1–v10 Archived, v11 Production; 11 versions total, zero deletions

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
