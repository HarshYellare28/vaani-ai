"""Data models passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AsrResult:
    """Sarvam ASR output for one attempt."""
    transcript: str
    language_code: Optional[str] = None      # detected, e.g. "hi-IN"
    language_probability: Optional[float] = None  # 0.0–1.0 detection confidence


@dataclass
class Assessment:
    """Uniform per-attempt judgement (language-agnostic, Sarvam-based).

    This is the SLP data record for one attempt — everything an analytics layer
    would aggregate over time.
    """
    target_word: str
    language: str
    transcript: str          # what Sarvam heard (gold truth)
    result_label: str        # textutils: correct | incorrect | no_speech
    similarity: float        # 0.0–1.0 transcript↔target match
    audio_duration_sec: float  # length of the recorded attempt (fluency proxy)
    language_detected: Optional[str] = None
    language_probability: Optional[float] = None

    @property
    def correct(self) -> bool:
        from .textutils import CORRECT
        return self.result_label == CORRECT
