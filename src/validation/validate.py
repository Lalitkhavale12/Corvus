"""
Phase 1 — raw-CSV validation gate (Great Expectations 1.x only).

Validates the quirk-normalized raw frame produced by
``src.ingestion.load_data.load_raw_data`` against the persisted contract in
``ckd_suite.json`` (under the configured ``data.validation_dir``), then
enforces config-driven row-count bounds and an exact-duplicate check. Every
path and threshold is resolved through ``src.utils.config.load_config`` — no
hard-coded data paths, no hard-coded row counts, and no fitting of any kind
(this module must stay leak-safe).

GX 1.x flow: ephemeral context -> pandas data source -> dataframe asset ->
whole-dataframe batch definition -> ``batch.validate(suite)``.

Exit contract: invoking this runner as a script exits 0 when the
configured raw CSV satisfies all gates, non-zero otherwise — and never with
an unhandled traceback for data failures (the gate fails closed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

try:
    import great_expectations as gx
except ImportError:  # minimal guard only — no hand-rolled fallback validator
    gx = None

from src.ingestion.load_data import load_raw_data
from src.utils.config import load_config
from src.utils.logger import get_logger

log = get_logger()

SUITE_FILENAME = "ckd_suite.json"
SUITE_NAME = "ckd_raw_suite"


def suite_path() -> Path:
    cfg = load_config()
    return Path(cfg["data"]["validation_dir"]) / SUITE_FILENAME


def load_suite_definitions() -> list[dict]:
    """Version-agnostic suite: list of {expectation_type, kwargs} dicts."""
    with open(suite_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def build_gx_suite(definitions: list[dict], name: str = SUITE_NAME):
    if gx is None:
        raise RuntimeError(
            "great_expectations is not importable in the active interpreter. "
            "Use the project interpreter and install requirements: "
            "venv/python.exe -m pip install -r requirements.txt"
        )
    suite = gx.ExpectationSuite(name=name)
    for item in definitions:
        expectation_cls = getattr(gx.expectations, item["expectation_type"])
        suite.add_expectation(expectation_cls(**item["kwargs"]))
    return suite


def _check_row_bounds(df, cfg) -> bool:
    """Row-count bounds come from config, never from hard-coded literals."""
    vcfg = cfg.get("validation", {})
    min_rows = vcfg.get("min_rows", 0)
    max_rows = vcfg.get("max_rows", float("inf"))
    n = len(df)
    if not (min_rows <= n <= max_rows):
        log.warning(f"Raw-data row count {n} outside [{min_rows}, {max_rows}]")
        return False
    return True


def _check_no_exact_duplicates(df, cfg) -> bool:
    if cfg.get("validation", {}).get("fail_on_duplicates", False) and df.duplicated().any():
        n_dup = int(df.duplicated().sum())
        log.warning(f"Raw-data gate found {n_dup} exact-duplicate rows")
        return False
    return True


def run_raw_validation(df=None):
    """Validate a raw CKD frame against the persisted suite plus config gates.

    When ``df`` is None the frame is loaded via ``load_raw_data()`` using the
    paths from ``load_config()["data"]``. Returns the GX validation result
    (which carries a ``success`` bool) on full pass; data failures fail closed
    with a ``success=False`` result instead of raising.
    """
    cfg = load_config()
    if df is None:
        df = load_raw_data(raw_path=cfg["data"]["raw_path"])
    if gx is None:
        raise RuntimeError(
            "great_expectations is not importable in the active interpreter. "
            "Use the project interpreter and install requirements: "
            "venv/python.exe -m pip install -r requirements.txt"
        )
    try:
        context = gx.get_context()
        suite = build_gx_suite(load_suite_definitions())
        data_source = context.data_sources.add_pandas("ckd_raw_validation")
        data_asset = data_source.add_dataframe_asset(name="ckd_raw")
        batch_definition = data_asset.add_batch_definition_whole_dataframe(
            "ckd_raw_batch"
        )
        batch = batch_definition.get_batch(batch_parameters={"dataframe": df})
        result = batch.validate(suite)
        log.info(f"Raw-data GX validation success={result.success}")
        if not result.success:
            return result
        if not _check_row_bounds(df, cfg):
            return SimpleNamespace(success=False)
        if not _check_no_exact_duplicates(df, cfg):
            return SimpleNamespace(success=False)
        return result
    except Exception as exc:
        log.warning(f"Raw-data validation failed: {type(exc).__name__}: {exc}")
        return SimpleNamespace(success=False)


def main() -> int:
    try:
        result = run_raw_validation()
    except Exception as exc:
        print(f"RAW VALIDATION ERROR: {exc}")
        return 1
    if result.success:
        print("RAW VALIDATION PASSED")
        return 0
    print("RAW VALIDATION FAILED — see log for failing expectations")
    return 1


if __name__ == "__main__":
    sys.exit(main())
