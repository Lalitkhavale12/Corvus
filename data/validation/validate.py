"""
Phase 1 — raw-CSV validation gate (Great Expectations 1.x only).

Validates the quirk-normalized raw frame produced by
``src.ingestion.load_data.load_raw_data`` against the persisted contract in
``ckd_suite.json`` (same directory). Every path is resolved through
``src.utils.config.load_config`` — no hard-coded data paths, no hard-coded
row counts, and no fitting of any kind (this module must stay leak-safe).

GX 1.x flow: ephemeral context -> pandas data source -> dataframe asset ->
whole-dataframe batch definition -> ``batch.validate(suite)``.

Exit contract: ``python data/validation/validate.py`` exits 0 when the
configured raw CSV satisfies the suite, non-zero otherwise — and never with
an unhandled traceback for data failures (the gate fails closed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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


def run_raw_validation(df=None):
    """Validate a raw CKD frame against the persisted suite.

    When ``df`` is None the frame is loaded via ``load_raw_data()`` using the
    paths from ``load_config()["data"]``. Returns the GX validation result
    (which carries a ``success`` bool); data failures fail closed with a
    ``success=False`` result instead of raising.
    """
    if df is None:
        cfg = load_config()
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
        log.info(f"Raw-data validation success={result.success}")
        return result
    except Exception as exc:
        log.warning(f"Raw-data validation failed: {exc}")
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
