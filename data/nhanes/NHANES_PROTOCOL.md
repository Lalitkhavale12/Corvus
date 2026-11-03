# NHANES Derivation + Quarantine Protocol (v1 — AWAITING APPROVAL)

> Status: PROPOSED, not approved. No labels derived until the user approves
> this exact text. Written 2026-10-10, Corvus data track.

## Source files (all CDC NHANES 2021–2023, public, in `data/nhanes/`)

| File | Rows | Role |
|---|---|---|
| `DEMO_L.xpt` | 11,933 | Age, sex (eGFR inputs), survey weights |
| `BIOPRO_L.xpt` | 7,199 | Serum creatinine `LBXSCR` (eGFR input), BUN, glucose, electrolytes |
| `ALB_CR_L.xpt` | 8,493 | Urine albumin `URXUMA`, urine creatinine `URXUCR`, ACR `URDACT` |
| `MCQ_L.xpt` | 11,744 | Comorbidity questionnaire (label support only, never inputs) |

Expected joinable cohort: ~6,000–7,000 adults with creatinine + ACR
(20+ years, per CDC convention).

## Label rule (KDIGO-2012, single-measure — same convention as CDC reports)

`ckd = 1` iff `eGFR < 60` OR `ACR ≥ 30`, where eGFR comes from the
CKD-EPI 2021 race-free equation on calibrated creatinine. Adults 20+.
Known bias (disclosed, not hidden): single-measure labeling overestimates
true CKD vs the >3-month persistence criterion — CDC's own reports carry
the same caveat.

## QUARANTINE LIST (banned from model inputs — violation aborts training)

`eGFR` (computed), `URXUMA`, `URXUMS`, `URXUCR`, `URXCRS`, `URDACT`,
`URDUMALC`, `URDUCRLC`, `LBXSCR`, `LBDSCRSI` (serum creatinine, both units),
and any column mathematically derived from the above. Rationale: every one
of these participated in the label rule directly or via CKD-EPI.

## Allowed inputs

Demographics (age, sex, ethnicity, income, education), vitals (BMI, BP),
non-creatinine labs (BUN, glucose, electrolytes, hemoglobin-adjacent,
lipids), comorbidities (diabetes, hypertension, smoking). Serum creatinine
is EXCLUDED even though it is our strongest UCI feature — that exclusion
is the entire credibility of this exercise.

## Audit gates (must all pass before harmonization)

1. Circularity: label reconstructible ≥99% from allowed inputs alone → STOP.
2. Sanity: positive rate 10–20% (CDC 2021–2023: ~14%); duplicates 0;
   missingness honest (expected heavy in urine labs).
3. Provenance: this file + CDC doc URLs recorded in `ppt.md`.

## v2 re-derivation (2026-10-10, user-approved: merge everything, re-audit)

All 10 XPTs left-joined (added BMX/BPXO/DIQ/GHB/GLU/CBC/MCQ to the v1
DEMO+BIOPRO+ALB_CR base). Cohort unchanged: 5,343 labeled adults, 17.3%
positive, 0 dups. Circularity re-probe on 83 allowed numeric inputs: 86% —
no leak. New fields present: BMI 1.0% missing, BP systolic 2.6%, HbA1c 0%,
DIQ010 0%. Locked training source: `nhanes_ckd_derived.csv` (5,343 × 177).

## Approval

- [x] User approved 2026-11-02 ("ok go ahead and do it"), authorizing
      multi-cycle expansion under the audit gates above

## v3 multi-cycle expansion (2026-11-02)

Cycles pooled: I (2015–16, SDDSRVYR 9), J (2017–18, 10), L (2021–23, 12).
Builder: `src/ingestion/build_nhanes_cohort.py`; golden test
`tests/test_nhanes_cohort_build.py` proves the cycle-L extraction reproduces
`nhanes_ckd_derived.csv` exactly (row set, labels, all 23 contract values).
Output: `nhanes_ckd_multi.csv` — 15,244 labeled adults, 2,696 positive
(17.69%), 0 duplicate SEQN.

Per-cycle positives: I 5,074 / 16.73%, J 4,827 / 19.10%, L 5,343 / 17.31%.
Missingness: INDFMPIR 11.8%, BP 6.3%, BMI 1.0%, everything else <1%.

Gates: 1 circularity — probe on the 23 allowed inputs only, ROC 0.8201
(threshold 0.99) → PASS, no leak. 2 sanity — 17.69% inside 10–20%, 0 dups,
missingness honest → PASS. 3 provenance — CDC component files below.

Structural drift handled: cycles G/H/I measure BP with the manual device, so
the component and columns are `BPX_I` with `BPXSY1`/`BPXDI1`, renamed to the
`BPXOSY1`/`BPXODI1` contract names at read time.

Evaluation: forward split — fit on I+J (9,901 rows), hold out cycle L whole
(5,343 rows, 925 positive) via `nhanes_holdout_cycle: 12`. The old random
20% split scored a model on unseen rows of the *same* cycle it was fitted on,
which flattered the estimate; the forward split is the honest number.

Result (model v15, gradient-boosting, threshold 0.1026 picked on I+J dev OOF
at recall target 0.80, applied blind to L): ROC 0.8214 on all 5,343 holdout
rows; precision 0.3239, recall 0.8378. On the 1,069 rows v14 was scored on,
v15 ROC 0.8145 vs v14 0.8313 (paired dROC −0.0171, CI [−0.0343, −0.0005])
while v15 PR-AUC is higher (0.5834 vs 0.5628, CI crosses zero). Reading: the
old 0.83 headline was inflated by within-cycle leakage; the ranking loss is
real but small, and the operating-point metrics improved.

Provenance (CDC public data files, `wwwn.cdc.gov/Nchs/Data/Nhanes/Public/`):

| cycle | folder | components |
|-------|--------|------------|
| I 2015–16 | `2015/DataFiles` | DEMO_I BIOPRO_I ALB_CR_I BMX_I DIQ_I GHB_I CBC_I BPX_I |
| J 2017–18 | `2017/DataFiles` | DEMO_J BIOPRO_J ALB_CR_J BMX_J DIQ_J GHB_J CBC_J BPXO_J |
| L 2021–23 | `2021/DataFiles` | DEMO_L BIOPRO_L ALB_CR_L BMX_L BPXO_L DIQ_L GHB_L CBC_L |
