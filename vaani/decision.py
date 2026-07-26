"""Coaching decision — turns a Sarvam Assessment into spoken feedback.

Rule-based, no LLM needed for the static drill. The judgement is uniform across
languages: Sarvam's transcript is compared to the target (see textutils), and
the resulting label maps to an encouraging, clinically-shaped response. When an
attempt isn't correct, we re-model the target slowly (syllable by syllable for
Devanagari) rather than naming a phoneme — that's what the patient can imitate.

Feedback text is spoken in the session language via Bulbul TTS.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .i18n import feedback_templates
from .models import Assessment
from .textutils import CORRECT, NO_SPEECH, syllabify


class Action(Enum):
    CORRECT = "correct"      # right word — advance
    INCORRECT = "incorrect"  # not the target — re-model slowly, try again
    NO_SPEECH = "no_speech"  # nothing heard — prompt to try again


@dataclass
class Decision:
    action: Action
    feedback_text: str  # shown in the UI (may contain syllabified word for display)
    tts_text: str = ""  # spoken via TTS — original word so Bulbul reads it naturally


def decide(assessment: Assessment) -> Decision:
    """Map an assessment to coaching feedback in the session's own language.

    Feedback templates come from i18n (English fallback). The written form
    re-models the target syllable-by-syllable for Devanagari (syllabify is a
    no-op for other scripts); the spoken form uses the plain word so TTS reads
    it naturally.
    """
    target    = assessment.target_word
    syllables = syllabify(target)  # "मे ह मा न" — display only, not for TTS
    label     = assessment.result_label
    fb        = feedback_templates(assessment.language)

    if label == CORRECT:
        msg = fb["correct"]
        return Decision(Action.CORRECT, msg, msg)

    action = Action.NO_SPEECH if label == NO_SPEECH else Action.INCORRECT
    template = fb["no_speech"] if label == NO_SPEECH else fb["incorrect"]
    display = template.format(word=syllables)
    spoken  = template.format(word=target)
    return Decision(action, display, spoken)
