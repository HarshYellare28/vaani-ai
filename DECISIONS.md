# Decisions log

Append one line per real decision, newest at the bottom. This is what survives a
context reset, a model switch, or a new assistant — a summary drops specifics, this
does not.

Format: `HH:MM — decision — because reason`

Worth logging: an API shape that differs from the docs, a threshold you tuned, an
approach you rejected and why, anything a fresh assistant would otherwise redo.

---

- `09:xx` — scaffolding and scope prepared the night before; no application code
  written before the sprint — because pre-sprint implementation is "code written off
  the floor" and does not qualify.

- `11:20` — ported the tested Sarvam-only drill (ASR match → rule-based decision →
  TTS feedback) from `~/Projects/vaani` (`hackathon-sarvam` branch) as the M1
  starting point, instead of writing it from scratch — because that pipeline was
  already verified end-to-end against the Sarvam API and re-deriving it would burn
  sprint time on already-solved plumbing. Dropped all Azure Pronunciation
  Assessment shadow-scoring code during the port (config, schema columns, response
  fields) — SCOPE.md already locked Sarvam as the only scored Voice Experience
  surface, so Azure was dead weight. Re-verified live against the event key after
  the port: `run_drill.py prompt/score` round-tripped Bulbul → Saaras → judge →
  Bulbul, and the browser UI drove the same loop through `/prompt`. Next: SLP-first
  patient list view (attempts + judge score) on top of this, no auth yet.

- `12:0x` — added parallel `mode=transcribe` + `mode=verbatim` Saaras calls per
  attempt (M3 dual-transcript) — because SCOPE.md's creativity thesis and the
  locked demo moment depend on both existing per attempt, and the SLP list planned
  next is far more useful showing both than retrofitted later. Scoring still keys
  off the normalised (`transcribe`) transcript, not verbatim — disfluency repair is
  what makes correct/incorrect fair to the patient; verbatim is stored purely for
  the SLP record and never affects the decision. New `attempts.transcript_verbatim`
  column added via the existing additive migration — confirmed it applies cleanly
  to a DB from an earlier run. Verified live: clean "water" audio round-tripped
  transcribe="Water" / verbatim="water", both persisted.

- `13:0x` — root-caused the stuck patient screen: `rm -f vaani.db` from a step-0
  verification script deleted the file the live `--reload` server still had open,
  so `/users` 500'd on the missing table and the frontend's fetch failed silently,
  leaving the loading spinner permanently stuck — because `renderUsers()` never
  handled a failed fetch. Lesson: never delete a shared sqlite file while a server
  may be holding it live; use a throwaway path for scratch verification instead.
  Fixed forward per the actual ask: patient picker is now a `<select>` dropdown
  (searchable later) instead of a card grid backed by a `prompt()` popup — SLP
  picks from an already-enrolled roster, no typing on stage. Seeded 3 demo
  patients (`_SEED_PATIENTS` in db.py) via an additive migration, so it also
  top-up an existing DB that only had the old placeholder "Patient" row, not just
  a fresh one. `renderUsers()` now catches a failed `/users` fetch instead of
  throwing, so a backend error can't leave the loading spinner stuck again.

- `14:0x` — built SLP steps 1+2: clinician view (`static/slp.html`/`slp.js`,
  reachable directly, no auth) and single-row-per-patient assignments
  (`assignments` table, PK on `user_id`) — because the patient shouldn't be
  picking their own language/level/words; that choice belongs to the SLP.
  Removed the patient app's language and level picker screens entirely
  (`renderLanguages`/`chooseLanguage`/`renderLevels`/`chooseLevel` and the
  matching menu items) — `chooseUser()` now calls `loadAssignmentAndStart()`,
  which reads `GET /assignment` and either drops straight into the assigned
  group or shows a "no assignment yet" screen with a manual re-check button
  (no websocket/poll — SLP assigns, patient taps "Check again"). SLP's
  attempts table shows `transcript` (heard, scored) next to
  `transcript_verbatim`, with a visual flag when they differ — the M3 judge
  comparison, surfaced. Also improved the drill.py log line per request: heard
  (transcribe) and heard (verbatim) are now on separate lines with an explicit
  "differs from transcribe" marker, for reading off a terminal live.
  Verified end-to-end: assigned Vikram Nair (English L1 G1) from `/slp.html`,
  confirmed `/assignment` persisted, then loaded the patient app fresh — it
  skipped straight to the drill screen with the right words, and the menu no
  longer offers change-language/change-level.

