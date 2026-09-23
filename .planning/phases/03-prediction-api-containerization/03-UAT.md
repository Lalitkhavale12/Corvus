---
status: testing
phase: 03-prediction-api-containerization
source: [03-VERIFICATION.md]
started: 2026-09-21
updated: 2026-09-21
---

## Current Test

number: 1
name: Compose-up live prediction
expected: |
  From PROJECT_ROOT: sync mlruns for the container, `docker compose -f
  docker/docker-compose.yml up -d --build`, then GET /health, GET /model_info,
  POST /predict return version 9; one timestamped row in the Postgres
  predictions table; `docker compose down` leaves zero containers.
awaiting: user response

## Tests

### 1. Compose-up live prediction
expected: Compose stack serves versioned predictions end-to-end (all version 9, one timestamped Postgres row, zero containers after down).
result: [pending]

### 2. Streamlit UI in a browser
expected: `streamlit run frontend/app.py` against the live stack — form predicts with versioned results, CSV upload works, 422s surface cleanly, disconnect names API_URL.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
