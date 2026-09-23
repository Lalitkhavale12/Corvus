---
phase: 03-prediction-api-containerization
plan: 01
subsystem: api
tags: [fastapi, mlflow, postgres, psycopg2, streamlit, model-registry]

# Dependency graph
requires:
  - phase: 02-model-training-experiment-tracking
    provides: corvus-ckd registry v1-v9 with v9 Staging winner (mlp-relu)
provides:
  - corvus-ckd v9 in Production stage (D-01 first act)
  - config api.* + db.* sections with pinned serving version (D-02)
  - three serving dependencies installed and pinned
  - Wave 0 fixtures + 8 red API contract stubs for 03-02
affects: [03-02 app endpoints, 03-03 batch logging, 03-04 compose frontend, phase-5 drift reads]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 2390
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: [psycopg2-binary 2.9.13, streamlit 1.64.0, python-multipart 0.0.32]
  patterns: [one-shot registry promotion script with main() -> int, startup-pinned serving version in config]

key-files:
  created: [scripts/promote_production.py, tests/test_api.py]
  modified: [requirements.txt, config/config.yaml, tests/conftest.py]

key-decisions:
  - "Promotion script hardcodes version 9 per plan; future version swaps go through config api.pinned_version + a new promotion run"
  - "config tracking_uri/database_url hold static fallbacks; runtime code reads MLFLOW_TRACKING_URI/DATABASE_URL env first (no second config mechanism)"
  - "Removed the stale commented streamlit pin from requirements.txt Later-phases section since it is now a real Phase 3 dependency"

patterns-established:
  - "Promotion scripts mirror evaluate.py apply_registry_stages call shape (transition_model_version_stage + archive_existing_versions)"
  - "Wave 0 stubs import the not-yet-existing app module so collection fails loudly until the implementing plan lands"

requirements-completed: [FR-4.4, FR-4.3]

# Coverage metadata (#1602) — drives DETERMINISTIC UAT routing in verify-work.
coverage:
  - id: D1
    description: "corvus-ckd v9 promoted Staging to Production via scripts/promote_production.py"
    requirement: "FR-4.4"
    verification:
      - kind: other
        ref: "venv/python.exe scripts/promote_production.py -> PROMOTED corvus-ckd version=9 stage=Production, exit 0; registry query shows v9 Production, v1-v8 Archived"
        status: pass
    human_judgment: false
  - id: D2
    description: "config.yaml carries api.* (model_name, pinned_version 9, tracking_uri) and db.* (database_url) sections loadable via load_config"
    requirement: "FR-4.4"
    verification:
      - kind: other
        ref: "load_config() returns api.model_name=corvus-ckd, api.pinned_version=9, db.database_url='' (checked 2026-09-23)"
        status: pass
    human_judgment: false
  - id: D3
    description: "psycopg2-binary, streamlit>=1.32, python-multipart installed (Task 1 human-approved) and pinned in requirements.txt under Phase 3 header"
    requirement: "FR-4.3"
    verification:
      - kind: other
        ref: "pip list shows psycopg2-binary 2.9.13, streamlit 1.64.0, python-multipart 0.0.32"
        status: pass
    human_judgment: false
  - id: D4
    description: "Existing suite green excluding the not-yet-created-then-red test_api.py (26 passed)"
    verification:
      - kind: unit
        ref: "venv/python.exe -m pytest tests -q --ignore=tests/test_api.py -> 26 passed"
        status: pass
    human_judgment: false
  - id: D5
    description: "Wave 0 fixtures (synthetic_ckd_request, synthetic_batch_csv) + 8 API contract stubs, red by design until 03-02"
    requirement: "FR-4.3"
    verification:
      - kind: unit
        ref: "venv/python.exe -m pytest tests/test_api.py -q -> collection ERROR naming api.app (ModuleNotFoundError: No module named 'api.app')"
        status: fail
    human_judgment: true
    rationale: "Red-by-design is the deliverable: verifier must confirm the failure is the missing api.app import, not broken assertions, before 03-02 turns it green"

# Metrics
duration: 8min
completed: 2026-09-23
status: complete
plan_head_before: 2f3e180f2fa5f138e3750006e6c026b1d0861504
---

