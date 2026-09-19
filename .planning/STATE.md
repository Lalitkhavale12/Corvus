# Project State — Corvus

> Auto-maintained by GSD workflow

## Current Position

- **Milestone**: M1 (Initial Build)
- **Active Phase**: Phase 1 — Data Pipeline (in progress)
- **Next Phase**: Phase 2 — Model Training + Experiment Tracking
- **Blocked**: Nothing

## Phase Status

| Phase | Status | Last Updated |
|---|---|---|
| 1 — Data Pipeline | 🔄 In Progress | 2026-09-19 |
| 2 — Model Training | ⬜ Not Started | — |
| 3 — API + Containers | ⬜ Not Started | — |
| 4 — CI/CD + Monitoring | ⬜ Not Started | — |
| 5 — Drift + Retraining | ⬜ Not Started | — |
| 6 — Visualization + Polish | ⬜ Not Started | — |

## Completed Work

### Phase 1 (partial)
- ✅ Raw data ingestion with UCI CKD quirk handling
- ✅ Leak-safe preprocessing (split-first, fit on train only)
- ✅ Single sklearn Pipeline artifact (Patent Claim 2 — object created)
- ✅ Config-driven pipeline (`config/config.yaml`)
- ✅ Centralized Loguru logging
- ✅ 4 pytest tests passing
- ✅ Codebase mapped (`.planning/codebase/`)
- ✅ Project initialized (`.planning/`)

## Decisions Log

| # | Decision | Date | Rationale |
|---|---|---|---|
| D1 | UCI-336 as primary dataset | 2026-09-19 | Real clinical data with documented provenance |
| D2 | UCI-857 for drift simulation | 2026-09-19 | Independent cohort, confirmed valid |
| D3 | Kubernetes cut | 2026-09-19 | Docker Compose sufficient for academic demo |
| D4 | React → Streamlit | 2026-09-19 | Single Python file, no frontend build |
| D5 | Synthetic datasets rejected | 2026-09-19 | Leaky labels, circular labeling |
| D6 | Abu Dhabi EHR deferred | 2026-09-19 | Different modeling paradigm (survival analysis) |

## Open Questions

1. Claims 1 and 3 — full text not yet shared, cannot assess compliance
2. Abu Dhabi EHR file — defer to stretch goal or integrate into core?

## Context for Next Session

Start with `/gsd-plan-phase 1` to complete remaining Phase 1 work (EDA, Great Expectations, test coverage), then `/gsd-plan-phase 2` to begin model training.
