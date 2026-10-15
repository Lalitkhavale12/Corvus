# Phase 7: NHANES Native Retrain - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-10
**Phase:** 7-NHANES Native Retrain
**Areas discussed:** Native feature set, Challenger promotion rule, API schema evolution, Validation design

---

## Native feature set

| Option | Description | Selected |
|--------|-------------|----------|
| Full mapped set | 14 mapped labs/vitals + demographics/comorbidities. Everything NHANES honestly offers. | ✓ |
| Clinical core only | Labs + vitals + age/sex only. Leaner, discards socioeconomic signal. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Ignore weights | Standard ML practice; model serves individuals. | ✓ |
| Use survey weights | Population-representative fitting; engineering-heavy. | |

**User's choice:** Full mapped set; Ignore weights
**Notes:** None

---

## Challenger promotion rule

| Option | Description | Selected |
|--------|-------------|----------|
| Beat v9 on holdout | Strictly exceeds v9's holdout ROC-AUC under the same protocol. | ✓ |
| Standalone merit bar | Wins on own CV merits regardless of v9. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Human gate | Code proposes, user disposes. | ✓ |
| Auto-promote | Executes on rule fire, no eyes. | |

**User's choice:** Beat v9 on holdout; Human gate
**Notes:** Orchestrator flagged for planning: cross-schema comparison protocol open (v9 can't natively read NHANES rows); recorded in CONTEXT.md, not re-asked.

---

## API schema evolution

| Option | Description | Selected |
|--------|-------------|----------|
| /v2 endpoints | New routes on native schema; v1 untouched until promotion. | ✓ |
| Extended union schema | One schema, union of fields; muddier validation. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Hard cutover | Pin flips at promotion; zero unversioned traffic. | ✓ |
| Shadow/canary traffic | Live comparison routing; needs splitting machinery. | |

**User's choice:** /v2 endpoints; Hard cutover
**Notes:** None

---

## Validation design

| Option | Description | Selected |
|--------|-------------|----------|
| CV + CIs + holdout | 5-fold CV with bootstrapped CIs + locked 20% holdout, internal-only honesty. | ✓ |
| Internal temporal split | Train/validate across cycles; stronger flavor, smaller train set. | |

| Option | Description | Selected |
|--------|-------------|----------|
| Disclose always | Derived labels disclosed next to every metric, forever. | ✓ |
| Accept as truth | Report derived labels as ground truth post-audit. | |

**User's choice:** CV + CIs + holdout; Disclose always
**Notes:** None

---

## the agent's Discretion

None — user decided every area directly.

## Deferred Ideas

None.
