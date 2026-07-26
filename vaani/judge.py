"""Sarvam-105b as a clinical judge — dynamic mode only.

Static mode scores locally against the transcribe transcript (see textutils
.classify) — cheap, instant, no LLM. Dynamic mode is different in kind: it
scores against the *verbatim* transcript (what the patient actually said,
disfluencies included) and additionally decides which word comes next, so the
LLM sits on the blocking path here — the patient is, by construction, waiting
on a real clinical judgement rather than a string comparison.

Verified API recipe (see JUDGE.md — re-verify if a call ever 4xx's):
  POST https://api.sarvam.ai/v1/chat/completions, OpenAI-compatible,
  header api-subscription-key, model "sarvam-105b" or "sarvam-30b".
  MUST set reasoning_effort=null or the model "thinks" into a separate
  reasoning_content field and `content` comes back None. Structured output
  (response_format=json_schema, strict) is not a hard guarantee — roughly
  1 in 8 calls come back malformed in testing, so this wraps json.loads in a
  retry and a rule-based fallback that never blocks the patient.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from .config import Config
from .http_retry import post_with_retry
from .textutils import CORRECT, classify

log = logging.getLogger(__name__)

_ENDPOINT = "https://api.sarvam.ai/v1/chat/completions"

# Clinical error taxonomy (JUDGE.md's cueing-hierarchy categories, plus the
# binary correct/no_speech local classify() already uses). error_type drives
# both the SLP note and which result_label the attempt gets.
ERROR_TYPES = (
    "correct",              # target reached cleanly
    "effortful_correct",    # reached the target, but with false starts / self-correction
    "semantic_paraphasia",  # a different real word, related in MEANING (milk for water)
    "phonemic_paraphasia",  # a near-miss in FORM/pronunciation (ಪುತ್ತಕ for ಪುಸ್ತಕ)
    "partial_groping",      # attempted, trailed off on a fragment
    "no_attempt",           # nothing intelligible
)

_ERROR_TO_LABEL = {
    "correct": "correct",
    "effortful_correct": "correct",
    "semantic_paraphasia": "incorrect",
    "phonemic_paraphasia": "incorrect",
    "partial_groping": "incorrect",
    "no_attempt": "no_speech",
}

_SYSTEM_PROMPT = """You are a speech-language pathologist's clinical judge for a \
post-stroke aphasia practice app. You see ONE attempt at a target word — both \
what a normalising ASR heard (disfluencies repaired) and what was literally \
said (verbatim, disfluencies kept) — and you do two things:

1. Classify the error type of THIS attempt from the verbatim transcript \
against the target, using exactly one of:
   - correct: heard_verbatim IS the target_word — same word, same number/\
tense/form. Not a related word, not a plural, not a different inflection: \
target "tooth" heard "teeth" is NOT correct (teeth is a different, real \
word — that is semantic_paraphasia or phonemic_paraphasia, see below, \
never correct). When in doubt whether two strings are "the same word", they \
are not — pick a paraphasia category instead of guessing correct.
   - effortful_correct: the target WAS reached verbatim (by the same strict \
rule above), but with visible false starts, repetition, or self-correction \
on the way there (e.g. verbatim "stay... station" for target "station" — \
the disfluency is exactly what verbatim exists to catch, and it still \
counts as reaching the word, just with visible effort).
   - semantic_paraphasia: a different real word, related in MEANING to the \
target (said "milk" for "water", or a morphological relative like "teeth" \
for "tooth").
   - phonemic_paraphasia: a near-miss in FORM/pronunciation, not meaning \
(said a word that sounds close but is wrong).
   - partial_groping: an attempt that trails off on a fragment of the word, \
never completing it.
   - no_attempt: nothing intelligible, silence, or an unrelated word.
   RULE: if heard_verbatim is empty or whitespace, the answer is ALWAYS \
no_attempt — never guess a paraphasia type from silence.
   RULE: the input field `verified_matches_target` is a deterministic string \
comparison computed before you were called. If it is true, the patient DID \
produce the target — error_type MUST be correct (or effortful_correct if \
heard_verbatim also shows false starts or repetition). Never return a \
paraphasia or no_attempt when verified_matches_target is true, no matter \
what the session history looks like.
   RULE: error_type is decided ONLY by comparing heard_verbatim to \
