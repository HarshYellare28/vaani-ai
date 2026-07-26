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

<!-- append below -->
