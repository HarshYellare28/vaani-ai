# Sarvam Epoch Buildathon — 26 Jul 2026

Standard FastAPI scaffold plus the control-plane docs. **No product code yet** —
that gets written during the sprint.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add the event Sarvam key
uvicorn app.main:app --port 8000 --reload --reload-include '*.json'
```

Open **http://localhost:8000** — it should say `health: ok · sarvam key: loaded`.

Use `localhost`, not the LAN IP: `getUserMedia` requires a secure context, and
`192.168.x.x` is not one, so the mic silently fails there.

## Files

| File | What it is |
|---|---|
| `AGENTS.md` | Entry point for **any** assistant. Read first. |
| `SCOPE.md` | Product decisions, rubric targets, milestones, parking lot. |
| `DECISIONS.md` | Running log. Append as you go. |
| `docs/FIELD_NOTES.md` | Sarvam API gotchas learned the hard way. |
| `app/main.py` | Generic scaffold: health, config, static mount. |

## Switching assistants mid-build

Any harness — Claude Code, Codex, Cursor, a local model — starts the same way:

> Read AGENTS.md, SCOPE.md and the tail of DECISIONS.md, then `git log --oneline -15`.
> Tell me the active milestone and its acceptance test before changing anything.

## Provenance

From-scratch build on the day. The builder has prior work in this problem domain,
disclosed to a mentor before the sprint. Scaffolding, helper services and AI coding
assistants are explicitly permitted; copied implementation is not.
