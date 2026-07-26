"""Retry wrapper for Sarvam calls — 429s are real under load.

Confirmed live during testing: TTS started returning 429 after heavy same-key
traffic (multiple testers + automated verification hitting the API back to
back) and cleared on its own after ~20-30s. Every Sarvam call in this codebase
went through `requests.post(...); resp.raise_for_status()` with zero retry —
one rate-limited call meant a crashed patient turn. This wraps that pattern.
"""

from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

_RETRY_STATUSES = {429, 502, 503, 504}


def post_with_retry(
    url: str,
    *,
    max_retries: int = 2,
    backoff_sec: float = 2.0,
    **kwargs,
) -> requests.Response:
    """`requests.post` that retries on 429/502/503/504, honoring a
    `Retry-After` header if the server sends one (Sarvam's 429 does, though
    conservatively — the observed real recovery time was ~20-30s under a
    sustained rate limit, not the 1s the header advertised). Raises on the
    final attempt same as a bare `requests.post` + `raise_for_status()` would.
    """
    last_resp = None
    for attempt in range(max_retries + 1):
        resp = requests.post(url, **kwargs)
        if resp.status_code not in _RETRY_STATUSES:
            if not resp.ok:
                log.error("%s -> %d: %s", url, resp.status_code, resp.text)
            resp.raise_for_status()
            return resp
        last_resp = resp
        if attempt < max_retries:
            wait = backoff_sec * (attempt + 1)
            retry_after = resp.headers.get("retry-after")
            if retry_after:
                try:
                    wait = max(wait, float(retry_after))
                except ValueError:
                    pass
            log.warning(
                "%s -> %d, retrying in %.1fs (attempt %d/%d)",
                url, resp.status_code, wait, attempt + 1, max_retries,
            )
            time.sleep(wait)
    log.error("%s -> %d after %d retries: %s", url, last_resp.status_code, max_retries, last_resp.text)
    last_resp.raise_for_status()
    return last_resp  # unreachable — raise_for_status always raises here
