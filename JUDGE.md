# The judge layer — design

Everything here was verified against the live Sarvam API on 26 Jul 2026 with a
personal key. **Re-verify on the event account** before depending on it.

---

## The distinction that matters

"LLM as judge" and "live conversation" are two different things, and only one of
them is buildable today.

- **The judge** scores one attempt and decides what to say next. This is the piece
  that is genuinely new, clinically meaningful, and buildable in 75 minutes.
- **Free-form live conversation** — open topic, full duplex, barge-in — is a
  Phase-2 product, not a milestone. Do not attempt it today.

What sits between them, and what to actually build: a **multi-turn cued exchange**.
The patient attempts a word, the judge classifies the error, picks the next cue
from the clinical hierarchy, and the patient tries again with that cue. Each turn
depends on the previous one. That *is* a conversation by the rubric's definition —
"each follow-up builds on the last answer rather than running down a list" is the
literal L4 wording for Voice Experience — without needing a streaming voice agent.

---

## Why string matching cannot do this

The current-generation approach compares the transcript to the target and returns
correct/incorrect plus a similarity number. It cannot tell you:

- **which kind of error** it was — and the kind is what a clinician treats;
- **whether the target was reached with effort** — "ನೀ… ನೀ… ನೀರು" and "ನೀರು" are the
  same string after normalisation and clinically very different;
- **what to say next** — a real SLP does not say "wrong", they cue.

The judge answers all three. That is the whole argument.

## The cueing hierarchy (the non-obvious part)

Real speech therapy uses a graded cue ladder, and *which* cue you give depends on
the error you saw:

| Error seen | Cue that helps | Why |
|---|---|---|
| Semantic paraphasia (milk for water) | **Phonemic** — "it starts with /nee/" | Meaning is intact, retrieval of the form failed |
| Phonemic paraphasia (ಪುತ್ತಕ for ಪುಸ್ತಕ) | **Model** — say it slowly, syllable by syllable | The form is close; give them something to imitate |
| No attempt | **Semantic** — "it's something you drink" | Nothing to build on; open the semantic route first |
| Partial / groping | **Completion** — "you drink ___" | They are nearly there; carry them over the line |
| Correct | **Advance** | Do not over-coach a success |

An LLM picking the right rung of that ladder from the error it just classified is
therapeutic behaviour that no string comparison can produce, and it is the thing
judges will not have seen from another team.

---

## Verified API recipe

`POST https://api.sarvam.ai/v1/chat/completions` — OpenAI-compatible.
Header `api-subscription-key`. Models: `sarvam-30b` (64K) or `sarvam-105b` (128K).
**Sarvam-M is deprecated and gone.** `response_format: {"type":"json_schema", ...}`
with `strict: true` works.

### The trap that will cost you an hour

These models **think by default**, and the thinking goes into a separate
`reasoning_content` field. While thinking, `content` is `null`. Measured:

| Config | Latency | Result |
|---|---|---|
| `sarvam-30b`, thinking on, `max_tokens=4096` | 15.0s | 14,668 chars of reasoning, blew the budget, **`content=None`** |
| `sarvam-105b`, thinking on | 10–18s | Valid JSON, best clinical accuracy |
| `sarvam-30b`, `reasoning_effort: null` | **0.7–0.8s** | Valid JSON, weaker accuracy |
| `sarvam-105b`, `reasoning_effort: null` | 0.7–4.5s | Better accuracy, one call still returned unparseable JSON |

So:

1. **Set `reasoning_effort: null`** for anything in a user-facing path. `"low"` is
   not enough — it still thinks, and still truncated.
2. **Never assume `content` is a string.** Check for `None` and for
   `finish_reason == "length"` before parsing. This *will* happen.
3. **Always wrap `json.loads` in a try/except** with one retry. Structured output
   is not a guarantee; roughly 1 in 8 calls came back malformed in testing.

### Accuracy is not solved — budget prompt iteration

With thinking off, `sarvam-30b` misclassified 2 of 4 test cases (called an
effortful-correct a "partial attempt"; called a no-attempt a "semantic
paraphasia") and leaked English into a field specified as native-language only.
`sarvam-105b` was better but not clean.

Mitigations that helped: spelling out each `error_type` in the system prompt with a
worked example, `temperature: 0.1`, and putting the range in the schema
`description` (though `score` still came back 0/1 rather than 0–100 — constrain it
with `minimum`/`maximum` or ask for a 0–5 band instead).

**Plan for at least two rounds of prompt tuning against fixed test cases.** Keep a
handful of hardcoded (target, verbatim, normalised) tuples and re-run them after
every prompt change — it takes seconds and it is the only way to know you improved
anything.

---

## The architecture that makes latency a non-issue

Do not put the LLM in the blocking path.

```
audio ──┬─> Saaras mode=verbatim   ─┐
        └─> Saaras mode=transcribe ─┴─> show BOTH transcripts immediately (~0.5s)
                                        │
                                        ├─> fast local match  -> instant correct/retry
                                        │                        + cached TTS reply
                                        └─> LLM judge (async)  -> error type, score,
                                                                  next cue, clinician note
```

- The **patient** never waits on the LLM. They get the two transcripts and an
  immediate verdict from the cheap path.
- The **judge** enriches the record and decides the *next* cue, which is needed a
  few seconds later anyway — so its latency is free.
- The **clinician view** shows the judge's clinical classification. That is where
  the LLM's value actually lands, and nobody is watching a spinner for it.

This also means you can afford thinking-on quality for the clinician-facing note
while keeping the patient loop sub-second.

Both ASR calls run in parallel — two requests, roughly one request of wall time.
Cache the cue audio: the cue set is finite per word, so it prewarms like everything
else.

---

## What makes it stand out

Ranked by how memorable they are in a 2-minute demo:

1. **The same audio, two transcripts, two different verdicts.** Patient says
   ಪುತ್ತಕ. Standard ASR "helpfully" returns ಪುಸ್ತಕ and scores it **correct**.
   Verbatim keeps ಪುತ್ತಕ and the judge names the s/t substitution. *Verified — this
   is real, not a hypothetical.* One screen, no narration needed.
2. **The judge names the error like a clinician.** Not "wrong, 20% match" but
   "semantic paraphasia — produced the word for milk". That is the language the
   therapist already uses, which is what makes the output billable and trusted.
3. **The cue adapts to the error.** Show two attempts back to back: a semantic
   error gets a phonemic cue, a phonemic error gets a slow model. The app is
   visibly reasoning about *therapy*, not string distance.
4. **It waits.** Draw the 700ms mark on the live waveform, labelled "where a normal
   voice agent would have cut you off", and let the silence run past it. One line
   on a canvas that explains the entire accessibility thesis.
5. **Effortful-correct is its own category.** Reaching the word after three false
   starts is scored as progress, not as a failure — and the trend across sessions
   is the thing a clinician actually wants.

## Cut order if behind

The comparison (1) is the creativity proof — protect it above everything. Then the
error typing (2). The cue hierarchy (3) is the differentiator but is the first
thing to drop if the clock beats you. Fall back to: two transcripts side by side
with a rule-based verdict, and say honestly in the demo that the judge is next.