- `14:3x` — added a second, independent passcode gate (`VAANI_SLP_PASS`,
  cookie `vaani_slp_auth`, login at `/slp/login`) scoped to just the clinician
  surface (`/slp.html`, `/slp.css`, `/slp.js`, `/languages`, `/levels`,
  `/assign`, `/patients/*/attempts`) — because /slp.html was reachable by
  anyone who could reach the patient app, and the general `VAANI_BASIC_PASS`
  doesn't distinguish patient from SLP. Layered on top of the existing
  passcode, not replacing it: a patient's passcode (if set) gets them into the
  app; it does not get them into the clinician view. Empty by default, so
  local dev stays exactly as before (both routes open) until it's set.
  Verified against a scratch server with `VAANI_SLP_PASS` set: `/slp.html` and
  `/languages` 401/redirect without the SLP cookie, `/` and `/users` (shared
  by the patient app) stay open, and the cookie granted by `/slp/login` opens
  both. Confirmed the running demo server (no `VAANI_SLP_PASS` in `.env` yet)
  is unaffected. Refactored `_LOGIN_PAGE` to take `action`/`title`/`subtitle`
  as real format args instead of the first draft's `.replace()` hack — that
  version worked but would've silently produced the wrong page on the next
  edit to the template.

- `15:0x` — built the dynamic mode (LLM-as-judge, the scored Sarvam parameter):
  `vaani/judge.py` wraps `sarvam-105b` per JUDGE.md's verified recipe
  (reasoning_effort=null, response_format json_schema strict, one retry on
  malformed/empty content) and does two things in one call — classifies the
  attempt's error type from the VERBATIM transcript against six categories
  (correct, effortful_correct, semantic/phonemic paraphasia, partial_groping,
  no_attempt), and picks the next word from a server-supplied candidate list
  it cannot deviate from (schema `enum` on next_word_id — never free-generates
  a word). The next-word policy is the four-row research mapping from
  aphasia_stroke_speech_research.md: switch category after 2 same-category
  misses, drop toward lower/higher-frequency words as errors trend, favor
  shorter words when duration is trending up, bump level after 2 consecutive
  corrects. Static mode is untouched — still scores locally on the transcribe
  transcript, zero LLM calls. `assignments`/`sessions` both got a `mode`
  column (additive migration); `/evaluate` reads mode from the session
  server-side (never trusts the client) and branches to
  `drill.evaluate_attempt_dynamic`, which is now genuinely on the blocking
  path — unlike JUDGE.md's original off-path design, the score itself depends
  on the judge in dynamic mode, so there's no cheap local stand-in to show
  first. Latency measured ~1-5s per call, acceptable given "the app waits" is
  already the product's own delight thesis.
  Prompt iteration (JUDGE.md warned to budget ≥2 rounds — took 3): (1) an
  empty verbatim transcript was getting classified as semantic_paraphasia
  instead of no_attempt — fixed with an explicit empty-string rule; (2)
  cue_hint leaked the prompt's own worked example verbatim regardless of the
  actual target word — fixed by banning example reuse and forcing per-target
  generation; (3) the phonemic_paraphasia cue was naming a sound borrowed from
  a candidate word instead of segmenting the actual target — fixed by
  replacing the "first sound" instruction with an explicit "segment target's
  own syllables" instruction, verified stable across 3 repeated trials after.
  Real (non-bug) finding from live testing: Saaras `mode=verbatim` transliterates
  clean English speech into Devanagari script (target "read", spoken cleanly,
  came back verbatim="रीट") while `mode=transcribe` correctly keeps it in Latin
  script — so an English attempt can verbatim-score as a phonemic error purely
  from a script mismatch, not an actual production error. Hindi has no such
  issue (both modes stay in Devanagari, verified against a clean "हड्डी"
  attempt). Demo dynamic mode in Hindi; treat English dynamic-mode scoring as
  unverified until Saaras's English-verbatim behavior is understood better.
  Frontend: patient app has no fixed word list in dynamic mode —
  `/session/start` returns a `first_word` (nearest-level candidate), each
  `/evaluate` response returns `next_word`, and the patient app just appends
  it to `state.words` (`nextWord()`'s existing index-increment logic needed no
  changes). Group sidebar and the "N / total" progress readout are hidden/
  adapted since dynamic mode has neither concept. SLP's assign form gained a
  Static/Dynamic toggle and the attempts table gained a Judge note column.
  Verified end-to-end through the real browser UI (not just curl): assigned
  both a Hindi and an English patient to dynamic mode from `/slp.html`, drove
  real recorded-equivalent attempts (fetched actual Bulbul TTS audio for the
  target word as the "attempt", since the preview browser can't grant mic
  permission), and confirmed correct classification, next-word selection,
  and UI advancement for both.

