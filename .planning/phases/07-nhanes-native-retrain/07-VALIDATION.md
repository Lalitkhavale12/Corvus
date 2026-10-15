---
phase: "7"
slug: "nhanes-native-retrain"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-10"
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none — default discovery over `tests/` |
| **Quick run command** | `.\venv\python.exe -m pytest tests -q` |
| **Full suite command** | `.\venv\python.exe -m pytest tests -q` |
| **Estimated runtime** | ~120 seconds (45 existing + new suites) |

---

## Sampling Rate

- **After every task commit:** Run `.\venv\python.exe -m pytest tests -q`
- **After every plan wave:** Run `.\venv\python.exe -m pytest tests -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-* | 01 | 1 | FR-2.1–FR-2.4 | — | Native feature builder drops all 11 quarantined names; holdout indices disjoint | unit (synthetic NHANES-shaped frames) | `.\venv\python.exe -m pytest tests/test_nhanes_training.py -q` | ❌ W0 | ⬜ pending |
| 07-0*-* | * | * | FR-2.3 | — | Every challenger run carries native pipeline + model (Claim 2, second cohort) | integration (tmp tracking URI) | `.\venv\python.exe -m pytest tests/test_nhanes_training.py -q -k claim2` | ❌ W0 | ⬜ pending |
| 07-0*-* | * | * | FR-3.1–FR-3.3, FR-4.1–FR-4.3 | — | /v2 routes version-stamped; v1 routes byte-identical behavior | unit (TestClient) | `.\venv\python.exe -m pytest tests/test_api_v2.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Planner refines this map with concrete task IDs during planning.*

---

## Wave 0 Requirements

- [ ] `tests/test_nhanes_training.py` — stubs (quarantine enforcement, native pipeline shape, Claim-2 run artifacts on tmp tracking URI)
- [ ] `tests/test_api_v2.py` — stubs (/v2 predict/batch/version behavior on TestClient, v1 regression)
- [ ] `tests/conftest.py` — extend with NHANES-shaped synthetic fixtures (never the real derived CSV)

*Planner creates Wave 0 stubs before implementation tasks.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Challenger beats v9 → human promotion → /v2 serves new version | D-03, D-04 | Human gate is a human decision | Registry Models tab: new versions, promotion on approval; `/v2/model_info` reports challenger |
| v1 still serves v9 after /v2 lands | D-05, D-06 | Cross-version coexistence eyeball check | `/predict` returns v9-stamped answers while `/v2/predict` serves challenger |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
