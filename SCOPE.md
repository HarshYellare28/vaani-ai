# SCOPE.md — the control plane

Edit this as reality changes. Everything else defers to it.

---

## The product

**One sentence.** A between-visits speech practice tool for post-stroke aphasia in
Indian languages, where the model *judges* the patient's speech instead of
transcribing it politely.

| Decision | Locked answer |
|---|---|
| User | An adult with non-fluent (Broca's) aphasia, practising at home between clinic visits |
| Job completed | One practice session finished, with a per-attempt score the clinician can act on |
| Hard input | Real disordered speech — long pauses, partial words, self-corrections, code-switching |
| Final output | A scored session persisted against the patient, visible to their clinician |
| **Sarvam parameter (scored)** | **Voice Experience** — one only; extra APIs add zero points |
| Exact Sarvam surfaces | Saaras v3 (`mode=verbatim`), Bulbul v3, Sarvam LLM as judge |
| Language subset | Kannada + English. Hindi only if time allows |
| Creativity thesis | Standard ASR *repairs* disordered speech and destroys the clinical signal. Verbatim mode preserves it. We show both transcripts side by side |
| Delight thesis | The app waits. Default endpointing cuts off at ~700ms; a patient in word-retrieval pauses 3–5s. Never interrupting is the whole feeling |
| Memory boundary | A patient sees only their own history. A clinician sees their own patients only |
| Demo proof | Live: speak badly on purpose → verbatim keeps the disfluency, normalised mode hides it → judge scores it → session appears in the clinician view |
| Team advantage | Solo builder with months of domain research on aphasia + Indic speech |

**Non-goals.** Not a diagnosis tool. Not multi-clinic billing. Not a full EMR. No
account self-signup. No payments.

---

## Rubric target vector

Judges score five product parameters plus **one** Sarvam parameter, each L1–L5
independently. The same proof cannot raise two parameters.

| Parameter | Target | The proof that earns it |
|---|---|---|
| Voice Experience | L4 | Handles code-switched, disfluent Kannada/English without breaking the transcript; tolerates long silence; never talks over the patient |
| Job-to-be-done | L3–L4 | A complete scored session, repeatable on unseen input |
| Memory and Context | L4 | Prior attempts inform the next session; clinician sees carried history; no cross-patient leakage |
| Creativity | L4–L5 | Verbatim-vs-normalised comparison — non-obvious and visible |
| Impact | L3 | 2M living with aphasia in India vs ~3–6K therapists; a stated per-session number |
| Delight | L3–L4 | A first-time user completes a session without help |

---

## Milestones

Each has an acceptance test and a cut-down fallback. **Do not start N+1 before N
passes.** Tick the box when the acceptance test actually passes — `build` picks the
first unticked milestone, so this is the source of truth for where we are.

### [ ] M0 · 10:30–11:00 · De-risk before building
- Disclose the borderline starting point to a mentor. Get a name.
- Verify on the **event account**: Saaras v3 accepts `mode=verbatim`; Bulbul v3
  returns audio; the LLM surface is reachable. Check rate limits.
- **Accept:** a 200 response from each, from the event key, saved in `DECISIONS.md`.
- **If behind:** if verbatim is unavailable the creativity thesis changes — decide
  immediately, do not discover this at 15:00.

### [ ] M1 · 11:00–12:15 · One ugly end-to-end pass
Hardcode one word. Record in the browser, send to Saaras, compare to the target,
speak a reply with Bulbul. No styling, no database, no login.
- **Accept:** press a button, speak, hear a spoken judgement. Repeatable twice.
- **If behind:** drop TTS; show the judgement as text. Ship the loop.

### [ ] M2 · 12:15–13:30 · Word practice with real scoring
The drill from M1 over a small word list, with difficulty levels and a score per
attempt persisted to SQLite.
- **Accept:** finish a 5-word session; scores survive a page reload.
- **If behind:** one difficulty level, no levels UI.

### [ ] M3 · 13:30–14:45 · The judge and the comparison *(the scored axis)*
Run the same audio through `mode=verbatim` and `mode=transcribe`. Show both
transcripts. Sarvam LLM scores the attempt against the target with a reason.
- **Accept:** on deliberately disfluent speech, the two transcripts visibly differ
  and the judge explains its score.
- **If behind:** drop the LLM; show the two transcripts alone. The comparison *is*
  the creativity proof — protect it over everything else in this milestone.

### [ ] M4 · 14:45–15:30 · Patient and clinician continuity
Patient identity, session history, and a clinician view listing their patients with
per-patient progress.
- **Accept:** a returning patient's prior attempts are visible; a second patient
  cannot see the first's data.
- **If behind:** patient history only, no clinician view. History is the Memory
  proof; the dashboard is decoration.

### [ ] M5 · 15:30–16:30 · Demo hardening — **build nothing new**
Reset state. Run the golden path three times. Record the fallback video. Verify the
public link on a phone. Write submission notes including the borderline flag. Two
timed rehearsals against the clock.

---

## Demo script — 3 minutes, fixed format

- **0:00–0:30 · Business context.** 2M people living with aphasia in India,
  ~3–6K speech therapists. Practice between visits is where recovery happens, and
  it is exactly what does not happen.
- **0:30–1:00 · Current workflow and pain.** A paper word list and a family member
  guessing whether it sounded right. No record reaches the therapist.
- **1:00–3:00 · Live demo.** Speak a word cleanly → scored. Speak it with a real
  disfluency → *normal ASR silently fixes it; verbatim keeps it* → judge scores the
  actual production → session lands in the clinician view.

The verbatim-vs-normalised reveal is the moment. Land it by 2:00 at the latest.

---

## Parking lot — not today

Pediatric corpus · sentence frames and script therapy · offline mode · payments ·
clinic self-signup · WhatsApp nudges · Hindi corpus beyond a token set · fine-tuning
· κ validation study · pitch deck · Azure migration · full analytics dashboard.
