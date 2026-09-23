---
phase: "3"
slug: "prediction-api-containerization"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-21"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none — default discovery over `tests/` |
| **Quick run command** | `.\venv\python.exe -m pytest tests -q` |
| **Full suite command** | `.\venv\python.exe -m pytest tests -q` |
| **Estimated runtime** | ~90 seconds (Phase 1+2 suites included) |

---

## Sampling Rate

- **After every task commit:** Run `.\venv\python.exe -m pytest tests -q`
- **After every plan wave:** Run `.\venv\python.exe -m pytest tests -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-* | 01 | 1 | FR-4.1, FR-4.2 | — | /predict validates 24 fields, rejects bad with 422 | unit (TestClient, no server) | `.\venv\python.exe -m pytest tests/test_api.py -q` | ❌ W0 | ⬜ pending |
| 03-01-* | 01 | 1 | FR-4.3, FR-4.4 | — | Every response carries model_version pinned at startup (D-02 deviation from per-request noted) | unit (TestClient) | `.\venv\python.exe -m pytest tests/test_api.py -q -k version` | ❌ W0 | ⬜ pending |
| 03-02-* | 02 | 2 | FR-5.1, FR-5.2 | — | Compose builds; prediction log row has full record incl. model_version | integration (compose + Postgres) | `docker compose -f docker/docker-compose.yml up -d --build` then API checks | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Planner refines this map with concrete task IDs during planning.*

---

## Wave 0 Requirements

- [ ] `tests/test_api.py` — stubs for FR-4.1–FR-4.4 (FastAPI TestClient, synthetic 24-field fixtures from test_raw.csv shape, never a live server or real Postgres)
- [ ] `tests/conftest.py` — extend with API fixtures (TestClient app with tmp tracking store, pinned test version)
- [ ] `pip install psycopg2-binary streamlit python-multipart` — human-verified installs (RESEARCH-flagged)

*Planner creates Wave 0 stubs before implementation tasks.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docker compose up` serves predictions end-to-end | FR-5.1 | Container orchestration can't be asserted by pytest | `docker compose -f docker/docker-compose.yml up -d --build`; `POST /predict` returns prediction + model_version; `GET /health` 200 |
| Streamlit UI predicts from a form + CSV | FR-4.1 (frontend) | Browser interaction can't be asserted by pytest | `streamlit run frontend/app.py`; fill 24 fields, submit, confirm prediction + version; upload CSV, confirm batch table |
| v9 serving Production traffic | FR-4.4, D-01 | Human promotion gate | Registry Models tab: v9 Production; `/model_info` reports v9 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
