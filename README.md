# Corvus

An end-to-end MLOps platform for automated training, deployment, and monitoring
of disease prediction models — Chronic Kidney Disease (CKD) as the pilot use case.

## Status

- [x] Project scaffolding
- [x] Phase 1 — Data pipeline
- [ ] Phase 2 — Experiment tracking (MLflow)
- [ ] Phase 3 — Model registry
- [ ] Phase 4 — FastAPI service
- [ ] Phase 5 — Docker
- [ ] Phase 6 — CI/CD
- [ ] Phase 7 — Monitoring (Prometheus + Grafana)
- [ ] Phase 8 — Drift detection (Evidently AI)
- [ ] Phase 9 — Auto retraining (Airflow)

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

Note: with only ~400 rows, drift-detection and auto-retraining (Phases 8–9)
will need either a held-out "incoming data" simulation or an augmented stream
to trigger meaningfully — worth deciding before you get there.
