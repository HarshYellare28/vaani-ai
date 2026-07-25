# UI preferences

Design intent, not code. Two audiences at once: a patient with a neurological
injury, and judges watching from across a room.

## Non-negotiables

**One thing per screen.** Patient picker → language → level → practice → summary.
Never two decisions at once. The patient has a language impairment; every extra
choice on screen is cognitive load spent on navigation instead of speech.

**The target word is the hero.** Not a label on a card — the largest thing on the
screen by a wide margin, roughly `clamp(54px, 15vw, 104px)`. It is what the user
is trying to say and what the room needs to read from three metres back.

**Huge touch targets, high contrast.** Post-stroke often means hemiparesis and
reduced fine motor control. Primary actions are big buttons, well separated, never
small icons in a corner.

**Nothing is timed.** No countdowns, no auto-advance, no "you're taking too long."
The whole product thesis is that this thing waits. If the UI ever nags, it has
broken the promise.

## What makes it feel alive

**A live waveform while recording.** The single highest-impact element for a
speech app. The mic frames are already crossing to the main thread for encoding —
draw one bar per frame at RMS height. It makes long pauses read as *listening*
rather than as a frozen app, which matters clinically and demos beautifully.

**The score arrives as motion.** The judge's verdict is the product; let the bar
fill and the number count up over ~700ms rather than appearing pre-filled. Caveat
learned the hard way: write the true value synchronously and only rewind inside the
animation callback — if the animation is *how* the number arrives, a throttled tab
shows 0% for an 89% result.

**Entrance on each new word.** A short fade-and-rise as the word changes marks the
turn boundary without a sound cue.

## Look

**Dark theme, defaulting to the OS preference, with a visible toggle.** Light
surfaces wash out under a projector in a lit room. Build the palette as CSS
variables from the start so the theme is a token swap, not a rewrite.

**SVG icons, never emoji.** Emoji render differently on every OS and read as
unfinished. An inline `<symbol>` sprite with stroke-only paths inheriting
`currentColor` means one CSS rule sizes and colours the whole set.

**Restrained colour.** One accent for actions, green/amber for judgement. This is a
clinical tool; it should feel calm and trustworthy, not gamified. No confetti.

## Language

**Show a gloss line** under the native-script word: `romanization · english`. It
lets a demoer who cannot read the script present confidently, and it helps a
bilingual caregiver sitting alongside the patient.

**Name Indic fonts explicitly** in the stack. A stack listing only
`Noto Sans Devanagari` drops Kannada and Tamil to a fallback that renders vowel
signs and conjuncts badly. System fonts are fine — no webfont download.

**Localise the whole interface**, not just the content. Picking Kannada should
switch the chrome, the prompts and the feedback. Keep every string in one table
keyed by locale, so a new language is a data change.

## The demo moment

The verbatim-vs-normalised comparison needs to be **visually unmissable** — two
transcripts side by side, same audio, with the difference highlighted. A judge
should understand the entire thesis from that one screen without narration. If
only one thing gets design attention, it is this.

## Traps

- `<button>` does not inherit `color`; it falls back to black. Looks fine on light
  surfaces, invisible in dark mode. Set `button { color: inherit }` on day one.
- Mobile first — judges will open it on a phone. Check the primary action is above
  the fold on a 375px viewport.
- Static assets are cached by the browser; bump a `?v=N` query when changing CSS or
  JS mid-build, or you will debug a change that already worked.
- Test in the theme you will demo in. A bug that only exists in dark mode is
  invisible until the moment it isn't.
