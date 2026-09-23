"""Central logger setup for Corvus. Import get_logger() wherever you need it."""
import sys
from pathlib import Path
from loguru import logger

from src.utils.config import load_config, PROJECT_ROOT

_configured = False


def get_logger():
    global _configured
    if not _configured:
        cfg = load_config()
        log_dir = PROJECT_ROOT / cfg["logging"]["log_dir"]
        log_dir.mkdir(parents=True, exist_ok=True)

        logger.remove()  # drop default handler to avoid duplicate console logs
        logger.add(sys.stderr, level=cfg["logging"]["level"])
        logger.add(
            log_dir / "corvus.log",
            level=cfg["logging"]["level"],
            rotation="5 MB",
            retention=5,
        )
        _configured = True
    return logger
