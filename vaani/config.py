"""Configuration — loaded from environment variables (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # reads .env from the working directory if present


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val or val.startswith("your-"):
        raise RuntimeError(
            f"Missing required env var {name!r}. "
            f"Copy .env.example to .env and fill it in."
        )
    return val


@dataclass(frozen=True)
class Config:
    # Sarvam
    sarvam_api_key: str
    sarvam_asr_model: str
    sarvam_asr_mode: str
    sarvam_tts_model: str
    sarvam_tts_speaker: str
    sarvam_tts_pace: float

    # Storage
    db_path: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            sarvam_api_key=_require("SARVAM_API_KEY"),
            sarvam_asr_model=os.getenv("SARVAM_ASR_MODEL", "saaras:v3"),
            sarvam_asr_mode=os.getenv("SARVAM_ASR_MODE", "transcribe"),
            # bulbul:v3 reads English phonetically (v2 translated it to Hindi);
            # its speaker pool differs from v2 — 'anushka' is v2-only.
            sarvam_tts_model=os.getenv("SARVAM_TTS_MODEL", "bulbul:v3"),
            sarvam_tts_speaker=os.getenv("SARVAM_TTS_SPEAKER", "priya"),
            sarvam_tts_pace=float(os.getenv("SARVAM_TTS_PACE", "0.8")),
            db_path=os.getenv("VAANI_DB_PATH", "vaani.db"),
        )
