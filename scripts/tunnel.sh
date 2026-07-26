#!/usr/bin/env bash
# Public HTTPS tunnel to the local dev server, for demoing on a phone or over
# wifi. getUserMedia needs a secure context; localhost qualifies but a LAN IP
# does not, so "put it on the wifi" silently kills the mic without this.
#
# Usage: start the app first (uvicorn api:app --port 8000), then in a second
# terminal:
#   ./scripts/tunnel.sh
# Cloudflare prints a random https://*.trycloudflare.com URL — open that on
# the phone instead of the LAN IP.

set -euo pipefail
PORT="${1:-8000}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found. Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" >&2
  exit 1
fi

exec cloudflared tunnel --url "http://localhost:${PORT}"
