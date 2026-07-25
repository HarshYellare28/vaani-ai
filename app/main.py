"""Standard FastAPI scaffold.

Deliberately generic: health check, env loading, and a static mount. All product
logic is written during the build sprint.

    uvicorn app.main:app --port 8000 --reload --reload-include '*.json'
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="buildathon")


@app.get("/health")
def health() -> dict:
    """Unauthenticated liveness probe — keep it that way for platform warmups."""
    return {"status": "ok"}


@app.get("/config")
def config() -> dict:
    """Whether the environment is wired up, without ever echoing the key itself."""
    return {"sarvam_key_present": bool(os.getenv("SARVAM_API_KEY"))}


# Mounted last so it cannot shadow the API routes above.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
