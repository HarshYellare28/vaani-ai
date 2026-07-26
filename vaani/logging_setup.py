"""Logging setup — one place to configure pipeline logging.

Logs go to both stdout (watch live) and logs/vaani.log (compare later).
Call setup_logging() once from an entry point (api.py / run_drill.py).
"""

from __future__ import annotations

import logging
import os
import sys


def setup_logging(level: int = logging.INFO, logfile: str = "logs/vaani.log"):
    """Configure the 'vaani' logger tree. Idempotent (safe under --reload)."""
    logger = logging.getLogger("vaani")
    if logger.handlers:  # already configured
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-5s %(name)s | %(message)s", "%H:%M:%S"
    )

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    os.makedirs(os.path.dirname(logfile), exist_ok=True)
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
