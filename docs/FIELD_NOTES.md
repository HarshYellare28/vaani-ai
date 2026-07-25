# Sarvam field notes — things that cost hours to learn

Everything below was learned by running against the live Sarvam API on 25 Jul 2026.
This is **knowledge, not code**. Read it, then write fresh code on the floor.

> Rule check: helper knowledge in your head is yours. Copying implementation
> written before the sprint is "code written off the floor" and does not qualify.
> Retype from understanding; do not paste.

---

## 1. API gotchas that produce confusing errors

**Speaker names are model-versioned.** `anushka` is a `bulbul:v2` voice and returns
HTTP 400 against `bulbul:v3`. The v3 set is: aditya, ritu, ashutosh, priya, neha,
rahul, pooja, rohan, simran, kavya, amit, dev, ishita, shreya, ratan, varun, manan,
sumit, roopa, kabir, aayan, shubh, advait, anand, tanya, tarun. The error message
does list the valid set — read it rather than guessing.

**`en-US` is rejected.** Sarvam takes `en-IN`. Any English variant has to be mapped
before the call. Indic codes (`kn-IN`, `hi-IN`, `ta-IN`, `te-IN` …) pass through.

**Saaras v3 has a `mode` parameter** — `transcribe` (default) | `verbatim` |
`codemix` | `translit` | `translate`. `verbatim` preserves disfluencies and fillers
instead of cleaning them up. For any clinical, assessment, or coaching use case this
is the difference between signal and noise. Default `transcribe` silently repairs
what the speaker actually said.

**Throttling does not return 429 — it stalls.** Sustained parallel requests make the
API hang until the client timeout. The identical text succeeds in ~1.4s seconds
later. Keep concurrency at **3 or below** and retry with backoff. If things feel
slow mid-demo, back off rather than retrying harder.

**Latency, measured:** TTS 0.8–3.2s depending on length; ASR 0.3–3.0s. Both are
jittery — a 0.5s call can spike to 3s on the same input. Never promise "realtime"
without measuring on the venue network.

---

## 2. The single biggest performance win: cache TTS

Each Bulbul call is a 2–3s round trip. In a judge-then-speak flow it lands *after*
ASR, i.e. squarely inside the user's wait. Most apps re-synthesise identical strings
forever — an invariant success line is byte-identical on every success.

- Key the cache on **model | language | speaker | pace | text**. Anything that
  changes the audio must be in the key, or changing voice serves stale audio.
- Write to a temp file and `os.replace` it into position. A half-written WAV from a
  crash is otherwise a permanent cache hit.
- **Pre-generate the finite set before demoing.** 37 clips took ~20s. Measured
  effect: prompt playback 1.0s → 0.00s, full judge round trip 3–5s → 0.35–0.85s.
- What remains is ASR, which is per-utterance audio and genuinely uncacheable.

Corollary: any finite corpus (prompts, menu options, confirmations) should be warmed
at startup, not synthesised on demand.

---

## 3. Browser audio

**`getUserMedia` needs a secure context.** `localhost` qualifies; `192.168.x.x` does
not. "Put it on the wifi so everyone can try it" silently kills the mic. Public HTTPS
means a real deploy or a tunnel.

**AudioWorklet frames can feed two consumers.** The worklet posts `Float32Array`
frames to the main thread for WAV encoding; the same frames drive a live waveform for
free. RMS per frame → one bar is steadier to look at than raw samples, and it makes
long silences read as *listening* rather than as a frozen app.

**Encode 16 kHz mono 16-bit PCM in the browser.** That is what Sarvam wants, so no
server-side ffmpeg step is needed.

---

## 4. Indic text handling

**Do not hardcode Devanagari.** The trap is writing `0x0900–0x097F` or `/[ऀ-ॿ]/`,
which silently degrades every other Indic script — no error, just wrong output.

- Script range covering Devanagari → Malayalam: **U+0900–U+0D7F**.
- Identify a virama/halant in *any* Brahmic script by **canonical combining class 9**
  (`unicodedata.combining(ch) == 9`). No per-script table needed.
- Syllable (akshara) segmentation: accumulate combining marks (`Mn`/`Mc`) onto the
  current cluster, and continue the cluster when the previous char was a virama.
  Verified on Hindi, Kannada, Tamil, Telugu.

**Normalise before comparing ASR output to expected text.** Sarvam appends
punctuation (`.`, `।`). NFC-normalise, strip Unicode category `P`, strip whitespace,
casefold. In Hindi treat `ँ` and `ं` as interchangeable. Without this, a perfect
match fails on a trailing full stop.

**Machine translation needs review before shipping as UI copy.** Sarvam Translate is
a good bootstrap but produced, in one pass: a **Telugu character inside Kannada
text**, "match" → the sports sense, "session" → the legislative sense, and informal
imperatives where an app addressing an adult wants polite forms. Generate, then have
a speaker check, or keep the surface small enough to verify.

**Show a gloss line.** Rendering `romanization · english` under a native-script word
lets someone who cannot read the script demo it confidently.

---

## 5. Front-end traps

**`<button>` does not inherit `color`.** It falls back to the UA's `buttontext`
(black). This looks correct on light surfaces and turns card labels near-invisible
the moment a dark theme exists. Set `button { color: inherit }` early.

**Name the Indic font families explicitly.** A stack listing only
`Noto Sans Devanagari` drops Kannada/Tamil/Telugu to a generic fallback that renders
vowel signs and conjuncts badly. Both Android and iOS ship Indic fonts, so system
fonts are fine — no webfont download needed.

**An animation driven by `requestAnimationFrame` must degrade to the true value.**
rAF does not fire in a page the browser is not painting. If the animation *is* how
the number arrives, a throttled tab shows `0%` for an 89% result — silently wrong,
which is worse than not animating. Write the real value synchronously, and only
rewind inside the rAF callback. Back it with a timer in case the run dies mid-flight.

**`<use href="#sprite">` icons**: make them stroke-only and inherit `currentColor`,
then one CSS rule sizes and colours the whole set. Emoji-as-icons render differently
on every OS and read as unfinished.

---

## 6. Voice UX for atypical speech

- **Default endpointing is wrong for disordered speech.** Voice pipelines cut off
  after ~700ms of silence; someone in word-retrieval pauses 3–5s. Long silence must
  be treated as sacred, never as end-of-turn. This is pipeline configuration, not
  model fine-tuning — a much cheaper win than it looks.
- **Keep spoken feedback short, and put the target word last.** Two-clause feedback
  ran 6.1s; one clause ran 3.6s. Pace barely helps (0.7 → 1.0 only moves 6.1s →
  4.6s) — length dominates. Word-last means the last thing heard is the thing to
  imitate, and there is less to hold in working memory.

---

## 7. Rubric-shaped strategy notes

Read from the bundled rubric, not invented:

- **Voice Experience is scored on conversation**: accents, Hindi-English
  code-switching, noisy lines, barge-in, emotional read, pacing that shifts, and
  follow-ups that build on the last answer. A fixed prompt→response loop, however
  polished, tops out around L2–L3 because there is no turn-taking to evaluate.
- **Memory and Context is a separate axis** and explicitly *not* conversational
  flow. It wants persisted, governed continuity: identity, prior history,
  corrections that propagate, and no leakage across users. Cross-session history
  is L4; business rules plus permission boundaries is L5.
- **The same proof cannot raise two parameters.** Assign each demo moment to one.
- Judges score **one** Sarvam capability. Extra APIs add zero. Depth beats breadth.
- Timings: commit to a problem by **11:30**, something running by **12:15**.
