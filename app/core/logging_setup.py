
import logging
from pathlib import Path
from app.core.config import LOGS_PATH

def setup_logging():
    LOGS_PATH.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("nizam_alqirtasiyah")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(
            LOGS_PATH / "system.log",
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
