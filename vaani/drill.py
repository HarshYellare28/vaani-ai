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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .asr import SarvamASR
from .config import Config
from .decision import Decision, decide
from .i18n import speaker_for
from .judge import SarvamJudge
from .models import AsrResult, Assessment
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
        self._judge = SarvamJudge(self._config)
        self._audio_dir = audio_dir
        os.makedirs(audio_dir, exist_ok=True)

    def _transcribe_both(self, attempt_wav_path: str, language: str) -> tuple[AsrResult, AsrResult]:
        """Saaras `mode=transcribe` + `mode=verbatim`, in parallel — two
        requests, roughly one request of wall time. Shared by both modes;
        which transcript actually *scores* the attempt differs (see below)."""
        with ThreadPoolExecutor(max_workers=2) as ex:
            transcribe_future = ex.submit(
                self._asr.transcribe, attempt_wav_path,
                language_code=language, mode="transcribe",
            )
            verbatim_future = ex.submit(
                self._asr.transcribe, attempt_wav_path,
                language_code=language, mode="verbatim",
            )
            return transcribe_future.result(), verbatim_future.result()

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
        """Static mode: judge one recorded attempt and produce spoken feedback.

        Scores against `mode=transcribe` (normalised) — disfluency repair is
        exactly what makes a fair correct/incorrect call for repeat-practice
        drilling. `mode=verbatim` is captured alongside (SLP-facing) but never
        affects the score here; dynamic mode (evaluate_attempt_dynamic) is
        where verbatim drives the judgement instead.
        """
        # 1. Run Sarvam ASR on the attempt, both modes concurrently.
        asr, asr_verbatim = self._transcribe_both(attempt_wav_path, language)

        # 2. How long was the attempt? (fluency proxy for SLP analytics)
        duration = _wav_duration_sec(attempt_wav_path)

        # 3. Judge from the normalised transcript vs target → label + similarity.
        label, sim = classify(asr.transcript, target_word)
        assessment = Assessment(
            target_word=target_word,
            language=language,
            transcript=asr.transcript,
            transcript_verbatim=asr_verbatim.transcript,
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
            "   target              : %r  (%s)\n"
            "   heard (transcribe)  : %r  [scored this one — detected %s p=%s]\n"
            "   heard (verbatim)    : %r%s\n"
            "   result              : %s  (similarity=%.2f, %.1fs)\n"
            "   decision            : %s\n"
            "────────────────────────────────────────────────────────────",
            target_word, language,
            asr.transcript, asr.language_code, asr.language_probability,
            asr_verbatim.transcript,
            "  ← differs from transcribe" if asr_verbatim.transcript != asr.transcript else "",
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

    def evaluate_attempt_dynamic(
        self,
        target_word: str,
        attempt_wav_path: str,
        *,
        language: str,
        candidates: list[dict],
        session_history: list[dict],
    ) -> DrillResult:
        """Dynamic mode: score against the VERBATIM transcript, judged by
        sarvam-105b (see vaani/judge.py), which also picks the next word from
        `candidates` using session_history. This call is on the patient's
        blocking path — unlike static mode, there's no cheap local stand-in
        for "what did a clinician just hear", so the wait is real (~1-5s).
        The judge itself never blocks forever: it falls back to a rule-based
        result rather than hang if the API is slow or returns garbage.
        """
        asr, asr_verbatim = self._transcribe_both(attempt_wav_path, language)
        duration = _wav_duration_sec(attempt_wav_path)

        result = self._judge.judge_attempt(
            target_word, asr.transcript, asr_verbatim.transcript,
            candidates, session_history,
        )
        # Local similarity on the verbatim transcript, purely for the UI's
        # match-percentage bar — result_label (correctness) comes from the
        # judge, not from this ratio.
        _, sim = classify(asr_verbatim.transcript, target_word)

        assessment = Assessment(
            target_word=target_word,
            language=language,
            transcript=asr.transcript,
            transcript_verbatim=asr_verbatim.transcript,
            result_label=result.result_label,
            similarity=sim,
            audio_duration_sec=duration,
            language_detected=asr.language_code,
            language_probability=asr.language_probability,
            judge_error_type=result.error_type,
            judge_next_word_id=result.next_word_id,
            judge_note=result.next_word_reason,
        )

        decision = decide(assessment)

        log.info(
            "\n── attempt (dynamic) ──────────────────────────────────────\n"
            "   target              : %r  (%s)\n"
            "   heard (transcribe)  : %r  [detected %s p=%s]\n"
            "   heard (verbatim)    : %r  [scored this one]%s\n"
            "   judge error_type    : %s%s\n"
            "   next word           : id=%s — %s\n"
            "   cue_hint            : %r\n"
            "────────────────────────────────────────────────────────────",
            target_word, language,
            asr.transcript, asr.language_code, asr.language_probability,
            asr_verbatim.transcript,
            "  ← differs from transcribe" if asr_verbatim.transcript != asr.transcript else "",
            result.error_type, "  [FALLBACK — judge call failed]" if result.fell_back else "",
            result.next_word_id, result.next_word_reason, result.cue_hint,
        )

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
