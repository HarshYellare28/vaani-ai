# Sarvam Epoch Buildathon — 26 Jul 2026

A between-visits speech practice tool for post-stroke aphasia. Word-target
drill: record an attempt, Saaras v3 transcribes it, the transcript is judged
against the target, Bulbul speaks feedback. See `SCOPE.md` for the product and
`JUDGE.md` for where this goes next (the LLM judge layer, SLP view).

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add the event Sarvam key
uvicorn api:app --port 8000 --reload --reload-include '*.json'
```

Open **http://localhost:8000**.

Use `localhost`, not the LAN IP: `getUserMedia` requires a secure context, and
`192.168.x.x` is not one, so the mic silently fails there. To demo on a phone
or over wifi, run `./scripts/tunnel.sh` in a second terminal for a public
HTTPS URL (Cloudflare quick tunnel) instead.

## Files

| File | What it is |
|---|---|
| `AGENTS.md` | Entry point for **any** assistant. Read first. |
| `SCOPE.md` | Product decisions, rubric targets, milestones, parking lot. |
| `DECISIONS.md` | Running log. Append as you go. |
| `docs/RUBRIC.md` | The organiser's actual L1–L5 ladders. GrowthX IP — keep private. |
| `docs/FIELD_NOTES.md` | Sarvam API gotchas learned the hard way. |
| `UI.md` | Design intent for anything user-facing. |
| `JUDGE.md` | The judge layer: verified API recipe, traps, architecture. |
| `api.py` | FastAPI app: drill endpoints + static mount. |
| `vaani/` | Sarvam ASR/TTS clients, matching, decisions, SQLite persistence. |
| `run_drill.py` | CLI to prompt/score a word against a WAV file, without the browser. |
| `scripts/tunnel.sh` | Public HTTPS tunnel (Cloudflare) for demoing off localhost. |

## Driving the build

Type a single word; the assistant does the rest.

| Command | What happens |
|---|---|
| `build` | Builds the next unticked milestone in `SCOPE.md`, runs its acceptance test, commits, then stops. |
| `status` | Where we are vs the schedule, largest risk, recommended cut. No changes. |
| `cut` | Proposes the smallest scope reduction that keeps a demonstrable path. |
| `demo` | Runs the golden path from a reset state as a judge would. |

## Switching assistants mid-build

Any harness — Claude Code, Codex, Cursor, a local model — starts the same way:

> Read AGENTS.md, SCOPE.md and the tail of DECISIONS.md, then `git log --oneline -15`.
> Tell me the active milestone and its acceptance test before changing anything.