- `14:2x` — fixed a real dynamic-mode misjudgment caught in live testing: the
  judge called verbatim "Teeth" `correct` for target "tooth" (attempt id 22 in
  vaani.db) — a 60% string-similarity, clearly-different real word, marked
  correct. Root cause: the `correct` definition in judge.py's system prompt
  ("the target word, produced cleanly") didn't rule out morphological
  relatives, so the model was too permissive. Tightened it — "correct"
  requires verbatim to literally BE the target (explicit tooth/teeth
  counter-example inline), everything else routes to semantic_paraphasia at
  minimum. Re-verified: 3 stable trials on the exact tooth/teeth
  reproduction (was intermittently wrong, now consistently
  semantic_paraphasia), plus the full 5-case regression suite from the
  original prompt-tuning pass still passes. Left the two stale attempt rows
  (21, 22) in vaani.db uncorrected — didn't want to mutate what's meant to be
  an append-only record without asking; the fix applies going forward.

- `15:3x` — fixed a more serious judge misclassification, also caught live:
  target "cat", transcript AND transcript_verbatim both exactly "Cat" (100%
  string match), still classified `no_attempt` (attempt ids 40-41 in
  vaani.db). Root cause: the prompt separated "classify this attempt" from
  "pick next word using session_history" but never said history was
  *irrelevant* to classification — the model was pattern-matching the
  session's recent no_speech trend onto the current attempt and ignoring
  what heard_verbatim actually said. Added an explicit isolation rule:
  error_type comes ONLY from comparing heard_verbatim to target_word for
  THIS attempt; session_history is for step 2 (next word) only, never step
  1. Reproduced the exact failure (clean verbatim match + a history of prior
  no_speech results), confirmed it now returns `correct` in 3 stable trials,
  and reran the full regression suite (now 7 cases including this one and
  tooth/teeth) — all pass.

- `15:3x` — found and fixed a demo-killing judge bug during an outside-in audit.
  Symptom (reported as a TTS problem): "it says I didn't hear you and suddenly
  says <word>". Real cause: five consecutive live attempts (ids 38-42) where
  `transcript_verbatim` was exactly "Cat" against target "cat" — a perfect
  match — were classified `no_attempt`. Isolated it: same input with an EMPTY
  session_history classifies `correct` 3/3; with a history of `no_speech`
  results it classifies `no_attempt` 4/4. **The failure streak in
  session_history anchors the model and it repeats the trend**, overriding
  what it was actually shown. An explicit prompt rule forbidding exactly this
  was already present and did NOT hold — prompt-level guards are not
  sufficient here. Fixed in code, not prose: `judge_attempt` now runs
  `classify(verbatim, target)` BEFORE the call, passes the result in as
  `verified_matches_target`, and hard-overrides any paraphasia/no_attempt
  verdict back to `correct` when that flag is true (clearing cue_hint too).
  A normalised exact/near match to the target IS the target — not the model's
  call to overturn. Verified 4/4 fixed with real errors still caught
  (phonemic, semantic, no_attempt, tooth/teeth) and effortful_correct intact.
  Worth stating plainly: this was the worst possible failure mode for this
  product — the struggling patient is the target user, and the app was
  refusing to credit a correct answer *because* they had been struggling.

- `15:5x` — closed the cross-session memory gap flagged as a known cut: the
  dynamic judge's history was scoped to `session_id`, so a patient closing
  the app and coming back started the judge's trend-tracking from zero.
  Added `db.patient_recent_attempts(user_id, limit)` — same shape as the
  method it replaces, but joins through `sessions` on `user_id` instead of
  filtering by the one session in progress. Removed the now-unused
  `session_recent_attempts` (only caller was `/evaluate`'s dynamic branch,
  now pointed at the new method). No new persistence needed — sqlite already
  survives restarts, the gap was purely that the query never looked past the
  current session. Verified directly: created a session, recorded 2
  attempts, ended it, created a brand-new session for the same patient, and
  confirmed `patient_recent_attempts` returns both attempts from the closed
  session.

- `16:0x` — fixed a patient-facing display bug caught live: target "knife",
  screen showed "HEARD: Nice" next to a "Correct, 100%" badge — looked
  insane. Root cause: `renderResult()`'s "heard" field always showed
  `d.transcript` (transcribe), but dynamic mode scores on
  `transcript_verbatim` — the DB record showed transcribe genuinely heard
  "Nice" while verbatim correctly caught "Knife" (matching the earlier
  read→Hrid ASR-quirk pattern). The verdict was right; the display showed
  the transcript that *didn't* drive it. Fixed: `renderResult()` now shows
  `transcript_verbatim` in dynamic mode, `transcript` in static (unchanged,
  since that's what static actually scores on). Verified by replaying the
  exact reported case through `renderResult()` directly (transcribe="Nice",
  verbatim="Knife") — now displays "Knife" — and confirmed static mode is
  untouched.

<!-- append below -->
