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
- Both classes at least 20% — 97/3 or 92/8 splits are unusable without
  resampling theater.
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

- Training set: UCI-336 (400 rows) — passes all blocks at small scale.
- **Big cohort: NHANES 2021–2023 derivation SELECTED 2026-10-10** —
  `data/nhanes/nhanes_ckd_derived.csv` (5,343 adults, 17.3% positive):
  KDIGO labels from CKD-EPI 2021 eGFR + ACR; quarantine held (10 banned
  columns); audit gates passed (circularity 86% < 99%, prevalence in band,
  0 dups). Protocol: `data/nhanes/NHANES_PROTOCOL.md`.
- Validation set: OPEN HUNT (UCI-857 disqualified 2026-10-10).
