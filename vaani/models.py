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
    transcript: str          # mode=transcribe — normalised; scores in static mode
    result_label: str        # textutils: correct | incorrect | no_speech
    similarity: float        # 0.0–1.0 transcript↔target match
    audio_duration_sec: float  # length of the recorded attempt (fluency proxy)
    transcript_verbatim: str = ""  # mode=verbatim — keeps disfluencies; scores in dynamic mode
    language_detected: Optional[str] = None
    language_probability: Optional[float] = None

    # Dynamic mode only — set when an LLM judge (not local classify()) decided
    # result_label. None for static-mode attempts.
    judge_error_type: Optional[str] = None   # clinical taxonomy, see vaani/judge.py
    judge_next_word_id: Optional[int] = None
    judge_note: Optional[str] = None

    @property
    def correct(self) -> bool:
        from .textutils import CORRECT
        return self.result_label == CORRECT
