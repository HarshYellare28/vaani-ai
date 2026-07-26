"""Sarvam Bulbul — Text-to-Speech.

Speaks the target word and the feedback. `pace` is set slow by default
(therapy context) and can be lowered further to syllable-stretch a word.

NOTE: Sarvam's API shapes evolve. Verify against https://docs.sarvam.ai
if a call 4xx's.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os

from .config import Config
from .http_retry import post_with_retry
from .langs import to_sarvam_lang

log = logging.getLogger(__name__)

_ENDPOINT = "https://api.sarvam.ai/text-to-speech"


class SarvamTTS:
    def __init__(self, config: Config, cache_dir: str = "audio_out/tts"):
        self._key = config.sarvam_api_key
        self._model = config.sarvam_tts_model
        self._speaker = config.sarvam_tts_speaker
        self._pace = config.sarvam_tts_pace
        self._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def cache_path(
        self,
        text: str,
        language_code: str,
        pace: float | None = None,
        speaker: str | None = None,
    ) -> str:
        """Content-addressed path for one utterance.

        Everything that changes the audio is in the key, so a hit is always
        safe to serve and changing voice/pace/model can't return stale audio.
        """
        key = "|".join((
            self._model,
            to_sarvam_lang(language_code),
            speaker or self._speaker or "",
            str(pace if pace is not None else self._pace),
            text,
        ))
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
        return os.path.join(self._cache_dir, f"{digest}.wav")

    def synthesize(
        self,
        text: str,
        out_path: str | None = None,
        language_code: str = "hi-IN",
        pace: float | None = None,
        speaker: str | None = None,
    ) -> str:
        """Synthesize `text` to a WAV and return its path.

        The corpus is finite and the feedback lines are templates, so the same
        handful of utterances recur constantly — the "correct" line is byte
        identical on every correct attempt. Each synthesis is a 2-3s network
        round trip that lands *after* ASR, i.e. squarely in the patient's wait.
        So results are cached on disk by content and a hit skips the API
        entirely. Omit `out_path` to use the cache (what callers want); pass
        one only to force a write to a specific location.

        Pass a lower `pace` (e.g. 0.5) to slow a word down for modeling, or a
        `speaker` to override the configured voice (e.g. a per-locale voice).
        """
        effective_pace = pace if pace is not None else self._pace
        effective_speaker = speaker or self._speaker
        lang = to_sarvam_lang(language_code)

        target = out_path or self.cache_path(text, language_code, pace, speaker)
        if out_path is None and os.path.exists(target) and os.path.getsize(target) > 0:
            log.info("Sarvam TTS cache hit: lang=%s text=%r -> %s", lang, text, target)
            return target

        log.info(
            "Sarvam TTS: speaker=%s pace=%s lang=%s (req %s) text=%r -> %s",
            effective_speaker, effective_pace, lang, language_code, text, target,
        )
        resp = post_with_retry(
            _ENDPOINT,
            headers={
                "api-subscription-key": self._key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "target_language_code": lang,
                "speaker": effective_speaker,
                "pace": effective_pace,
                "model": self._model,
                "speech_sample_rate": 16000,
            },
            timeout=30,
        )
        audio_b64 = resp.json()["audios"][0]
        # Write via a temp file and rename: a half-written WAV left by a crash
        # would otherwise be served as a cache hit forever.
        tmp = f"{target}.part"
        with open(tmp, "wb") as f:
            f.write(base64.b64decode(audio_b64))
        os.replace(tmp, target)
        return target
