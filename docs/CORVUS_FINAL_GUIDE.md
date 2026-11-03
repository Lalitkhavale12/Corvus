# Corvus — Final Project Structure & Development Guide

**Timeline: 4–6 weeks (1–1.5 months)**
**Status: Phase 1 complete — data pipeline built, tested, and refactored for
patent-claim compliance and leakage safety.**

This supersedes the earlier development plan. Same overall approach and
timeline; this version folds in everything found during the goals/patent/
structure review and records what's actually been fixed vs. what's tracked
for later.

---

## 1. What Changed Since the Last Version

| Item | Before | Now |
|---|---|---|
| Preprocessing fit order | Imputer/scaler/encoder fit on the **full dataset**, then split | Split happens **first**; pipeline fits on **train only** — data leakage closed |
| Preprocessing artifact | Inline `fit_transform()` calls + `pd.get_dummies()` — no single reusable object | One fitted **`sklearn.Pipeline`** (`ColumnTransformer` of imputer+scaler+encoder), saved as `data/processed/preprocessing_pipeline.joblib` — satisfies **Claim 2** |
| Categorical encoding | `pd.get_dummies()` (not a fit/transform object, can't live inside a Pipeline) | `OneHotEncoder` inside the Pipeline — sklearn-native, serializable |
| Tests | 3 tests, structural only | 4 tests — added direct checks for train/val/test index disjointness (leakage) and that the pipeline is a single fitted `Pipeline` object (Claim 2) |

All 4 tests pass; the full pipeline was run end-to-end against synthetic
UCI-CKD-shaped data (including its `?` missing-value markers) before this
was written up.

---

## 2. Development Approach

**Config-driven, phase-by-phase, parallelized where dependencies allow.**

- `config/config.yaml` is the single source of truth for paths, dataset
  choice, and pipeline parameters.
- Each phase produces a working, testable artifact before the next starts.
  If time runs out, the platform still works end-to-end with a smaller
  feature set — no phase is "finished later."
- Tests are written alongside each phase, not bolted on at the end.
- Heavy/optional infrastructure was cut on day one, not mid-timeline:

| Original item | Decision | Why |
|---|---|---|
| Kubernetes | **Cut** | Docker Compose demonstrates orchestration competency without weeks of learning curve |
| React frontend | **Simplified to Streamlit** | Single Python file vs. a separate frontend build |
| Full 4-stage CI/CD gating | **Simplified to one GitHub Actions workflow** | Still demonstrates CI/CD |
| MLP activation comparison | **Kept**, folded into Phase 2's model comparison, not its own week | No separate phase needed |
| 400-row primary dataset | **Supplemented with UCI id 857** as a simulated incoming batch | Needed for drift detection to trigger meaningfully |

---

## 3. Patent Claim Compliance Tracker

Tracked against what's been discussed for Claims 2, 4, 5, and Component 102.
Claims 1 and 3 and the full five-layer architecture haven't been shared yet —
listed as open below rather than assumed compliant.

| Claim / Component | Requirement | Status | Where it lives |
|---|---|---|---|
| **Claim 2** | Fitted preprocessing pipeline stored as MLflow artifact, same run as model | ✅ **Pipeline object exists and is fitted correctly** (leak-safe). MLflow logging itself happens in Phase 2, when training code loads `preprocessing_pipeline.joblib` and calls `mlflow.log_artifact()` inside the training run. | `src/preprocessing/preprocess.py` |
| **Claim 4** | Log deployed model version per prediction | ⬜ Not built (Phase 4) | Needs a `model_version` field in the prediction-log schema and DB table; FastAPI must resolve current production version from the MLflow Registry per request |
| **Claim 5** | 5 Airflow trigger types + champion/challenger promotion + archived retention | ⬜ Not built (Phase 9) | MLflow Registry's Staging/Production/Archived stages cover "archived retention" natively. Trigger types + promotion logic still need design work in Phase 9 |
| **Component 102** | Standalone data visualization module | ⬜ Not built | No `src/visualization/` yet — tracked below, not forgotten |
| Claims 1, 3 | Unknown | ⬜ Not reviewed | Full claim text not yet shared |

### Backlog tied to phases (not built yet, by design)

These were identified as gaps but deliberately **not** scaffolded early —
building empty folders weeks before their phase starts doesn't save time,
and the risk of them being forgotten is handled by listing them here against
a specific phase, not by pre-creating placeholder files.

- **Phase 2/3:** training code logs `preprocessing_pipeline.joblib` + model as MLflow artifacts in the same run (Claim 2 completion)
- **Phase 4:** `api/schemas/` with a `model_version` field; prediction logging resolves current production model version per request (Claim 4)
- **Phase 7/8:** split `src/monitoring/` into `metrics.py` (Prometheus) and `drift.py` (Evidently) so Claim 5's Airflow triggers call drift-check logic directly, not a mixed module
- **Phase 9:** `airflow/dags/` — 5 trigger-type DAGs + promotion/comparison logic (Claim 5)
- **Whenever picked up:** `src/visualization/` for Component 102, kept distinct from `notebooks/` (which is exploration, not a shippable component)

---

## 4. Tech Stack

| Layer | Technology | Status |
|---|---|---|
| Language | Python | — |
| Data processing | Pandas, NumPy | ✅ Phase 1 |
| Preprocessing pipeline | scikit-learn `Pipeline` + `ColumnTransformer` | ✅ Phase 1 (refactored for Claim 2) |
| Artifact serialization | joblib | ✅ Phase 1 |
| Data validation | Great Expectations | Planned — Phase 2 |
| ML models | Logistic Regression, Random Forest, XGBoost, LightGBM | Planned — Phase 2 |
| Deep learning (MLP comparison) | scikit-learn `MLPClassifier` (Sigmoid/Tanh/ReLU) | Planned — Phase 2 |
| Experiment tracking | MLflow | Planned — Phase 2 |
| Model registry | MLflow Registry | Planned — Phase 3 |
| API | FastAPI | Planned — Phase 4 |
| Frontend | Streamlit | Planned — Phase 4 |
| Containerization | Docker, Docker Compose | Planned — Phase 5 |
| Orchestration (heavy) | ~~Kubernetes~~ | **Cut** |
| CI/CD | GitHub Actions | Planned — Phase 6 |
| Monitoring | Prometheus + Grafana | Planned — Phase 7 |
| Drift detection | Evidently AI | Planned — Phase 8 |
| Retraining orchestration | Apache Airflow | Planned — Phase 9 |
| Database | PostgreSQL | Planned — Phase 5 |
| Logging | Loguru | ✅ Phase 1 |
| Testing | pytest | ✅ Phase 1 (4 tests passing) |
| Visualization (EDA) | Matplotlib, Seaborn | Planned — Phase 2 |

---

## 5. Timeline (5 weeks core + optional buffer)

### Week 1 — Data pipeline + EDA *(complete)*
- ✅ Ingestion, leak-safe preprocessing, single-Pipeline artifact, 4 passing tests
- Remaining: EDA notebook, Great Expectations schema/range checks

### Week 2 — Model training + experiment tracking *(Phases 2–3 merged)*
- Train LR, Decision Tree, Random Forest, Gradient Boosting, XGBoost,
  LightGBM, MLP (Sigmoid/Tanh/ReLU as separate runs)
- Log accuracy/precision/recall/F1/ROC-AUC to MLflow per run
- **Log `preprocessing_pipeline.joblib` + model as artifacts in the same
  MLflow run** — completes Claim 2
- Register best model (by ROC-AUC) to MLflow Registry

### Week 3 — API + containerization *(Phases 4–5 merged)*
- FastAPI: `/predict`, `/batch_predict`, `/health`, `/model_info`
- `api/schemas/` with `model_version` field (Claim 4)
- Dockerize FastAPI + MLflow + PostgreSQL via Docker Compose
- Prediction logging to PostgreSQL, including model version per prediction

### Week 4 — CI/CD + monitoring *(Phases 6–7 merged)*
- GitHub Actions: test → build → push image
- `src/monitoring/metrics.py` — Prometheus (latency, request count, error rate)
- Grafana dashboard

### Week 5 — Drift detection + auto-retraining *(Phases 8–9 merged)*
- `src/monitoring/drift.py` — Evidently AI report, UCI-336 baseline vs.
  UCI-857 as simulated incoming batch
- `airflow/dags/` — trigger types + conditional retrain → re-register →
  redeploy (Claim 5)

### Week 6 (optional buffer)
- Integration testing end-to-end
- Documentation pass, architecture diagram, demo script

---

## 6. Risks & Mitigations

| Risk | Status |
|---|---|
| Preprocessing leaking test-set statistics into training | ✅ **Resolved** — split now happens before any fitting |
| No single artifact to satisfy Claim 2 | ✅ **Resolved** — `sklearn.Pipeline` object, saved via joblib |
| 400-row primary dataset too small for meaningful drift | Mitigated — UCI id 857 used as simulated incoming batch (Week 5) |
| Kubernetes eating disproportionate time | Mitigated — cut entirely |
| Airflow learning curve arriving late (Week 5) | Open — front-load a minimal install/smoke-test in Week 2–3 |
| Compressed timeline leaves no slack | Open by design — each phase has one deliverable, extras are explicitly out of scope |

---

## 7. Final Project Structure

```
Corvus/
├── .gitignore
├── README.md
├── requirements.txt
│
├── config/
│   └── config.yaml                     ✅
│
├── data/
│   ├── raw/
│   ├── processed/                      # + preprocessing_pipeline.joblib after running Phase 1
│   └── validation/                     # Great Expectations, Phase 2
│
├── src/
│   ├── ingestion/
│   │   └── load_data.py                ✅
│   ├── preprocessing/
│   │   └── preprocess.py               ✅ refactored: leak-safe split + single Pipeline artifact
│   ├── feature_engineering/            ⬜ Phase 2
│   ├── training/                       ⬜ Phase 2 — logs pipeline + model together (Claim 2)
│   ├── evaluation/                     ⬜ Phase 2
│   ├── prediction/                     ⬜ Phase 4 — logs model_version per prediction (Claim 4)
│   ├── monitoring/                     ⬜ to split into metrics.py (Phase 7) + drift.py (Phase 8)
│   ├── visualization/                  ⬜ Component 102 — not yet created, tracked above
│   ├── deployment/                     ⬜ Phase 4–5
│   └── utils/
│       ├── config.py                   ✅
│       └── logger.py                   ✅
│
├── models/                             ⬜ MLflow Registry (Staging/Production/Archived — Claim 5)
├── mlruns/                             ⬜ Phase 2
├── airflow/                            ⬜ dags/ to be added in Phase 9 (Claim 5)
├── docker/                             ⬜ Phase 5
├── api/                                ⬜ schemas/ to be added in Phase 4 (Claim 4)
├── frontend/                           ⬜ Phase 4 (Streamlit)
├── notebooks/                          ⬜ EDA, Week 1
├── tests/
│   └── test_preprocessing.py           ✅ 4 tests passing
├── logs/
└── reports/
```

**Legend:** ✅ built & tested · ⬜ planned, tied to a specific phase above

---

## 8. Stretch Goal (Optional): Image-Based CNN Classifier

**Status: not started. Only pursued if Weeks 1–5 finish on schedule and the
optional Week 6 buffer is available.**

- Deferred, not parallel — the core plan has no slack, and neither imaging
  dataset identified so far (ultrasound: segmentation task, non-commercial
  license; histology: rodent-model data) is a clean fit as-is.
- Safe to bolt on later — Corvus's core loop (train → log → register → serve
  → monitor → drift-check → retrain) isn't hardcoded to tabular data; MLflow
  logs PyTorch/TensorFlow models the same way it logs scikit-learn models.
- If pursued: dataset re-selection first, then a separate image ingestion
  module, transfer-learning CNN training, a second registered model, and a
  new `POST /predict_image` endpoint — none of which needs to happen before
  Week 5 of the core plan.
