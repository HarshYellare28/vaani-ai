"""Static drill orchestrator (Feature 1) — Sarvam-only judging.

One round: speak the target word, listen to the attempt, judge it against the
target with Sarvam's transcript, produce a uniform Assessment (the SLP data
record), and speak feedback. Uniform across all languages.

The phone/web client handles mic capture and playback; this backend works with
WAV file paths.
"""

from __future__ import annotations

import contextlib
import logging
import os
import wave
from dataclasses import dataclass

from .asr import SarvamASR
from .config import Config
from .decision import Decision, decide
from .i18n import speaker_for
from .models import Assessment
from .textutils import classify
from .tts import SarvamTTS

log = logging.getLogger(__name__)


@dataclass
class DrillResult:
    assessment: Assessment
    decision: Decision
    feedback_audio_path: str  # spoken feedback, ready to play


class StaticDrill:
    def __init__(self, config: Config | None = None, audio_dir: str = "audio_out"):
        self._config = config or Config.from_env()
        self._asr = SarvamASR(self._config)
        self._tts = SarvamTTS(self._config, cache_dir=os.path.join(audio_dir, "tts"))
        self._audio_dir = audio_dir
        os.makedirs(audio_dir, exist_ok=True)

    def prompt_word(self, word: str, language_code: str = "hi-IN") -> str:
        """Generate the audio that says the target word to the patient.

        Served from the TTS cache, so replaying a word costs nothing.
        """
        return self._tts.synthesize(
            word, language_code=language_code,
            speaker=speaker_for(language_code),
        )

    def evaluate_attempt(
        self,
        target_word: str,
        attempt_wav_path: str,
        *,
        language: str = "hi-IN",
    ) -> DrillResult:
        """Judge one recorded attempt and produce spoken feedback."""
        # 1. Run Sarvam ASR on the attempt.
        asr = self._asr.transcribe(attempt_wav_path, language_code=language)

        # 2. How long was the attempt? (fluency proxy for SLP analytics)
        duration = _wav_duration_sec(attempt_wav_path)

        # 3. Judge from SARVAM ONLY: transcript vs target → label + similarity.
        label, sim = classify(asr.transcript, target_word)
        assessment = Assessment(
            target_word=target_word,
            language=language,
            transcript=asr.transcript,
            result_label=label,
            similarity=sim,
            audio_duration_sec=duration,
            language_detected=asr.language_code,
            language_probability=asr.language_probability,
        )

        # 4. Map to coaching feedback.
        decision = decide(assessment)

        log.info(
            "\n── attempt ─────────────────────────────────────────────────\n"
            "   target     : %r  (%s)\n"
            "   heard      : %r  [detected %s p=%s]\n"
            "   result     : %s  (similarity=%.2f, %.1fs)\n"
            "   decision   : %s\n"
            "────────────────────────────────────────────────────────────",
            target_word, language, asr.transcript,
            asr.language_code, asr.language_probability,
            label, sim, duration, decision.action.value,
        )

        # 5. Speak the feedback (in the session language). Cached by content —
        #    the "correct" line is identical every time, so after the first
        #    correct answer this stops being a network round trip at all.
        tts_text = decision.tts_text or decision.feedback_text
        fb_path = self._tts.synthesize(
            tts_text, language_code=language, speaker=speaker_for(language),
        )

        return DrillResult(
            assessment=assessment,
            decision=decision,
            feedback_audio_path=fb_path,
        )


def _wav_duration_sec(path: str) -> float:
    """Duration of a WAV file in seconds (0.0 if unreadable)."""
    with contextlib.suppress(Exception):
        with wave.open(path, "rb") as w:
            rate = w.getframerate()
            if rate:
                return round(w.getnframes() / rate, 2)
    return 0.0
