# Dataset Analysis — All 11 Uploaded Files

## Group A: Same dataset, different packaging (no new information)

| File | What it actually is |
|---|---|
| `kidney_disease.csv` | **Canonical UCI-336.** 400 rows, 250 ckd / 150 notckd (2 rows have a stray `ckd\t` label, sums correctly to 250). Matches `chronic_kidney_disease_info.txt` exactly. |
| `chronic_kidney_disease.arff` | Same UCI-336 data, Weka ARFF format. Redundant with the CSV above. |
| `chronic_kidney_disease_full.arff` | Same UCI-336 data + full metadata header comments. Redundant. |
| `chronic_kidney_disease_info.txt` | The `.names` metadata file for UCI-336 — not a dataset, just documentation (already reviewed). |
| `kidney_disease_test.csv` | Checked by ID: **100% of its 120 rows are a subset of `kidney_disease.csv`** with the label column stripped. Zero new information — it's a Kaggle-style unlabeled test split of the same 400 records. |
| `CKD_Preprocessed.csv` | Same 400 rows, same 250/150 split, but pre-imputed and pre-one-hot-encoded (zero nulls). This is the pre-cleaned mirror flagged before — skips the preprocessing story we want the pipeline to demonstrate. |

**Verdict: these six files are one dataset.** No comparison needed between them — `kidney_disease.csv` is already what Corvus is built on.

## Group B: Genuinely different data

| File | What it is | Verdict |
|---|---|---|
| `ckd-dataset-v2.csv` | **UCI-857 confirmed.** After stripping 2 leaked ARFF-header rows: 200 rows, 128 ckd / 72 notckd, includes `stage` (s1–s5) and `grf` (eGFR). Independent Bangladeshi cohort. | ✅ Already our planned drift-simulation source (Phase 8) — this just confirms the file is the right one. |
| `ChronicKidneyDisease_EHRs_from_AbuDhabi.csv` | **Real, independent cohort** — 491 patients, zero missing values, genuinely different task shape: `EventCKD35` + `TimeToEventMonths` is **survival/time-to-event data** (progression to CKD stage 3–5 over up to ~9 years), ~11.4% event rate, not a snapshot classification label. | New finding — not a drop-in replacement or supplement. See decision needed below. |
| `CKD_Risk_Progression_Dataset_2026.csv` | 200,000 rows, 82 columns. **Synthetic, with a leaky target**: mean eGFR is 85.3 for CKD=0 vs. 50.0 for CKD=1, with the CKD=0 minimum sitting exactly at 60.0 — the clinical eGFR<60 diagnostic threshold. The label was almost certainly rule-generated directly from eGFR, not independently observed. A model trained on this mostly just learns to threshold one input feature. | Not suitable as a primary training source; the size makes it tempting but the label leakage defeats the purpose. |
| `kidney_disease_dataset.csv` | 20,000 rows, 43 columns, 5-level severity target. Class split is suspiciously exact (80% / 10% / 4.01% / 3.985% / 2.005%) and there are **zero missing values across 43 fields including rare labs** (IL-6, PTH, Cystatin C) that real clinical data essentially never has fully populated. Synthetic. | Same issue as above — realistic-looking but generated, not collected. |
| `updated_ckd_dataset_with_stages.csv` | 4,000 rows. Contains `ckd_pred` (already **model-predicted** labels — 3,875 CKD / 125 No CKD, ~97% positive) and `cluster` (output of an unsupervised clustering step). | **Not usable as ground truth at all** — training on `ckd_pred` means training on another model's fallible predictions, not real diagnoses. Circular. |

---

## Recommendation: no change to the existing plan

**Primary training set: `kidney_disease.csv` (UCI-336)** — real, clinically-sourced, the only one with a documented provenance chain (named nephrologist, named hospital, named institution) and no leakage or circularity issues. Confirmed exactly matches what Corvus is already built against.

**Drift-simulation set: `ckd-dataset-v2.csv` (UCI-857)** — confirmed as the right file, independent population, ready for Phase 8.

**Do not use:** the 200K and 20K "rich" synthetic sets, or the `ckd_pred`/`cluster` derived set — each has a specific, demonstrable validity problem (leaky label, synthetic-generation artifacts, or circular labeling), not just "less realistic."

## One open decision: the Abu Dhabi EHR file

This is the one file that's genuinely new and genuinely real. But it answers a different question than Corvus currently asks — "who progresses to CKD stage 3–5 over the next several years" (survival analysis) vs. "does this patient have CKD right now" (snapshot classification). Folding it in would mean adding a second modeling paradigm (Cox proportional hazards / time-to-event) alongside the existing pipeline, similar in scope-cost to the image-classifier stretch goal — not a quick add.

Worth deciding explicitly rather than defaulting either way: is this something you want to note for later (a "Phase 11" stretch, parallel to the CNN one) and continue with UCI-336/857 as-is, or is progression prediction actually closer to the core research question than binary CKD classification?
