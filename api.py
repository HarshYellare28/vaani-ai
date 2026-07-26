"""FastAPI surface — serves the web app and the drill API (Sarvam-only).

Run:  uvicorn api:app --reload --host 0.0.0.0 --port 8000
Then open http://localhost:8000  (localhost is a secure context, so the mic works)

Patient flow: pick user → play the assigned drill (no picker; see /assignment).
Clinician flow (/slp.html): pick a patient → assign language/level/group,
static or dynamic → review attempts with both transcripts + judge notes.
Gated separately — see VAANI_SLP_PASS.

Two judging modes, set per-assignment (see JUDGE.md, vaani/judge.py):
  static  — fixed word list, scored locally against the transcribe
            transcript. Repeat-practice, no LLM, instant.
  dynamic — no fixed list; scored by sarvam-105b against the VERBATIM
            transcript, which also picks each next word from the patient's
            error/duration trend (vaani/judge.py's research-mapped policy).
            On the blocking path — the score itself depends on the judge.

API:
  GET  /users                                -> patient list
  POST /users                                -> create patient {name}
  GET  /languages                            -> available languages + word counts   [clinician]
  GET  /levels?language=hi-IN                -> levels for a language + word counts  [clinician]
  GET  /groups?language=hi-IN&level=1&user_id=1  -> groups with per-user scores
  GET  /words?language=hi-IN&level=1&group=1 -> drill words (optionally filtered)
  POST /assign                               -> set a patient's assignment {mode: static|dynamic} [clinician]
  GET  /assignment?user_id=1                 -> a patient's current assignment (or {})
  GET  /patients/{user_id}/attempts          -> a patient's attempts, both transcripts + judge notes [clinician]
  POST /session/start                        -> {session_id, mode, first_word}  (form: language, level, user_id, group_num)
                                                 first_word is set only when the assignment's mode is dynamic
  POST /session/{id}/end                     -> session summary
  POST /prompt                               -> WAV audio of a target word
  POST /evaluate                             -> assessment + decision + feedback (persisted)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles

from vaani import Config, Database, StaticDrill, setup_logging
from vaani.i18n import load_locales

setup_logging()
config = Config.from_env()
drill = StaticDrill(config)
db = Database(config.db_path)
db.seed_words()   # idempotent (seed_users runs inside Database.__init__)

app = FastAPI(title="Vaani", version="0.1.0")

# ── Passcode gate (set VAANI_BASIC_PASS in env to enable) ─────────────
# Cookie-based, not HTTP Basic: the browser's Basic-auth dialog is unreliable
# with fetch()/XHR (it re-prompts on every API call). A signed cookie set once
# at /login rides along on every fetch + audio request automatically. Useful
# once the app is exposed via a public tunnel for the demo.
_BASIC_PASS = os.getenv("VAANI_BASIC_PASS", "")
_COOKIE_NAME = "vaani_auth"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
# Paths reachable without a valid cookie.
_OPEN_PATHS = {"/health", "/login", "/slp/login"}


def _expected_token() -> str:
    """Cookie value = HMAC(passcode, constant). Can't be forged without the passcode."""
    return hmac.new(_BASIC_PASS.encode(), b"vaani-authenticated", hashlib.sha256).hexdigest()


def _is_authed(request: Request) -> bool:
    if not _BASIC_PASS:
        return True
    token = request.cookies.get(_COOKIE_NAME, "")
    return secrets.compare_digest(token, _expected_token())


# ── Second, independent gate for the clinician surface (set VAANI_SLP_PASS) ──
# The patient passcode above (if set) just gets you into the app at all — it
# doesn't distinguish patient from SLP, so a patient who has it could still
# browse to /slp.html. This is a separate cookie/passcode layered on top of
# specifically the clinician paths, so a patient device never needs to know
# it and a leaked patient passcode can't expose other patients' attempts.
_SLP_PASS = os.getenv("VAANI_SLP_PASS", "")
_SLP_COOKIE_NAME = "vaani_slp_auth"


def _slp_expected_token() -> str:
    return hmac.new(_SLP_PASS.encode(), b"vaani-slp-authenticated", hashlib.sha256).hexdigest()


def _is_slp_authed(request: Request) -> bool:
    if not _SLP_PASS:
        return True
    token = request.cookies.get(_SLP_COOKIE_NAME, "")
    return secrets.compare_digest(token, _slp_expected_token())


def _is_slp_path(path: str) -> bool:
    """Clinician-only surface: the dashboard page/assets, and the API
    endpoints that expose or change data across patients. Everything else
    (/, /users, /groups, /assignment, /prompt, /evaluate, ...) stays on the
    ordinary patient passcode — the patient app itself depends on those."""
    if path in ("/slp.html", "/slp.css", "/slp.js", "/languages", "/levels", "/assign"):
        return True
    return path.startswith("/patients/")


