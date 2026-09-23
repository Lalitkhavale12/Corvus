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

Training-input contract (Claim 2, locked before Phase 2):
  Phase 2 training re-splits from RAW (or loads the ``*_raw.csv`` files
  below) and uses this pipeline as the input step, so the logged
  ``preprocessing_pipeline.joblib`` is the object that actually produced
  the training features. The transformed ``train/val/test.csv`` files are
  audit outputs, not the training inputs.

Produces:
  data/processed/train.csv
  data/processed/val.csv
  data/processed/test.csv              <- transformed features + target + lineage
  data/processed/train_raw.csv
  data/processed/val_raw.csv
  data/processed/test_raw.csv          <- cleaned-but-untransformed features + target + lineage
  data/processed/preprocessing_pipeline.joblib   <- the fitted Pipeline object

Lineage columns (metadata, must be excluded from model features):
  __source_row  original raw-frame index label for every row
  __source_id   raw id-column value, when the dataset has one

Column lists (numeric/categorical) are the single source of truth in
``config/config.yaml`` under ``data.numeric_cols`` /
``data.categorical_cols``. ``NUMERIC_COLS`` / ``CATEGORICAL_COLS`` below are
deprecated import-time aliases kept only so old imports don't crash.
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
from src.validation.validate import run_raw_validation

log = get_logger()

# Fallback column groups for the UCI CKD dataset. The live values come from
# config.yaml via get_column_lists(); these exist only for contexts where the
# config can't be read and for backward-compatible imports.
_DEFAULT_NUMERIC_COLS = [
    "age", "bp", "sg", "al", "su", "bgr", "bu", "sc", "sod", "pot",
    "hemo", "pcv", "wc", "rc",
]
_DEFAULT_CATEGORICAL_COLS = [
    "rbc", "pc", "pcc", "ba", "htn", "dm", "cad", "appet", "pe", "ane",
]

# Deprecated aliases — prefer get_column_lists().
NUMERIC_COLS = list(_DEFAULT_NUMERIC_COLS)
CATEGORICAL_COLS = list(_DEFAULT_CATEGORICAL_COLS)

LINEAGE_ROW_COL = "__source_row"
LINEAGE_ID_COL = "__source_id"


def get_column_lists() -> tuple[list[str], list[str]]:
    """Config-driven column groups (single source of truth)."""
    cfg = load_config()
    numeric = cfg["data"].get("numeric_cols") or list(_DEFAULT_NUMERIC_COLS)
    categorical = cfg["data"].get("categorical_cols") or list(_DEFAULT_CATEGORICAL_COLS)
    return list(numeric), list(categorical)


