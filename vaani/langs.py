"""Language-code helpers for the Sarvam boundary.

Sarvam (Saaras ASR + Bulbul TTS) accept Indic locales plus `en-IN` — but NOT
`en-US`. Azure Pronunciation Assessment, in contrast, uses `en-US` for English.
So the app uses `en-US` everywhere for consistency with Azure, and we normalize
to a Sarvam-supported code only when calling Sarvam: any English variant maps to
`en-IN`; supported codes pass through unchanged.
"""

from __future__ import annotations

SARVAM_LANGS = {
    "as-IN", "bn-IN", "brx-IN", "doi-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN",
    "kok-IN", "ks-IN", "mai-IN", "ml-IN", "mni-IN", "mr-IN", "ne-IN", "od-IN",
    "pa-IN", "sa-IN", "sat-IN", "sd-IN", "ta-IN", "te-IN", "ur-IN",
}


def to_sarvam_lang(code: str) -> str:
    if code in SARVAM_LANGS:
        return code
    if code.lower().startswith("en"):
        return "en-IN"
    return code  # unknown — let Sarvam validate and surface a clear error