_LOGIN_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vaani — Sign in</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; min-height:100vh; display:grid; place-items:center;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: linear-gradient(160deg,#eef2ff,#faf5ff); color:#1e1b4b; }}
  .card {{ background:#fff; padding:2rem 1.75rem; border-radius:18px;
    box-shadow:0 12px 40px rgba(79,70,229,.15); width:min(360px,92vw); text-align:center; }}
  .logo {{ font-size:2.25rem; }}
  h1 {{ font-size:1.4rem; margin:.4rem 0 .15rem; }}
  p.sub {{ margin:0 0 1.4rem; color:#6b7280; font-size:.9rem; }}
  input {{ width:100%; padding:.8rem .9rem; font-size:1.05rem; text-align:center;
    border:1.5px solid #ddd6fe; border-radius:12px; outline:none; }}
  input:focus {{ border-color:#6366f1; }}
  button {{ width:100%; margin-top:.9rem; padding:.8rem; font-size:1.05rem; font-weight:600;
    color:#fff; background:#6366f1; border:none; border-radius:12px; cursor:pointer; }}
  button:hover {{ background:#4f46e5; }}
  .err {{ color:#dc2626; font-size:.88rem; margin-top:.8rem; min-height:1.1em; }}
</style></head>
<body>
  <form class="card" method="post" action="{action}">
    <div class="logo">🗣️</div>
    <h1>{title}</h1>
    <p class="sub">{subtitle}</p>
    <input name="passcode" type="password" autofocus autocomplete="current-password"
           placeholder="Passcode" required>
    <button type="submit">Enter</button>
    <div class="err">{error}</div>
  </form>
</body></html>"""


@app.get("/login")
def login_page():
    return HTMLResponse(_LOGIN_PAGE.format(
        action="/login", title="Vaani", subtitle="Enter passcode", error="",
    ))


@app.post("/login")
def login_submit(passcode: str = Form(...)):
    if _BASIC_PASS and secrets.compare_digest(passcode.encode(), _BASIC_PASS.encode()):
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(
            _COOKIE_NAME, _expected_token(),
            max_age=_COOKIE_MAX_AGE, httponly=True, secure=True, samesite="lax",
        )
        return resp
    return HTMLResponse(
        _LOGIN_PAGE.format(
            action="/login", title="Vaani", subtitle="Enter passcode",
            error="Wrong passcode",
        ),
        status_code=401,
    )


@app.get("/slp/login")
def slp_login_page():
    return HTMLResponse(_LOGIN_PAGE.format(
        action="/slp/login", title="Vaani · Clinician",
        subtitle="Enter clinician passcode", error="",
    ))


@app.post("/slp/login")
def slp_login_submit(passcode: str = Form(...)):
    if _SLP_PASS and secrets.compare_digest(passcode.encode(), _SLP_PASS.encode()):
        resp = RedirectResponse("/slp.html", status_code=303)
        resp.set_cookie(
            _SLP_COOKIE_NAME, _slp_expected_token(),
            max_age=_COOKIE_MAX_AGE, httponly=True, secure=True, samesite="lax",
        )
        return resp
    return HTMLResponse(
        _LOGIN_PAGE.format(
            action="/slp/login", title="Vaani · Clinician",
            subtitle="Enter clinician passcode", error="Wrong passcode",
        ),
        status_code=401,
    )


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    path = request.url.path
    accept = request.headers.get("accept", "")
    is_get_html = request.method == "GET" and "text/html" in accept

    if path not in _OPEN_PATHS and not _is_authed(request):
        # Unauthenticated. Send browser navigations to the login page; APIs get JSON.
        if is_get_html:
            return RedirectResponse("/login", status_code=303)
        return JSONResponse({"detail": "unauthorized"}, status_code=401)

    if _is_slp_path(path) and not _is_slp_authed(request):
        if is_get_html:
            return RedirectResponse("/slp/login", status_code=303)
        return JSONResponse({"detail": "unauthorized"}, status_code=401)

    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/i18n")
def i18n():
    """The full locale table — UI strings, level names, badges, metadata.
    The front-end picks a locale from this and flips the whole UI."""
    return load_locales()


# ── users ──────────────────────────────────────────────────────────────
@app.get("/users")
def users_list():
    return db.list_users()


@app.post("/users")
def users_create(name: str = Form(...)):
    user_id = db.create_user(name)
    return {"user_id": user_id, "name": name}


# ── SLP: assignment + attempts (clinician view, no picker for the patient) ──
@app.post("/assign")
def assign(
    user_id: int = Form(...),
    language: str = Form(...),
    level: int = Form(...),
    group_num: int = Form(...),
    mode: str = Form("static"),
):
    db.set_assignment(user_id, language, level, group_num, mode)
    return {"ok": True}


@app.get("/assignment")
def assignment(user_id: int):
    return db.get_assignment(user_id) or {}


@app.get("/patients/{user_id}/attempts")
def patient_attempts(user_id: int, limit: int = 100):
    return db.list_attempts(user_id, limit)


# ── data ──────────────────────────────────────────────────────────────
@app.get("/languages")
def languages():
    return db.languages()


@app.get("/levels")
def levels(language: str):
    return db.levels(language)


@app.get("/groups")
def groups(language: str, level: int, user_id: int):
    return db.groups(language, level, user_id)


@app.get("/words")
def words(language: str | None = None, level: int | None = None, group: int | None = None):
    return db.list_words(language, level, group)


# ── session lifecycle ──────────────────────────────────────────────────
@app.post("/session/start")
def session_start(
    language: str = Form(None),
    level: int = Form(None),
    user_id: int = Form(None),
    group_num: int = Form(None),
):
    """Mode comes from the patient's assignment, not the client — the
    frontend never gets to pick dynamic mode for itself. Dynamic sessions
    additionally return `first_word`, since there's no fixed word list to
    fetch from /words; the patient app appends to its own list from there."""
    a = db.get_assignment(user_id) if user_id else None
    mode = a["mode"] if a else "static"
    session_id = db.create_session(language, level, user_id, group_num, mode)

    first_word = None
    if mode == "dynamic":
        candidates = db.candidate_words(language, user_id, exclude_word_id=None, limit=8)
        if candidates:
            target_level = level or 1
            first_word = min(candidates, key=lambda w: abs((w["level"] or 1) - target_level))

    return {"session_id": session_id, "mode": mode, "first_word": first_word}


@app.post("/session/{session_id}/end")
def session_end(session_id: int):
    db.end_session(session_id)
    return {"session_id": session_id, "summary": db.session_summary(session_id)}


# ── drill ───────────────────────────────────────────────────────────────
@app.post("/prompt")
def prompt(word: str = Form(...), lang: str = Form("hi-IN")):
    """Synthesize and return the spoken target word as a WAV."""
    path = drill.prompt_word(word, language_code=lang)
    return FileResponse(path, media_type="audio/wav", filename="prompt.wav")


@app.post("/evaluate")
async def evaluate(
    word: str = Form(...),
    session_id: int = Form(...),
    language: str = Form("hi-IN"),
    word_id: int | None = Form(None),
    attempt: UploadFile = File(...),
):
    """Judge one recorded attempt, persist it, return assessment + feedback.

    Mode is read from the session (server-authoritative, not client-supplied):
    static scores against the transcribe transcript with a fixed word list;
    dynamic scores against the verbatim transcript via the LLM judge, which
    also picks the next word — returned as `next_word` since dynamic mode has
    no fixed list for the client to walk.
    """
    session = db.get_session(session_id)
    mode = session["mode"] if session else "static"

    tmp_path = f"/tmp/attempt_{int(time.time() * 1000)}.wav"
    next_word = None
    try:
        with open(tmp_path, "wb") as f:
            f.write(await attempt.read())
        if mode == "dynamic":
            user_id = session["user_id"]
            candidates = db.candidate_words(language, user_id, exclude_word_id=word_id, limit=8)
            history = db.session_recent_attempts(session_id, limit=5)
            result = drill.evaluate_attempt_dynamic(
                word, tmp_path, language=language,
                candidates=candidates, session_history=history,
            )
            next_word = next(
                (c for c in candidates if c["id"] == result.assessment.judge_next_word_id), None,
            )
        else:
            result = drill.evaluate_attempt(word, tmp_path, language=language)
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
    a, d = result.assessment, result.decision

    attempt_id = db.record_attempt(session_id, a, d, word_id=word_id)

    with open(result.feedback_audio_path, "rb") as f:
        feedback_b64 = base64.b64encode(f.read()).decode()

    return JSONResponse({
        "attempt_id": attempt_id,
        "target_word": a.target_word,
        "transcript": a.transcript,
        "transcript_verbatim": a.transcript_verbatim,
        "result_label": a.result_label,
        "correct": a.correct,
        "similarity": round(a.similarity, 2),
        "audio_duration_sec": a.audio_duration_sec,
        "language_detected": a.language_detected,
        "language_probability": a.language_probability,
        "judge_error_type": a.judge_error_type,
        "judge_note": a.judge_note,
        "cue_hint": result.cue_hint,  # dynamic mode retry cue; "" if correct or static mode
        "next_word": next_word,  # dynamic mode only; null otherwise (or if candidates ran out)
        "decision": {
            "action": d.action.value,
            "feedback_text": d.feedback_text,
        },
        "feedback_audio_wav_b64": feedback_b64,
    })


# ── static web app (mounted last so it doesn't shadow the API routes) ───
app.mount("/", StaticFiles(directory="static", html=True), name="static")
