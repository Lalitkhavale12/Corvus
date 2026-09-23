"""
Phase 1 — Data ingestion.

Loads the raw CKD dataset, runs basic structural sanity checks, and writes a
quick data-quality summary to reports/. This does NOT clean or transform the
data — that's preprocessing.py's job. Keeping the two separate means you can
re-validate a new raw file drop without re-running the full pipeline, and it
maps cleanly onto Phase 1's "Data Validation Layer" from the project plan.

Handles the UCI CKD dataset's known quirks out of the box:
- missing values encoded as "?" rather than NaN
- numeric columns (e.g. packed cell volume, white/red blood cell counts)
  stored as strings because of stray "?" or whitespace
- inconsistent categorical labels (e.g. "yes", " yes", "\tno")

If you're using a different dataset, only this file and preprocess.py's
NUMERIC_COLS/CATEGORICAL_COLS need to change — config.yaml holds the paths
and target column so the rest of the pipeline doesn't need touching.
"""
from pathlib import Path
import pandas as pd

from src.utils.config import load_config, PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger()


def load_raw_data(raw_path: str | None = None) -> pd.DataFrame:
    cfg = load_config()
    path = Path(raw_path or cfg["data"]["raw_path"])

    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {path}.\n"
            f"Download the UCI CKD dataset and place it there as 'kidney_disease.csv', "
            f"or update data.raw_path in config/config.yaml."
        )

    df = pd.read_csv(path)

    # Normalize the well-known UCI CKD quirks: "?" -> NaN, strip whitespace
    # from string cells (values and column names alike).
    df.columns = [c.strip() for c in df.columns]
    df = df.replace(r"^\s*\?\s*$", pd.NA, regex=True)
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": pd.NA, "": pd.NA})

    log.info(f"Loaded raw data: {df.shape[0]} rows x {df.shape[1]} cols from {path}")
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column missingness + dtype summary, also written to reports/."""
    summary = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "missing_count": df.isna().sum(),
            "missing_pct": (df.isna().mean() * 100).round(2),
            "n_unique": df.nunique(),
        }
    ).sort_values("missing_pct", ascending=False)
    return summary


def main():
    cfg = load_config()
    df = load_raw_data()

    # Fail fast on a bad raw drop — same gate preprocess.main() enforces, so
    # standalone ingestion runs can never silently pass invalid data downstream.
    from src.validation.validate import run_raw_validation  # local: avoids import cycle

    gate_result = run_raw_validation(df)
    if not gate_result.success:
        raise SystemExit("Raw-data validation failed — aborting before summary.")

    summary = summarize(df)
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_path = reports_dir / "data_quality_summary.csv"
    summary.to_csv(summary_path)
    log.info(f"Wrote data quality summary to {summary_path}")

    target_col = cfg["data"]["target_column"]
    if target_col in df.columns:
        counts = df[target_col].value_counts(dropna=False)
        log.info(f"Target column '{target_col}' distribution:\n{counts}")
    else:
        log.warning(
            f"Configured target column '{target_col}' not found in columns: "
            f"{list(df.columns)}"
        )

    log.info(f"Data quality summary:\n{summary}")


if __name__ == "__main__":
    main()
