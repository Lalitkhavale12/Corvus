"""
Backward-compatibility shim: the validation runner now lives at
``src.validation.validate``. This file keeps the old CLI entry point
(``python data/validation/validate.py``) working by re-exporting it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.validation.validate import (  # noqa: E402
    SUITE_FILENAME,
    SUITE_NAME,
    build_gx_suite,
    load_suite_definitions,
    main,
    run_raw_validation,
    suite_path,
)

__all__ = [
    "SUITE_FILENAME",
    "SUITE_NAME",
    "build_gx_suite",
    "load_suite_definitions",
    "main",
    "run_raw_validation",
    "suite_path",
]

if __name__ == "__main__":
    sys.exit(main())
