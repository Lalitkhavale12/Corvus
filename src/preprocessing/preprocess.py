"""
Phase 1 - Preprocessing.

Cleans raw data, splits FIRST (train/val/test), then fits a single
sklearn Pipeline (imputer + scaler + encoder) on the training split only,
and applies it to val/test. This fixes two issues found in review:

1. Data leakage: the original version fit imputers/scaler/encoder on the
   FULL dataset before splitting, so test-set statistics leaked into
   training-time preprocessing. Now the split happens on raw (uncleaned
   but leak-safe) data first, and only X_train is used to .fit() anything.

2. Patent Claim 2: the preprocessing steps are now a single fitted
   sklearn.Pipeline object (not inline fit_transform calls + pd.get_dummies),
   so there's one artifact to persist and later log to MLflow in the same
   run as the model (Phase 2/3).

Produces:
  data/processed/train.csv
  data/processed/val.csv
  data/processed/test.csv
  data/processed/preprocessing_pipeline.joblib   <- the fitted Pipeline object

Column lists (NUMERIC_COLS / CATEGORICAL_COLS) are for the UCI CKD dataset.
If your raw file has different columns, update these two lists - everything
downstream is driven by config/config.yaml and doesn't need to change.
"""
from pathlib import Path
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder

from src.ingestion.load_data import load_raw_data
from src.utils.config import load_config, PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger()

# UCI CKD dataset column groups. Adjust for a different dataset.
NUMERIC_COLS = [
    "age", "bp", "sg", "al", "su", "bgr", "bu", "sc", "sod", "pot",
    "hemo", "pcv", "wc", "rc",
]
CATEGORICAL_COLS = [
    "rbc", "pc", "pcc", "ba", "htn", "dm", "cad", "appet", "pe", "ane",
]


def _clean_target(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """UCI CKD labels sometimes carry stray whitespace/tabs (e.g. 'ckd\\t')."""
    df[target_col] = (
        df[target_col].astype(str).str.strip().str.lower().str.rstrip("\t")
    )
    return df


def clean_raw(df: pd.DataFrame) -> pd.DataFrame:
    """
    Leak-safe cleaning only: dropping the id column, normalizing the target
    label's text, coercing numeric dtypes, and dropping rows with no label.
    None of this involves fitting anything on the data, so it's safe to do
    before the train/val/test split.
    """
    cfg = load_config()
    target_col = cfg["data"]["target_column"]
    id_col = cfg["data"].get("id_column")

    df = df.copy()
    if id_col and id_col in df.columns:
        df = df.drop(columns=[id_col])

    df = _clean_target(df, target_col)
    df = df.dropna(subset=[target_col])

    numeric_cols = [c for c in NUMERIC_COLS if c in df.columns]
    categorical_cols = [c for c in CATEGORICAL_COLS if c in df.columns]
    missing_expected = set(df.columns) - set(numeric_cols) - set(categorical_cols) - {target_col}
    if missing_expected:
        log.warning(
            f"Columns present in data but not classified as numeric/categorical: "
            f"{missing_expected}. They'll be dropped - add them to NUMERIC_COLS or "
            f"CATEGORICAL_COLS in preprocess.py if they should be kept."
        )

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    positive_label = cfg["data"]["positive_label"].strip().lower()
    unique_labels = set(df[target_col].unique())
    if positive_label not in unique_labels:
        raise ValueError(
            f"config.data.positive_label='{positive_label}' not found in target "
            f"values {unique_labels}. Update config/config.yaml."
        )
    df[target_col] = (df[target_col] == positive_label).astype(int)

    keep_cols = numeric_cols + categorical_cols + [target_col]
    return df[keep_cols]


def split_raw(df: pd.DataFrame):
    """Split BEFORE any fitting happens, so no statistic ever sees test data."""
    cfg = load_config()
    target_col = cfg["data"]["target_column"]
    X = df.drop(columns=[target_col])
    y = df[target_col]

    strat = y if cfg["split"]["stratify"] else None
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y,
        test_size=cfg["split"]["test_size"] + cfg["split"]["val_size"],
        random_state=cfg["split"]["random_state"],
        stratify=strat,
    )
    val_ratio = cfg["split"]["val_size"] / (cfg["split"]["test_size"] + cfg["split"]["val_size"])
    strat_temp = y_temp if cfg["split"]["stratify"] else None
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp,
        test_size=1 - val_ratio,
        random_state=cfg["split"]["random_state"],
        stratify=strat_temp,
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def build_pipeline(numeric_cols: list[str], categorical_cols: list[str]) -> Pipeline:
    """
    Single fitted-artifact preprocessing pipeline (Patent Claim 2).
    Returns an UNFITTED Pipeline; caller fits it on X_train only.
    """
    cfg = load_config()

    numeric_steps = [("imputer", SimpleImputer(strategy=cfg["preprocessing"]["numeric_impute_strategy"]))]
    if cfg["preprocessing"]["scale_numeric"]:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric_pipeline = Pipeline(numeric_steps)

    if cfg["preprocessing"]["encode_categorical"] == "onehot":
        encoder = OneHotEncoder(handle_unknown="ignore", drop="first")
    else:
        encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy=cfg["preprocessing"]["categorical_impute_strategy"])),
        ("encoder", encoder),
    ])

    transformers = []
    if numeric_cols:
        transformers.append(("num", numeric_pipeline, numeric_cols))
    if categorical_cols:
        transformers.append(("cat", categorical_pipeline, categorical_cols))

    preprocessor = ColumnTransformer(transformers)
    return Pipeline([("preprocessor", preprocessor)])


