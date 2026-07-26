"""Text matching + Devanagari helpers — the core of Sarvam-based judging.

Sarvam's transcript is the gold-truth record of what the patient said. We judge
an attempt by comparing that transcript to the target word: exact (normalized)
match or high similarity = correct; otherwise incorrect; empty = no speech.
Binary on purpose (see classify) — string similarity can't reliably separate a
near-miss from a different word, so we don't fake an "almost" tier. This is
uniform across all languages.
"""

from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher


# ── normalization & similarity ───────────────────────────────────────────
def normalize(text: str) -> str:
    """NFC-normalize, unify interchangeable Hindi nasal marks, and strip
    punctuation/whitespace so transcript ↔ target compares cleanly.

    Sarvam appends punctuation (।, ?, .) and ँ/ं are interchangeable in Hindi
    ASR output, so both are neutralized here.
    """
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("ँ", "ं")  # candrabindu → anusvara
    text = "".join(
        ch for ch in text
        if not unicodedata.category(ch).startswith("P") and not ch.isspace()
    )
    return text.casefold()


def similarity(a: str, b: str) -> float:
    """0.0–1.0 similarity between two raw strings (normalized internally)."""
    na, nb = normalize(a), normalize(b)
    if not na and not nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


# Result labels (stored for SLP analytics; drive feedback in decision.py).
CORRECT = "correct"
INCORRECT = "incorrect"  # not the target word (could be close OR very different)
NO_SPEECH = "no_speech"  # nothing transcribed


def classify(
    transcript: str,
    target: str,
    correct_ratio: float = 0.85,
) -> tuple[str, float]:
    """Return (label, similarity) for an attempt — binary correct/incorrect.

    Binary on purpose: string similarity can't reliably tell a "near-miss
    pronunciation" from a different word that happens to share letters (पानी
    vs पापी = 0.75), so a middle "almost" band mislabels different words. We
    keep the continuous `similarity` for SLP analytics, but the LABEL is binary.

    exact match OR similarity >= correct_ratio → CORRECT
    empty transcript                           → NO_SPEECH
    otherwise                                  → INCORRECT
    """
    if not normalize(transcript):
        return NO_SPEECH, 0.0
    ratio = similarity(transcript, target)
    if normalize(transcript) == normalize(target) or ratio >= correct_ratio:
        return CORRECT, ratio
    return INCORRECT, ratio


# ── Indic syllabification (for slow re-modeling via TTS) ──────────────────
# U+0900–U+0D7F spans Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil,
# Telugu, Kannada and Malayalam — every Sarvam language written in a Brahmic
# script. They share one akshara model, so the algorithm below is identical
# across them; only the virama codepoint differs per script.
def _is_indic(ch: str) -> bool:
    return 0x0900 <= ord(ch) <= 0x0D7F


def _is_virama(ch: str) -> bool:
    """True for any Brahmic virama/halant (U+094D, U+0CCD, …).

    Every one of them carries canonical combining class 9, so this identifies
    the consonant-joiner in all nine scripts without a per-script table.
    """
    return unicodedata.combining(ch) == 9


def syllabify(word: str) -> str:
    """Space-separate Indic orthographic syllables (aksharas) so TTS speaks the
    target slowly, syllable by syllable. Non-Indic (English) is returned
    unchanged. e.g. 'पापा' -> 'पा पा', 'नमस्ते' -> 'न म स्ते',
    'ಅಮ್ಮ' -> 'ಅ ಮ್ಮ'.
    """
    if not any(_is_indic(c) for c in word):
        return word
    aksharas: list[str] = []
    cur, prev = "", ""
    for ch in word:
        combining = unicodedata.category(ch) in ("Mn", "Mc")
        if not cur:
            cur = ch
        elif combining or _is_virama(prev):
            cur += ch
        else:
            aksharas.append(cur)
            cur = ch
        prev = ch
    if cur:
        aksharas.append(cur)
    return " ".join(aksharas)