target_word for THIS attempt. session_history describes PAST attempts on \
DIFFERENT words — it is irrelevant to this classification and must never \
change it. A clean, clear heard_verbatim match to target_word is correct \
even if every prior attempt in the history was no_attempt; a trend in the \
history is never evidence about what was heard just now. session_history \
matters ONLY for step 2 below (picking the next word), never for step 1.

2. Pick the SINGLE best next word for this patient from the numbered \
candidate list you're given — you may ONLY return an id from that list, \
never invent a word. Apply these rules, in order, using the session history \
you're given:
   - If the last 2 attempts in the history were errors on the SAME word_type \
or the SAME category as each other, do not pick a candidate in that same \
category — word-finding deficits are category-specific, so switch domains \
rather than re-drilling the one that's failing.
   - If errors are trending in the history (2 or more non-correct results), \
prefer a LOWER-level candidate (more concrete, higher-frequency) over a \
higher one — abstract and low-frequency words are harder, so don't escalate \
difficulty into a losing streak.
   - If audio_duration_sec is trending upward across the history (attempts \
taking longer), prefer a candidate with SHORTER text — that's a pace/fluency \
accommodation, independent of difficulty.
   - If the last 2 attempts were both correct, prefer a HIGHER-level \
candidate than the word just attempted — don't stall on mastered material.
   - Otherwise, prefer variety: don't repeat the same category as the \
immediately preceding word if an alternative exists.

Respond with strict JSON only, matching the given schema. next_word_reason is \
one short clinical sentence for the therapist's note, about the NEXT word \
choice, e.g. "Two misses on body-part nouns — switching to food category at \
the same level." cue_hint MUST be generated fresh for the actual target_word \
given in THIS request — never reuse an example word from these instructions. \
It is a retry cue for the CURRENT target_word the patient just attempted \
(NOT about the next word, and NOT the target word spoken aloud) — empty \
string if error_type is correct or effortful_correct, otherwise pick the \
style matching error_type: semantic_paraphasia → name the FIRST SOUND of \
THIS target_word specifically — read target_word's own first letter/sound \
before writing the cue, e.g. target_word "bread" starts with /b/, so the cue \
is "it starts with the /b/ sound" (never borrow a sound from a candidate or \
example word); phonemic_paraphasia → break THIS target_word into its own \
syllables and ask the patient to repeat it slowly, e.g. target_word "station" \
→ "say it slowly: stay... shun" (segment the actual target_word, do not \
describe or name any other word); no_attempt → a semantic description \
of what THIS target IS or DOES, in your own words, specific to this word \
(not a stock phrase); partial_groping → a completion cue built from THIS \
target's meaning ("you use it to ___", "you ___ it")."""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "error_type": {"type": "string", "enum": list(ERROR_TYPES)},
        "next_word_id": {"type": "integer"},
        "next_word_reason": {"type": "string"},
        "cue_hint": {"type": "string"},
    },
    "required": ["error_type", "next_word_id", "next_word_reason", "cue_hint"],
    "additionalProperties": False,
}


@dataclass
class JudgeResult:
    error_type: str
    result_label: str          # derived from error_type via _ERROR_TO_LABEL
    next_word_id: Optional[int]
    next_word_reason: str
    cue_hint: str
    fell_back: bool = False    # True if the LLM call failed and this is the rule-based fallback


