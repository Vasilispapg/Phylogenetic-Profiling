#!/usr/bin/env bash
# Start BOTH PhyloFlask dev servers together:
#   - Flask JSON API  → http://127.0.0.1:8000
#   - Vite React SPA  → http://localhost:5173
# The React app proxies /tools, /allvsall_*, /downloads, /upload … to the Flask API,
# so both must run. Without the API you get "Unexpected end of JSON input" in the UI.
# Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

# Kill the whole process group (both servers) when this script exits.
trap 'kill 0' EXIT

echo "→ Flask API   http://127.0.0.1:8000"
FLASK_DEBUG=0 PORT=8000 HOST=127.0.0.1 "$PY" app.py &

echo "→ React (dev) http://localhost:5173"
npm --prefix frontend run dev &

wait
