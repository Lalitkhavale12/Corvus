---
phase: "2"
slug: "model-training-experiment-tracking"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-21"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none — default discovery over `tests/` |
| **Quick run command** | `.\venv\python.exe -m pytest tests -q` |
| **Full suite command** | `.\venv\python.exe -m pytest tests -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.\venv\python.exe -m pytest tests -q`
- **After every plan wave:** Run `.\venv\python.exe -m pytest tests -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-* | 01 | 1 | FR-2.1–FR-2.5 | — | Training envelope: fit on train-raw only, no transformed-CSV input | unit/integration | `.\venv\python.exe -m pytest tests/test_training.py -q` | ❌ W0 | ⬜ pending |
| 02-01-* | 01 | 1 | FR-2.3 | — | Every MLflow run carries pipeline + model artifacts (Claim 2) | integration | `.\venv\python.exe -m pytest tests/test_training.py -q -k claim2` | ❌ W0 | ⬜ pending |
| 02-02-* | 02 | 2 | FR-3.1–FR-3.3 | — | Registry versions resolve; winner in Staging | integration | `.\venv\python.exe -m pytest tests/test_registry.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Planner refines this map with concrete task IDs during planning.*

---

## Wave 0 Requirements

- [ ] `tests/test_training.py` — stubs for FR-2.1–FR-2.5 (synthetic data, tmp MLflow tracking dir)
- [ ] `tests/test_registry.py` — stubs for FR-3.1–FR-3.3 (tmp tracking dir, no production registry writes)
- [ ] `tests/conftest.py` — shared fixtures (synthetic CKD frame, isolated tracking URI)

*Planner creates Wave 0 stubs before implementation tasks.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MLflow UI shows 9 runs with metrics + artifacts under experiment `corvus-ckd` | FR-2.2, FR-2.3 | UI rendering can't be asserted by pytest | `mlflow ui --backend-store-uri mlruns`, open http://localhost:5000, confirm 9 runs, params, metrics, 2 artifacts per run |
| Registry shows versioned models, winner in Staging | FR-3.1–FR-3.3 | Registry stage transitions confirmed visually | Same UI → Models tab: versions listed, winner stage = Staging |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