def _clean_target(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """UCI CKD labels sometimes carry stray whitespace/tabs (e.g. 'ckd\\t')."""
    df[target_col] = df[target_col].astype(str).str.strip().str.lower()
    return df


def clean_raw(df: pd.DataFrame) -> pd.DataFrame:
    """
    Leak-safe cleaning only: normalizing the target label's text, coercing
    numeric dtypes, and dropping rows with no label. The id column (when
    configured) is CARRIED, not dropped — split_raw excludes it from features
    and main() persists it as lineage. None of this involves fitting anything
    on the data, so it's safe to do before the train/val/test split.
    """
    cfg = load_config()
    target_col = cfg["data"]["target_column"]
    id_col = cfg["data"].get("id_column")
    numeric_cfg, categorical_cfg = get_column_lists()

    df = df.copy()
    df = _clean_target(df, target_col)
    df = df.dropna(subset=[target_col])

    numeric_cols = [c for c in numeric_cfg if c in df.columns]
    categorical_cols = [c for c in categorical_cfg if c in df.columns]
    missing_expected = (
        set(df.columns) - set(numeric_cols) - set(categorical_cols)
        - {target_col} - ({id_col} if id_col else set())
    )
    if missing_expected:
        log.warning(
            f"Columns present in data but not classified as numeric/categorical: "
            f"{missing_expected}. They'll be dropped - add them to data.numeric_cols "
            f"or data.categorical_cols in config/config.yaml if they should be kept."
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
    if id_col and id_col in df.columns:
        keep_cols = keep_cols + [id_col]
    return df[keep_cols]


def split_raw(df: pd.DataFrame):
    """Split BEFORE any fitting happens, so no statistic ever sees test data.

    The configured id column (when present) is excluded from the feature
    matrix alongside the target. Callers recover per-split ids with
    ``df.loc[X_split.index, id_col]`` since the original index is preserved.
    """
    cfg = load_config()
    target_col = cfg["data"]["target_column"]
    id_col = cfg["data"].get("id_column")
    drop_cols = [target_col] + ([id_col] if id_col and id_col in df.columns else [])
    X = df.drop(columns=drop_cols)
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

    Encoder choice is deliberate: OneHotEncoder(drop="first") favors linear
    models (LR/MLP in Phase 2) by avoiding the dummy-variable trap, at the
    cost of one level per categorical that tree models would otherwise split
    on directly. The trade is negligible at 10 low-cardinality clinical
    fields and is recorded here so Phase 2 tree results are read correctly.
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
        log.warning("get_feature_names_out() failed — falling back to f{i} names")
        cols = [f"f{i}" for i in range(arr.shape[1])]
    if hasattr(arr, "toarray"):  # sparse matrix from OneHotEncoder; dense is fine at CKD scale
        arr = arr.toarray()  # ceiling: switch to sparse CSR past ~100k rows
    return pd.DataFrame(arr, columns=cols, index=index)


def fit_transform_split(X_train, X_val, X_test, y_train, y_val, y_test):
    numeric_cfg, categorical_cfg = get_column_lists()
    numeric_cols = [c for c in numeric_cfg if c in X_train.columns]
    categorical_cols = [c for c in categorical_cfg if c in X_train.columns]

    pipeline = build_pipeline(numeric_cols, categorical_cols)
    pipeline.fit(X_train)  # <-- fit on TRAIN ONLY, this is the leakage fix

    train_df = _to_dataframe(pipeline.transform(X_train), pipeline, X_train.index)
    val_df = _to_dataframe(pipeline.transform(X_val), pipeline, X_val.index)
    test_df = _to_dataframe(pipeline.transform(X_test), pipeline, X_test.index)

    log.info(f"Fitted pipeline on train only: {train_df.shape[0]} rows x {train_df.shape[1]} feature columns")
    log.info(f"Feature columns: {list(train_df.columns)}")
    log.info(f"Train target distribution: {y_train.value_counts().to_dict()}")
    log.info(f"Val target distribution: {y_val.value_counts().to_dict()}")
    log.info(f"Test target distribution: {y_test.value_counts().to_dict()}")

    return pipeline, (train_df, val_df, test_df), (y_train, y_val, y_test)


def save_outputs(pipeline, splits, ys, raw_splits=None, source_ids=None) -> None:
    """Persist transformed splits, raw splits, lineage, and the pipeline.

    Transformed ``{train,val,test}.csv`` files are audit outputs. The
    ``{train,val,test}_raw.csv`` files carry cleaned-but-untransformed
    features so Phase 2 can use the pipeline as the actual training input
    step (Claim 2 contract). ``__source_row`` / ``__source_id`` are metadata
    and MUST be excluded from model features.
    """
    cfg = load_config()
    target_col = cfg["data"]["target_column"]
    out_dir = Path(cfg["data"]["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    raws = raw_splits if raw_splits is not None else [None, None, None]
    ids = source_ids if source_ids is not None else [None, None, None]
    for name, X_split, y_split, X_raw, id_vals in zip(["train", "val", "test"], splits, ys, raws, ids):
        split_df = X_split.copy()
        split_df[LINEAGE_ROW_COL] = X_split.index
        if id_vals is not None:
            split_df[LINEAGE_ID_COL] = pd.Series(id_vals, index=X_split.index).values
        split_df[target_col] = y_split.values
        split_df.to_csv(out_dir / f"{name}.csv", index=False)
        log.info(f"Wrote {name}.csv: {split_df.shape[0]} rows")

        if X_raw is not None:
            raw_df = X_raw.copy()
            raw_df[LINEAGE_ROW_COL] = X_raw.index
            if id_vals is not None:
                raw_df[LINEAGE_ID_COL] = pd.Series(id_vals, index=X_raw.index).values
            raw_df[target_col] = y_split.values
            raw_df.to_csv(out_dir / f"{name}_raw.csv", index=False)
            log.info(f"Wrote {name}_raw.csv: {raw_df.shape[0]} rows")

    pipeline_path = out_dir / "preprocessing_pipeline.joblib"
    joblib.dump(pipeline, pipeline_path)
    log.info(
        f"Saved fitted preprocessing pipeline to {pipeline_path} "
        f"(Phase 2 training must use this pipeline as the input step — "
        f"train from *_raw.csv, not from the transformed CSVs — Claim 2)"
    )


def main():
    df_raw = load_raw_data()
    gate_result = run_raw_validation(df_raw)
    if not gate_result.success:
        raise SystemExit("Raw-data validation failed — aborting before clean/split.")
    df = clean_raw(df_raw)
    X_train, X_val, X_test, y_train, y_val, y_test = split_raw(df)
    pipeline, splits, ys = fit_transform_split(X_train, X_val, X_test, y_train, y_val, y_test)

    cfg = load_config()
    id_col = cfg["data"].get("id_column")
    if id_col and id_col in df.columns:
        id_map = df[id_col]
        source_ids = [id_map.loc[X.index] for X in (X_train, X_val, X_test)]
    else:
        source_ids = [None, None, None]
    save_outputs(pipeline, splits, ys,
                 raw_splits=(X_train, X_val, X_test), source_ids=source_ids)
    log.info("Phase 1 preprocessing complete (leak-safe, single-pipeline artifact).")


if __name__ == "__main__":
    main()
