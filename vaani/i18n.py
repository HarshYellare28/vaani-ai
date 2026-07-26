"""Localization — one source of truth for every language the app speaks.

`data/i18n.json` holds one entry per locale (`en`, `hi`, …) with UI strings,
level names, badges, spoken/written feedback templates, and per-locale metadata
(native name, flag, text direction, Sarvam TTS language + voice).

Adding a new Sarvam-supported language is a *data* task: add one entry here and
the word corpus — no code changes. The front-end fetches the whole table via
`GET /i18n`; the backend uses `feedback_templates` / `speaker_for` here.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_I18N_JSON = Path(__file__).resolve().parent / "data" / "i18n.json"

_FALLBACK = "en"  # locale used when a language has no translation yet


@lru_cache(maxsize=1)
def load_locales() -> dict:
    """The full locale table (cached). Keys are base-language locales."""
    with open(_I18N_JSON, encoding="utf-8") as f:
        return json.load(f)


def to_locale(language_code: str | None) -> str:
    """Map a practice/BCP-47 code to a locale key: 'hi-IN'→'hi', 'en-US'→'en'.

    Falls back to English when we have no translation for that language yet.
    """
    locales = load_locales()
    if not language_code:
        return _FALLBACK
    base = language_code.split("-", 1)[0].lower()
    if base in locales:
        return base
    return _FALLBACK


def locale(language_code: str | None) -> dict:
    """The locale entry for a language code (English fallback)."""
    return load_locales()[to_locale(language_code)]


def feedback_templates(language_code: str | None) -> dict:
    """`{correct, no_speech, incorrect}` templates in the session language."""
    return locale(language_code)["feedback"]


def speaker_for(language_code: str | None) -> str | None:
    """Preferred Sarvam (bulbul:v3) voice for a language, if set."""
    return locale(language_code)["meta"].get("speaker")
