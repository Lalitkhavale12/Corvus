# Reference Papers — ML/DL Extraction & Dataset Map

> Source: `TY/EDI/Reference Papers/` (4 PDFs, read 2026-10-10).
> Purpose: ground Corvus decisions in published methods and map where big
> real datasets actually live. Facts below are transcribed from the papers;
> judgments are marked as such.

## Paper 1 — AKI prediction with CNN (Wang et al., arXiv:2005.13171)

- **Task:** Binary AKI-onset prediction after ICU admission (KDIGO labels).
- **Datasets:** MIMIC-III (61,532 ICU patients → 2,663 included → 5,010 post-SMOTE)
  and eICU (200,000+ stays → 116,775 → 186,298 post-SMOTE). First ICU stay,
  age 18–89, last measurements from 7 days pre-admission.
- **Model:** 1D conv (16 filters, 3×1) → reshape → 2D CNN block (VGG-8/12/16,
  ResNet-18/34; 3×3, stride 1) → FC 64 → FC 16 → sigmoid; batch norm,
  dropout 0.5; 5-fold CV; AUROC metric.
- **Baselines beaten:** MLP (degrades with depth), LR, DT/XGBoost, RF,
  WB-CNN, RNN.
- **Results:** AUROC 0.988 (MIMIC-III), 0.936 (eICU). 16 features (15 on
  eICU). Code + data on GitHub.
- **Access:** Credentialed (PhysioNet + ethics training). Not a direct download.

## Paper 2 — Interpretable AKI in cirrhosis (Sun et al., arXiv:2508.10233)

- **Task:** Creatinine-elevation prediction in cirrhotic ICU patients, first-48h data.
- **Dataset:** MIMIC-IV v2.2 (65,366 stays → 1,240 cirrhosis cohort, ICD
  K74/K70, stay ≥48h, no cancer). Stratified 70/30 split.
- **Pipeline:** KNN imputation → z-score → drop >20% missing → LASSO (16 final
  features) → SMOTE inside training folds only.
- **Models:** LightGBM, CatBoost, XGBoost, LR (L1/L2), Naïve Bayes, shallow
  1-hidden-layer NN. 5-fold CV tuning; AUROC/acc/sens/spec/F1/PPV/NPV +
  bootstrapped CIs; SHAP + ALE + ablation.
- **Results:** LightGBM wins — AUROC 0.808 (95% CI 0.741–0.856), NPV 0.911.
  Top predictors: prolonged PTT, absent outside-facility 20G placement, low
  pH, altered pO2.
- **Access:** Credentialed (PhysioNet).

## Paper 3 — Leakage review in CKD prediction (Hossain et al., arXiv:2607.11963)

- **Task:** Systematic review of 19 CKD studies; leakage taxonomy
  (Li = 2·DL + PL + 2·TL; low ≤2, high ≥3).
- **Datasets named (hunting map):** UCI CKD India 400 · NHANES USA 28,377 ·
  UK Biobank UK 15,811 · BD Community Bangladesh 284 · TH UAE 491 · Korean
  multi-center 5,120 · Thai T2DM 3,471 · Chinese T2DM 12,190 · China
  multicenter 22,263 · Enam (UCI-857 source) 200.
- **ML/DL inventoried:** LR/SVM/DT → RF/XGBoost/CatBoost → MLP/NN, GCN,
  GAN few-shot; RFE/RFECV/SFS/LASSO/PCA; MICE/KNN/median; SMOTE.
- **Results:** high-leakage studies avg 95.48% accuracy vs 80.2% leakage-free
  (+15.3%, p=0.005). Stable predictors: age, BP, glycemic control
  (Fleiss κ=0.224, "fair"). eGFR/creatinine-as-features = direct leakage.
- **Judgment:** peer-reviewed vindication of the Corvus vetting doctrine
  (see `dataset_requirements.md`).

## Paper 4 — AKI models critical appraisal (Vagliano et al., Clin Kidney J 2022)

- **Task:** PROBAST appraisal of 46 AKI studies (from 3,166 titles).
- **Datasets:** mostly single-center + MIMIC (10/46); populations 50–1.84M.
- **ML/DL inventoried:** RF most common (37%) and most often best-in-study;
  GBTs; SVM; RNN strongest DL family; CNN/MLP/Bayes/KNN/ensembles; LR
  comparator in 50% (best in 13%); CV 43%; external validation 17%;
  calibration in 7%.
- **Results:** AUROC 0.49–0.99; high bias risk in 39/46; code shared 11%,
  data 19%.
- **Judgment:** the "what not to do" checklist — external validation,
  calibration, code sharing are exactly the gaps Corvus was built to close.

## Dataset hunting implications (judgment, not paper fact)

1. MIMIC-IV is the one big real EHR source within student reach (free
   account + training, no institutional deal) — but AKI/ICU-shaped, so it
   means a task reframing, not a drop-in CKD set.
2. Korean 5.1K, Chinese 12–22K cohorts from Paper 3's references are the next
   leads; their supplementary data may be requestable.
3. NHANES 28K appears as legitimate survey data — consistent with the
   NHANES-with-leakage-protocol stretch already scoped.
4. No paper hands us a clean large CKD-clinic CSV; the hunt continues under
   `dataset_requirements.md`.
