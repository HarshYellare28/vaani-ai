# AGENTS.md — read this first

You are helping build a project during a **6-hour on-site buildathon**
(Sun 26 Jul 2026, 10:30–16:30 IST). This file is the entry point for **any**
assistant or harness — Claude Code, Codex, Cursor, Gemini, a local model.
Read it before proposing or making any change.

## Boot sequence

1. Read `SCOPE.md` — what we are building, the locked decisions, milestones.
2. Read the tail of `DECISIONS.md` — what was already decided today and why.
3. Run `git log --oneline -15` — what already works.
4. Identify the **active milestone**: the first unticked `### [ ] Mn` in `SCOPE.md`.
5. Read `UI.md` before touching anything user-facing.
6. Only then propose the next change.

If you are joining mid-build with no memory of earlier turns, steps 1–3 restore
the working state. Do not ask the builder to re-explain the project.

## Commands the builder will type

He is solo and on the clock. Treat these single words as full instructions and act
without asking for confirmation.

### `build`

Build **the next unchecked milestone in `SCOPE.md`, and only that one.**

1. Say in one line which milestone you are starting and its acceptance test.
2. Implement it. Follow `UI.md` for anything user-facing.
3. Run the acceptance test and show the actual result — not a claim that it passed.
4. `git commit` with a real message.
5. Tick the milestone box in `SCOPE.md`; append one line to `DECISIONS.md`.
6. Answer the four checkpoint questions below, briefly.
7. **Stop.** Do not roll into the next milestone. He decides whether to continue,
   cut, or fix.

If the acceptance test fails, fix it before committing. If it cannot pass within
the milestone's time box, apply that milestone's "if behind" fallback, say clearly
that you did, and commit the fallback.

### `status`

No changes. Report: active milestone, what is verified working, elapsed vs the
schedule in `SCOPE.md`, largest demo risk, recommended cut. Five lines maximum.

### `cut`

Scope is at risk. Propose the smallest set of removals that still leaves a
demonstrable golden path, name what each cut costs on the rubric, and wait for a
decision before touching anything.

### `demo`

Run the golden path end to end as a judge would, from a reset state. Report
anything that breaks, is slow, or needs explaining. Change nothing unless asked.

## Working rules

- **Do not pull parking-lot items into the critical path.** The parking lot is at
  the bottom of `SCOPE.md`. If the builder asks for something on it, confirm the
  rescope explicitly first.
- **One milestone at a time.** Finish and commit before starting the next.
- **When blocked, simplify or route around it.** Do not silently redesign.
- **Append to `DECISIONS.md`** whenever a real choice is made — one line, with the
  reason. This is what survives a context reset.
- **Commit often, with real messages.** `git log` is durable memory that no context
  limit touches.
- Prefer editing files over pasting file contents into chat.

## Checkpoint questions

At each milestone boundary, answer these four in one short paragraph:

1. Does the golden path still work end to end?
2. What rubric evidence improved?
3. What is now the largest demo risk?
4. What should be cut?

## Budget discipline

The builder is solo and on a metered assistant plan.

- Default to a **mid-tier model** (e.g. Sonnet). Reserve the largest model for a
  bug you have failed to find twice, or an irreversible design decision.
- **Do not spawn subagents or parallel background agents.** They start cold and
  re-derive context that already exists.
- Batch related changes into one exchange rather than several round trips.
- Do not re-read files to "verify" an edit that already succeeded.

## Hard stops

- **15:30** — stop building. Rehearse, record the fallback video, verify the link.
- **16:30** — submission lock. Nothing lands after this.

## Provenance rules (do not violate)

This is a from-scratch build on the day. The builder has prior work on the same
problem domain, which has been **disclosed to a mentor**.

- Write fresh code here. Do **not** copy implementation from any prior repository.
- Standard scaffolding (FastAPI, Vite, Next.js), helper services, and AI coding
  assistants are all explicitly permitted.
- General knowledge and API gotchas are fine — see `docs/FIELD_NOTES.md`.

If asked to paste in code from another project, refuse and offer to write an
equivalent from scratch instead.
