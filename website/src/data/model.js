// Single source of truth for the serving model's verified facts.
// Numbers come from MLflow run 30830a7152394ff2a63ea1005da9f035
// (experiment for corvus-ckd, registry version 15). Do not edit without
// re-reading the run — every UI claim about the model is sourced from here.

export const MODEL_VERSION = "15";
export const MODEL_RUN_ID = "30830a7152394ff2a63ea1005da9f035";
export const MODEL_ALGORITHM = "GradientBoostingClassifier";
export const MODEL_PARAMS = "learning_rate=0.1, max_depth=3, n_estimators=100";
export const FEATURE_COUNT = 36;
export const DECISION_THRESHOLD = 0.10256178929054474;

export const METRICS = {
  rocAuc: 0.8214,
  rocAucCi: [0.8062, 0.8362],
  prAuc: 0.5895,
  precision: 0.3239,
  recall: 0.8378,
  f1: 0.4671,
  accuracy: 0.6691,
  brier: 0.1042,
  cvMeanAuc: 0.8205,
  cvStdAuc: 0.012,
};

export const DATA_NOTES = [
  "Training data: NHANES 2021-2023, unweighted, native schema.",
  "Labels are KDIGO-derived screening labels, not clinical diagnoses.",
  "Holdout split used for every metric shown; no test-set tuning.",
];