class SarvamJudge:
    def __init__(self, config: Config):
        self._key = config.sarvam_api_key
        self._model = config.sarvam_judge_model

    def judge_attempt(
        self,
        target_word: str,
        transcript: str,
        transcript_verbatim: str,
        candidates: list[dict],
        session_history: list[dict],
    ) -> JudgeResult:
        """Classify this attempt and pick the next word, in one call.

        `candidates` and `session_history` are the dicts db.candidate_words()
        / db.patient_recent_attempts() return (the latter spans all of the
        patient's sessions, not just the one in progress). Falls back to a
        rule-based result (never raises, never blocks) if the API call fails,
        times out, or comes back malformed after one retry.
        """
        if not candidates:
            return self._fallback(target_word, transcript_verbatim, None, "no candidates left")

        # Does the patient's own verbatim production already match the target?
        # If so that is a settled fact, not something to ask an LLM about —
        # see the override below.
        local_label, _ = classify(transcript_verbatim, target_word)
        verified_correct = local_label == CORRECT

        candidate_ids = {c["id"] for c in candidates}
        schema = dict(_RESPONSE_SCHEMA)
        schema["properties"] = dict(_RESPONSE_SCHEMA["properties"])
        schema["properties"]["next_word_id"] = {
            "type": "integer", "enum": sorted(candidate_ids),
        }

        user_payload = {
            "target_word": target_word,
            "heard_normalised": transcript,
            "heard_verbatim": transcript_verbatim,
            # Deterministic string comparison, computed before the call. When
            # true, step 1 is already settled — say so rather than letting the
            # model re-derive it from a losing streak.
            "verified_matches_target": verified_correct,
            "candidates": [
                {k: c[k] for k in ("id", "text", "word_type", "category", "level")}
                for c in candidates
            ],
            "session_history_most_recent_first": session_history,
        }

        body = {
            "model": self._model,
            "temperature": 0.1,
            "reasoning_effort": None,  # thinking-on leaves content=None — see module docstring
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "judge_result", "strict": True, "schema": schema},
            },
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }

        for attempt in (1, 2):  # one retry — structured output isn't a hard guarantee
            try:
                resp = post_with_retry(
                    _ENDPOINT,
                    headers={
                        "api-subscription-key": self._key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=12,
                )
                choice = resp.json()["choices"][0]
                content = choice["message"].get("content")
                if not content or choice.get("finish_reason") == "length":
                    log.warning("Judge call %d/2: empty/truncated content, retrying", attempt)
                    continue
                parsed = json.loads(content)
                error_type = parsed["error_type"]
                next_word_id = int(parsed["next_word_id"])
                if error_type not in ERROR_TYPES or next_word_id not in candidate_ids:
                    log.warning("Judge call %d/2: invalid error_type/next_word_id, retrying", attempt)
                    continue

                cue_hint = parsed.get("cue_hint", "")
                # GUARDRAIL. Measured failure: given a session_history of
                # no_speech results, the model anchors on the streak and
                # returns no_attempt for a verbatim transcript that exactly
                # matches the target (4/4 trials; 0/3 with the same input and
                # an empty history). Prompt rules did not hold. The worst
                # possible failure for this product — the struggling patient
                # is the target user, and the app would refuse to credit their
                # correct answer *because* they had been struggling. A
                # normalised exact/near match to the target IS the target, so
                # that verdict is not the model's to overturn.
                if verified_correct and error_type not in ("correct", "effortful_correct"):
                    log.warning(
                        "Judge override: verbatim %r matches target %r but model said %s "
                        "— forcing correct (history-anchoring guard)",
                        transcript_verbatim, target_word, error_type,
                    )
                    error_type = "correct"
                    cue_hint = ""  # nothing to cue; they said it right

                return JudgeResult(
                    error_type=error_type,
                    result_label=_ERROR_TO_LABEL[error_type],
                    next_word_id=next_word_id,
                    next_word_reason=parsed.get("next_word_reason", ""),
                    cue_hint=cue_hint,
                )
            except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as e:
                log.warning("Judge call %d/2 failed: %s", attempt, e)

        return self._fallback(target_word, transcript_verbatim, candidates, "judge call failed twice")

    def _fallback(
        self, target_word: str, transcript_verbatim: str,
        candidates: Optional[list[dict]], reason: str,
    ) -> JudgeResult:
        """Rule-based degradation: local classify() on the verbatim transcript
        (still verbatim-scored, just not LLM-judged) and the first — already
        category-shuffled — candidate. Never blocks the patient."""
        label, _ = classify(transcript_verbatim, target_word)
        next_id = candidates[0]["id"] if candidates else None
        log.warning("Judge fallback (%s): target=%r label=%s next=%s", reason, target_word, label, next_id)
        return JudgeResult(
            error_type="correct" if label == "correct" else (
                "no_attempt" if label == "no_speech" else "phonemic_paraphasia"
            ),
            result_label=label,
            next_word_id=next_id,
            next_word_reason=f"Judge unavailable ({reason}) — rule-based fallback.",
            cue_hint="",
            fell_back=True,
        )
