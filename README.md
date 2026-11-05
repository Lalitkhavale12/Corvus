# Corvus

An end-to-end MLOps platform for automated training, deployment, and monitoring
of disease prediction models — Chronic Kidney Disease (CKD) as the pilot use case.

## Status

- [x] Phase 1 — Data pipeline
- [x] Phase 2 — Experiment tracking + model training (MLflow)
- [x] Phase 3 — Prediction API + containers
- [x] Phase 4 — CI/CD + monitoring (GitHub Actions, Prometheus, Grafana)
- [ ] Phase 5 — Drift detection + auto-retraining (code built; Airflow service pending)
- [ ] Phase 6 — Visualization + polish
- [x] Phase 7 — NHANES native retrain
- [x] Phase 8 — Web platform + authentication

## Getting started

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Place the raw CKD dataset (UCI CKD, `kidney_disease.csv`) into `data/raw/`.

Run the Phase 1 pipeline:

```bash
python -m src.ingestion.load_data
python -m src.preprocessing.preprocess
```

This produces `data/processed/processed_data.csv` plus train/test splits under
`data/processed/`, and writes a data-quality summary to `reports/`.

## Folder structure

```
Corvus/
├── data/{raw,processed,validation}
├── notebooks/
├── src/{ingestion,preprocessing,feature_engineering,training,evaluation,
│        prediction,monitoring,deployment,utils}
├── models/
├── mlruns/
├── airflow/
├── docker/
├── api/
├── frontend/
├── tests/
├── config/
├── logs/
├── reports/
```

## Dataset

Default target: [UCI CKD dataset](https://archive.ics.uci.edu/dataset/336/chronic+kidney+disease)
(~400 rows, 24 features + class label, mixed numeric/categorical, many missing
values). Config lives in `config/config.yaml` — update `data.raw_path` and
`data.target_column` if you swap datasets.

Note: the UCI cohort (~400 rows) is now a legacy/eval input only. The served
model is NHANES-native **v15**, trained on 5,343 labelled rows from a 15,244-adult
cohort (17.7% positive), holdout ROC-AUC 0.8214 / precision 0.32 / recall 0.84 —
a screening aid, not a diagnosis. Drift detection and auto-retraining (Phase 5)
read live `predictions_v2` rows, so they need real traffic or a held-out
simulation to trigger meaningfully.
