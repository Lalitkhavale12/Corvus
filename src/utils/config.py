"""Load and expose the project config (config/config.yaml)."""
from copy import deepcopy
from pathlib import Path
from functools import lru_cache
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


@lru_cache(maxsize=1)
def _read_config_file(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Return a fresh, caller-owned copy with data paths resolved to absolute.

    The parsed file is cached, but every caller gets its own deepcopy so a
    mutation in one place can never poison later callers.
    """
    cfg = deepcopy(_read_config_file(str(path)))
    cfg["data"]["raw_path"] = str(PROJECT_ROOT / cfg["data"]["raw_path"])
    cfg["data"]["processed_dir"] = str(PROJECT_ROOT / cfg["data"]["processed_dir"])
    cfg["data"]["validation_dir"] = str(PROJECT_ROOT / cfg["data"]["validation_dir"])
    return cfg


# Keep `load_config.cache_clear()` working for tests that reset config state.
load_config.cache_clear = _read_config_file.cache_clear
