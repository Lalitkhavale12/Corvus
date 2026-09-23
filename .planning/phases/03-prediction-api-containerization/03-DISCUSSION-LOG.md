# Phase 3: Prediction API + Containerization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-21
**Phase:** 3-Prediction API + Containerization
**Areas discussed:** Production promotion, Prediction-log store, Input schema breadth, Batch input shape

---

## Production promotion

| Option | Description | Selected |
|--------|-------------|----------|
| Promote v9 now | You approve, Phase 3 opens by transitioning v9 Staging→Production. The human gate from Phase 2 pays off; API resolves Production from day one. | ✓ |
| Serve from Staging | API serves whatever is in Staging until you say otherwise. Fewer steps, but Staging becomes de-facto prod. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Resolve per request | API resolves the Production version on every request. Registry is source of truth; no restarts for swaps. | |
| Pin at startup | Version pinned at startup via config/env. Simpler and faster, but model swaps need restarts. | ✓ |

**User's choice:** Promote v9 now; Pin at startup
**Notes:** User overrode the per-request recommendation — accepted trade-off recorded in CONTEXT.md D-02.

---

## Prediction-log store

| Option | Description | Selected |
|--------|-------------|----------|
| Postgres in Compose | Compose runs Postgres; API logs there when DATABASE_URL points at it. Full ROADMAP story. | ✓ |
| SQLite fallback locally | Local database file when Postgres unreachable. Two backends to maintain. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Full record | Request fields + prediction + probability + model_version + timestamp. Fuel for Phases 4-5. | ✓ |
| Minimal record | Prediction + model_version + timestamp only. Starves later drift analysis. | |

**User's choice:** Postgres in Compose; Full record
**Notes:** Verified Docker v29.6.2 + Compose v5.3.1 available on this machine before asking.

---

## Input schema breadth

| Option | Description | Selected |
|--------|-------------|----------|
| All 24, impute gaps | Every request carries all 24 fields; pipeline imputes missing. Matches training exactly. | ✓ |
| Required core + optional | Small required core, rest optional. Friendlier form, serve-train skew risk. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Strict, reject fast | Bad values get a clear 422 before inference. Same fail-closed instinct as GX gate. | ✓ |
| Lenient coercion | Coerce what's coercible. Friendlier, more code paths. | |

**User's choice:** All 24, impute gaps; Strict, reject fast
**Notes:** None

---

## Batch input shape

| Option | Description | Selected |
|--------|-------------|----------|
| CSV upload | Client uploads CSV with 24 columns; server parses per row. Matches how users hold data. | ✓ |
| JSON array | POST a JSON array of records. Cleaner semantics, heavier payloads. | |

| Option | Description | Selected |
|--------|-------------|----------|
| All-or-nothing | One bad row rejects the whole batch with the row number. Atomic, simple. | ✓ |
| Per-row errors | Valid rows predict, bad rows return errors. Partial-success bookkeeping. | |

**User's choice:** CSV upload; All-or-nothing
**Notes:** None

---

## the agent's Discretion

None — user decided every area directly.

## Deferred Ideas

None.