def _to_dataframe(arr, pipeline: Pipeline, index) -> pd.DataFrame:
    try:
        cols = pipeline.named_steps["preprocessor"].get_feature_names_out()
    except Exception:
        cols = [f"f{i}" for i in range(arr.shape[1])]
    if hasattr(arr, "toarray"):  # sparse matrix from OneHotEncoder
        arr = arr.toarray()
    return pd.DataFrame(arr, columns=cols, index=index)


def fit_transform_split(X_train, X_val, X_test, y_train, y_val, y_test):
    numeric_cols = [c for c in NUMERIC_COLS if c in X_train.columns]
    categorical_cols = [c for c in CATEGORICAL_COLS if c in X_train.columns]

    pipeline = build_pipeline(numeric_cols, categorical_cols)
    pipeline.fit(X_train)  # <-- fit on TRAIN ONLY, this is the leakage fix

    train_df = _to_dataframe(pipeline.transform(X_train), pipeline, X_train.index)
    val_df = _to_dataframe(pipeline.transform(X_val), pipeline, X_val.index)
    test_df = _to_dataframe(pipeline.transform(X_test), pipeline, X_test.index)

    log.info(f"Fitted pipeline on train only: {train_df.shape[0]} rows x {train_df.shape[1]} feature columns")
    log.info(f"Train target distribution: {y_train.value_counts().to_dict()}")

    return pipeline, (train_df, val_df, test_df), (y_train, y_val, y_test)


def save_outputs(pipeline, splits, ys) -> None:
    cfg = load_config()
    target_col = cfg["data"]["target_column"]
    out_dir = Path(cfg["data"]["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, X_split, y_split in zip(["train", "val", "test"], splits, ys):
        split_df = X_split.copy()
        split_df[target_col] = y_split.values
        split_df.to_csv(out_dir / f"{name}.csv", index=False)
        log.info(f"Wrote {name}.csv: {split_df.shape[0]} rows")

    pipeline_path = out_dir / "preprocessing_pipeline.joblib"
    joblib.dump(pipeline, pipeline_path)
    log.info(
        f"Saved fitted preprocessing pipeline to {pipeline_path} "
        f"(Phase 2 training should log this as an MLflow artifact in the "
        f"same run as the model - Claim 2)"
    )


def main():
    df = load_raw_data()
    import importlib.util as _importlib_util
    _gate_cfg = load_config()
    _validate_path = Path(_gate_cfg["data"]["validation_dir"]) / "validate.py"
    _gate_spec = _importlib_util.spec_from_file_location(
        "ckd_raw_validate", _validate_path
    )
    _gate_module = _importlib_util.module_from_spec(_gate_spec)
    _gate_spec.loader.exec_module(_gate_module)
    _gate_result = _gate_module.run_raw_validation(df)
    if not _gate_result.success:
        raise SystemExit("Raw-data validation failed — aborting before clean/split.")
    df = clean_raw(df)
    X_train, X_val, X_test, y_train, y_val, y_test = split_raw(df)
    pipeline, splits, ys = fit_transform_split(X_train, X_val, X_test, y_train, y_val, y_test)
    save_outputs(pipeline, splits, ys)
    log.info("Phase 1 preprocessing complete (leak-safe, single-pipeline artifact).")


if __name__ == "__main__":
    main()