# Phase 03 Plan 01: Foundation (Promotion + Config + Wave 0 Stubs) Summary

**corvus-ckd v9 promoted to Production, serving deps installed, startup-pinned config landed, 8 API contract stubs red and ready for 03-02**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-09-23T06:29:00Z
- **Completed:** 2026-09-23T06:36:38Z
- **Tasks:** 2 (Task 1 checkpoint pre-approved by human before this run)
- **Files modified:** 5

## Accomplishments

- corvus-ckd v9 serves from the Production stage (D-01 first act, verified live)
- API config carries pinned serving version 9 readable at startup via load_config (D-02)
- psycopg2-binary 2.9.13, streamlit 1.64.0, python-multipart 0.0.32 installed and pinned
- Wave 0 fixtures + 8 API stubs exist and are red until 03-02 implements the endpoints
- Existing suite green: 26 passed, 0 failed

## Task Commits

Each task was committed atomically:

1. **Task 2: Install deps, extend config, promote v9 to Production** - `0303f59` (feat)
2. **Task 3: Land Wave 0 fixtures and red API stubs** - `c21f4b7` (test)

**Plan metadata:** `2f3e180` (docs: create phase plan, pre-existing)

## Files Created/Modified

- `scripts/promote_production.py` - One-shot v9 Staging to Production promotion (REGISTERED_MODEL_NAME, main() -> int, PROMOTED/PROMOTION ERROR prints)
- `config/config.yaml` - api.* (model_name, pinned_version "9", tracking_uri) + db.* (database_url "") sections
- `requirements.txt` - API header fixed Phase 4 to Phase 3; three serving pins added; stale commented streamlit line removed
- `tests/conftest.py` - synthetic_ckd_request (24 fields, rc None) + synthetic_batch_csv (3 valid rows) fixtures
- `tests/test_api.py` - 8 contract stubs (predict/versioned, 422s, imputer path, health, model_info, batch all-or-nothing, Claim 4 log row)

## Decisions Made

- Promotion script hardcodes version 9 per plan; future swaps go through config api.pinned_version plus a new promotion run.
- Static YAML holds env fallbacks only; runtime code reads MLFLOW_TRACKING_URI / DATABASE_URL first — load_config stays the only config mechanism.
- Removed the stale `# streamlit>=1.32 # Phase 4/9: frontend` comment since streamlit is now a real Phase 3 pin.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added sys.path project-root bootstrap to scripts/promote_production.py**
- **Found during:** Task 2 (promotion script run)
- **Issue:** Plan's run command `.\venv\python.exe scripts/promote_production.py` fails with ModuleNotFoundError: No module named 'src' — plain-script runs don't put the repo root on sys.path (unlike `python -m` used by evaluate.py).
- **Fix:** Three-line `sys.path.insert(0, <script-parent>)` bootstrap before the src imports.
- **Files modified:** scripts/promote_production.py
- **Verification:** Script exits 0 with the PROMOTED line; registry confirms v9 Production.
- **Committed in:** 0303f59 (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to run the plan-specified command verbatim. No scope creep.

## Issues Encountered

- PowerShell 5.1 rejects `&&` chaining and mangles nested-quote `python -c` invocations — worked around with `;` separators, `$env:PYTHONPATH`, and temp check scripts under AppData Temp. No plan impact.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-02 unblocked: v9 Production serving source exists, pinned version readable, 8 failing stubs define the endpoint contract.
- Watch item for 03-02: test 8 patches `api.db.Session` — adjust the patch target if the real session factory lives elsewhere.
- Watch item for 03-04: streamlit install downgraded websockets 17.1 to 16.1.1 (streamlit 1.64.0 pin) — verify no conflict with other consumers.

## Self-Check: PASSED

- FOUND: scripts/promote_production.py, tests/test_api.py, config/config.yaml, requirements.txt, tests/conftest.py
- FOUND: 0303f59, c21f4b7 (git log)
- Suite: 26 passed excluding test_api.py; test_api.py red with collection error naming api.app; 5 model_version hits in stubs

---
*Phase: 03-prediction-api-containerization*
*Completed: 2026-09-23*
