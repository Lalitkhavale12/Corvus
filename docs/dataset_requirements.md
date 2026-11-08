# Corvus — Dataset Requirements

> The binding specification for any training or validation dataset.
> Every candidate is scored 0–6 against these blocks BEFORE download completes.
> Born from six forensic rejections (2026-09-21 → 2026-10-10); each rule below
> names the failure that created it. No exceptions, no sentiment.

## Block 1 — Task shape (non-negotiable)

- One row = one patient encounter; label = independently observed diagnosis
  (chart review, biopsy registry, nephrologist diagnosis).
- Labels must NEVER be computed from input columns in the same row, and NEVER
  be another model's output.
- Binary or stage-graded CKD status only. Survival/time-to-event, imaging,
  and genomics formats do not fit this pipeline.

## Block 2 — Size and composition

- At least 2,000 rows, so a held-out test set can actually separate models
  (the failure 400 rows guarantees).
- Both classes at least 10% — the live NHANES cohort is 17.7% positive, so a
  20% floor would reject the cohort we actually train and ship; 97/3 or 92/8
  splits are still unusable without resampling theater.
- Documented selection criteria (clinic cohort, survey, registry), so an
  off-baseline prevalence can be judged rather than guessed.

## Block 3 — Features

- Core renal labs required: creatinine/eGFR, or the raw markers (BUN, albumin,
  hemoglobin, RBC/WBC counts, electrolytes, urine protein).
- Continuous values, not pre-binned ranges ("11.3–12.6" killed UCI-857 —
  midpoints are assumptions wearing data's clothes).
- Missingness present and unhidden. Zero nulls across dozens of clinical
  columns is a synthetic fingerprint (real EHR data has holes; our imputers
  exist for exactly that).
- Lifestyle/demographic extras welcome, never required.

## Block 4 — Provenance (the filter that killed all six)

- Named institution, collection period, and label-definition method in
  writing: data card, paper, or registry documentation.
- Derivation audit must pass: no input column (or small set) reconstructs the
  label at 99% or above; no `ckd_pred`-style columns; no stage grid sitting
  beside the target.
- License permitting academic reuse.

## Block 5 — Format practicalities

- CSV, UTF-8, documented headers. No ARFF-header rows leaking into data, no
  unverifiable translated schemas.
- Companion files (data cards, papers) stored as same-named `.txt` links
  beside the CSV; provenance evidence counts toward Block 4.

## Block 6 — Role assignment

- A file that clears Blocks 1–5 becomes the TRAINING candidate.
- External validation requires all of the above PLUS a different
  population/source than the training set. A harmonization mapping must be
  written and reviewed before a single metric is read — the 2026-10-10
  harmonization artifact (v9 scoring 0.36 on garbage-mapped inputs) is why.

## Independent cross-check (2026-11-08)

An externally supplied NHANES derivation (`nhanes_kidney/`, kept outside the
repo) was scored against these blocks. NHANES 2007–2018, 6 cycles, 32,361
adults x 46 features, 16.9% positive, same label rule (CKD-EPI 2021 race-free
eGFR < 60 OR ACR >= 30).

- **Implementation agreement.** 9,901 shared SEQN (our dev cycles, SDDSRVYR 9
  and 10 = 2015–16 and 2017–18); 9,900/9,901 labels agree (99.99%).
- **The one disagreement** is `SEQN 98699`: our label was computed from the
  unrounded ACR 29.996 (negative), their file rounds to 30.0 (positive).
  eGFR max abs diff 0.05, ACR max abs diff 0.01 — agreement to rounding, not
  a rule difference. This is independent evidence that our label derivation
  does what it claims, which is the exact axis the six rejections failed.
- **New rows.** 21,989 rows from 2007–2014, prevalence 16.68% vs 17.37% in
  2015–18 — stable. Covariate shift is modest (age median 47→49, age 65+
  21.9%→23.4%, BUN median 12→14 mg/dL).
- **Feature gap.** Biochemistry only: no blood pressure, BMI, HbA1c or
  diabetes history, so it cannot fill the portable-23 contract.
- **Verdict: not a swap and not external validation.** Same source, same
  population and same label method as our training set, so it fails Block 6;
  it is US data, so it says nothing about Indian patients. Accepted uses:
  (a) the implementation check above, recorded for the report; (b) optional
  reproduction of its 2007–14 → 2015–18 benchmark; (c) optional harvest of
  2007–2014, which would need 16 extra XPTs (`BPX_E–H`, `BMX_E–H`,
  `DIQ_E–H`, `GHB_E–H`) and would grow dev from 9,901 to roughly 19k rows.

## Rejection log (evidence, not opinion)

| Candidate | Size | Failing block | Forensic finding |
|---|---|---|---|
| 200K risk-progression CSV | 200,000 | Block 1 | Label rule-generated from eGFR threshold (85.3 vs 50.0 split at 60.0) |
| 20K severity CSV | 20,000 | Block 3 | Zero missingness incl. rare labs; exact 80/10/4/4/2 splits |
| 4K stages (`ckd_pred`) | 4,000 | Block 1 | Target is another model's predictions; 97% positive |
| 25.8K KDIGO file | 25,800 | Block 1 | Target deterministic in (GFR × Albuminuria): 7 combos, 0 mixed |
| Kaggle NHANES-derived | 11,933 | Block 1 | 5,607 no-eGFR rows all labeled positive by unknown logic |
| UCI-857 (`ckd-dataset-v2`) | 200 | Blocks 1, 3 | Pre-binned numerics; ten 0/1 indicators with P(CKD\|1)=1.0 (target-derived) |

## Current status

- Training set: NHANES 2015–16 + 2017–18 (`data/nhanes/nhanes_ckd_multi.csv`,
  9,901 dev rows after the adult/exclusion rules). UCI-336 (400 rows) is no
  longer the training set — it survives only as the eval-only harmonization
  adapter, which the suite asserts stays out of the serving path.
- **Big cohort: NHANES 2021–2023 derivation SELECTED 2026-10-10** —
  `data/nhanes/nhanes_ckd_derived.csv` (5,343 adults, 17.3% positive):
  KDIGO labels from CKD-EPI 2021 eGFR + ACR; quarantine held (10 banned
  columns); audit gates passed (circularity 86% < 99%, prevalence in band,
  0 dups). Protocol: `data/nhanes/NHANES_PROTOCOL.md`.
- Validation set: OPEN HUNT (UCI-857 disqualified 2026-10-10).
- Label rule cross-checked against an independent implementation on
  2026-11-08: 9,900/9,901 agreement (see the section above).
- Indian cohort: OPEN — no data in hand. This is the only remaining gap that
  changes what the model means for its intended users; everything else left
  is engineering.
