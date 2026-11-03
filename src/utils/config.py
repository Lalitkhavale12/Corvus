"""Load and expose the project config (config/config.yaml)."""

from __future__ import annotations

import os
import re
from copy import deepcopy
from pathlib import Path
from functools import lru_cache
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

# .env holds the local dev secrets (SECRET_KEY and friends) and is
# gitignored. Deployment sets real environment variables instead; a missing
# .env is normal and not an error.
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:  # python-dotenv ships with uvicorn[standard]
    pass

_ENV_VAR_RE = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


def _substitute_env(value: str) -> str:
    """Replace ${VAR:default} or ${VAR} with env value or default."""
    if not isinstance(value, str):
        return value

    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        return os.environ.get(var_name, default if default is not None else "")

    return _ENV_VAR_RE.sub(_replace, value)


def _substitute_env_recursive(obj):
    """Recursively substitute env vars in all string values of a config."""
    if isinstance(obj, str):
        return _substitute_env(obj)
    if isinstance(obj, dict):
        return {k: _substitute_env_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_env_recursive(v) for v in obj]
    return obj


@lru_cache(maxsize=1)
def _read_config_file(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Return a fresh, caller-owned copy with data paths resolved to absolute.

    The parsed file is cached, but every caller gets its own deepcopy so a
    mutation in one place can never poison later calls. Environment variables
    in ${VAR:default} form are substituted before resolution.
    """
    cfg = deepcopy(_read_config_file(str(path)))
    cfg = _substitute_env_recursive(cfg)
    cfg["data"]["raw_path"] = str(PROJECT_ROOT / cfg["data"]["raw_path"])
    cfg["data"]["processed_dir"] = str(PROJECT_ROOT / cfg["data"]["processed_dir"])
    cfg["data"]["validation_dir"] = str(PROJECT_ROOT / cfg["data"]["validation_dir"])
    return cfg


# Keep `load_config.cache_clear()` working for tests that reset config state.
load_config.cache_clear = _read_config_file.cache_clear
