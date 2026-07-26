"""Sarvam Saaras v3 — Speech-to-Text.

Transcribes the patient's audio. For the static drill this is mainly for
logging *what they actually said* (Azure PA handles the scoring). It is the
same ASR layer you'll reuse for Feature 2's open conversation.

Saaras v3 replaces the deprecated Saarika v2.5. Same `/speech-to-text`
endpoint, but selects behaviour via `mode`:
    transcribe (default) | verbatim | codemix | translit | translate
  * codemix  → best for mixed Hindi-English (this patient's profile)
  * verbatim → keeps disfluencies/fillers literally (clinically useful)
Saaras v3 auto-detects language, so `language_code` is optional.

NOTE: Sarvam's API shapes evolve. These match the documented form at time of
writing — verify against https://docs.sarvam.ai if a call 4xx's.
"""

from __future__ import annotations

import logging

from .config import Config
from .http_retry import post_with_retry
from .langs import to_sarvam_lang
from .models import AsrResult

log = logging.getLogger(__name__)

_ENDPOINT = "https://api.sarvam.ai/speech-to-text"


class SarvamASR:
    def __init__(self, config: Config):
        self._key = config.sarvam_api_key
        self._model = config.sarvam_asr_model
        self._mode = config.sarvam_asr_mode

    def transcribe(
        self,
        wav_path: str,
        language_code: str | None = None,
        mode: str | None = None,
    ) -> AsrResult:
        """Transcribe a WAV file (16kHz mono recommended) → AsrResult.

        language_code is optional (Saaras v3 auto-detects); pass e.g. "hi-IN"
        to pin it. mode overrides the configured default for this one call.
        """
        data = {"model": self._model, "mode": mode or self._mode}
        if language_code:
            data["language_code"] = to_sarvam_lang(language_code)

        log.info(
            "Sarvam ASR request: model=%s mode=%s lang=%s file=%s",
            data["model"], data["mode"], language_code or "auto", wav_path,
        )
        # Read into bytes rather than streaming the file handle: a retry
        # re-sends the request, and a handle already read to EOF on attempt 1
        # would silently upload an empty file on attempt 2.
        with open(wav_path, "rb") as f:
            wav_bytes = f.read()
        resp = post_with_retry(
            _ENDPOINT,
            headers={"api-subscription-key": self._key},
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data=data,
            timeout=30,
        )
        body = resp.json()
        result = AsrResult(
            transcript=body.get("transcript", ""),
            language_code=body.get("language_code"),
            language_probability=body.get("language_probability"),
        )
        log.info(
            "Sarvam ASR result: transcript=%r detected_lang=%s prob=%s",
            result.transcript, result.language_code, result.language_probability,
        )
        return result
