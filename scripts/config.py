"""Configuration and shared constants for UmarTransit scripts."""

import logging
import sys
from pathlib import Path


# ── Paths ──────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
CLEANED_DIR = DATASETS_DIR / "cleaned"
SYNTHETIC_DIR = DATASETS_DIR / "synthetic"
CATALOG_DIR = DATASETS_DIR / "catalog"
SEED_FEEDS_PATH = CATALOG_DIR / "seed_feeds.json"
MOBILITY_DB_CSV_PATH = CATALOG_DIR / "mobility_db_feeds.csv"

# ── URLs ───────────────────────────────────────────────────────────────────────

MOBILITY_DB_CSV_URL = "https://bit.ly/catalogs-csv"

# ── Download settings ──────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 120
MAX_RETRIES = 3
RETRY_DELAY = 2.0
CHUNK_SIZE = 8192
USER_AGENT = (
    "UmarTransit-1B/0.1 "
    "(research; github.com/umarfarookm/transit-foundation-model)"
)

# ── Logging ────────────────────────────────────────────────────────────────────

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create a configured logger with console output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
