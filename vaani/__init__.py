"""Vaani — AI-assisted speech therapy pipeline.

Pipeline:  audio → Sarvam ASR (gold-truth transcript) → judge vs target
                  → decision logic → Sarvam TTS → audio feedback
"""

from .config import Config
from .drill import StaticDrill, DrillResult
from .decision import Decision, Action
from .models import Assessment, AsrResult
from .db import Database
from .logging_setup import setup_logging

__all__ = [
    "Config", "StaticDrill", "DrillResult", "Decision", "Action",
    "Assessment", "AsrResult", "Database", "setup_logging",
]
