# Phase 7: NHANES Native Retrain - Context

**Gathered:** 2026-10-10
**Status:** Ready for planning

## Phase Boundary

Train 9 model configs on NHANES-native features from 5,343 derived rows, validate with CV + CIs + locked holdout, register challenger versions, promote iff the challenger beats v9 under the locked rule at a human gate, and serve the winner on new `/v2` endpoints while v9 keeps serving v1 until cutover. No 24-field forcing — the native schema is the honest one.

## Implementation Decisions

### Native feature set
- **D-01:** Full mapped set: 14 labs/vitals (BUN, glucose, Na/K/Ca/P, bicarbonate, HGB, HCT, WBC, RBC, BP, BMI, age) + sex/ethnicity/income/education + diabetes/hypertension flags. Quarantine (creatinine/eGFR/ACR + 7 derived columns) stays banned.
- **D-02:** Survey weights ignored in training (ML convention; model serves individuals).

### Challenger promotion rule
- **D-03:** Challenger dethrones v9 iff its holdout ROC-AUC strictly exceeds v9's under the same protocol. Open protocol detail for planning: v9 cannot natively read NHANES rows (10 absent fields), so the comparison protocol (e.g. v9 on imputed-harmonized holdout vs challenger native, or vs v9's recorded 1.0 with documented handicap) must be designed by research/planning — not assumed.
- **D-04:** Human gate approves any Production promotion. No auto-promote, ever.

### API schema evolution
- **D-05:** New `/v2/predict` + `/v2/batch_predict` on the native schema; v1 untouched until promotion, then explicit traffic move.
- **D-06:** Hard cutover at promotion (pin flips). No shadow/canary machinery.

### Validation design
- **D-07:** Stratified 5-fold CV with bootstrapped CIs on all 5,343 rows + one locked 20% holdout scored once. Internal-only; reported as such.
- **D-08:** Derived labels are disclosed as derived next to every metric, forever. Never presented as diagnosed truth.

### the agent's Discretion
None — the user decided every area directly. Planner has flexibility only on module layout, run naming, and test design.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements + roadmap
- `.planning/REQUIREMENTS.md` FR-2.1 → FR-2.5, FR-3.1 → FR-3.3, FR-4.1 → FR-4.4 (training/tracking/registry/API requirements carry over; new REQ-IDs for v2 endpoints expected from planning)
- `.planning/ROADMAP.md` Phase 7 section — tasks, deliverables, UCI-857 replanning note for Phase 5

### Data contracts (must not be broken)
- `data/nhanes/NHANES_PROTOCOL.md` — derivation rule, 10-column quarantine, 3 audit gates (all passed 2026-10-10)
- `data/nhanes/nhanes_ckd_derived.csv` — 5,343 × 78, the training source; never re-derive casually
- `dataset_requirements.md` — vetting bar that selected this cohort; Blocks 1–6 still bind
- MLflow Registry `corvus-ckd`: v9 Production (champion), v1–v8 Archived; challenger versions append, never overwrite

## Existing Code Insights

### Reusable Assets
- `src/training/train.py:run_experiment()` — per-run shape (raw→pipeline→fit→log Claim-2 run) to generalize for the native schema
- `src/training/train_mlp.py` — MLP activation pattern for the native configs
- `src/evaluation/evaluate.py` — strict-max ranking + stage transitions to extend with CV/CIs + challenger comparison
- `api/app.py` — route/validation/logging patterns for `/v2` endpoints; `api/model_loader.py` pinned-version pattern for the second serving slot
- `tests/` synthetic-fixture + `tmp_path` isolation; never touch real `mlruns/` or Postgres in tests

### Established Patterns
- `def main()` + `if __name__ == "__main__"`, `python -m ...` entry points
- Config-driven via `load_config()` deepcopy; new `data.nhanes_*` / `api.v2_*` keys extend `config.yaml`
- Fail closed everywhere; immutable inputs; warning-not-crash on unexpected columns

### Integration Points
- New native pipeline artifact + challenger runs under experiment `corvus-ckd` (or a named successor experiment — planner decides, registry continuity preserved either way)
- `/v2/*` routes read the native pipeline + promoted challenger; v1 routes untouched until the human gate flips the pin
- Phase 5 drift design must be replanned (UCI-857 disqualified) — out of scope here, flagged in ROADMAP

## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

## Deferred Ideas

None — discussion stayed within phase scope

---

*Phase: 7-NHANES Native Retrain*
*Context gathered: 2026-10-10*
