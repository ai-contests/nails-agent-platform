#!/usr/bin/env bash
#
# Local dev launcher: FastAPI + Chat UI + Consumer C端 + Caddy
# Logs go to logs/<svc>.log. Ctrl-C stops everything.
#
# Routes after start-up:
#   http://localhost:8080/        → Chat UI       (demo/chat_app.py  :8501)
#   http://localhost:8080/user/   → C端 AI试戴   (demo_v1/app.py    :8503)
#   http://localhost:8080/api/    → FastAPI        (nails_agent       :8000)
#
# Direct access (no Caddy):
#   http://localhost:8501         → Chat UI
#   http://localhost:8503         → C端 AI试戴
#   http://localhost:8000         → FastAPI

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p logs

pids=()
cleanup() {
  echo
  echo "→ shutting down…"
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "→ starting FastAPI on :8000 (logs/api.log)"
uvicorn nails_agent.api.main:app --host 0.0.0.0 --port 8000 --reload \
  >logs/api.log 2>&1 &
pids+=($!)

echo "→ starting Chat UI on :8501 (logs/chat.log)"
NAILS_API_BASE="http://localhost:8000" \
streamlit run demo/chat_app.py --server.port 8501 --server.headless true \
  >logs/chat.log 2>&1 &
pids+=($!)

echo "→ starting C端 AI试戴 on :8503 (logs/consumer.log)"
NAILS_API_BASE="http://localhost:8000" \
streamlit run demo_v1/app.py --server.port 8503 --server.headless true \
  >logs/consumer.log 2>&1 &
pids+=($!)

if command -v caddy >/dev/null 2>&1; then
  echo "→ starting Caddy on :8080 (logs/caddy.log)"
  caddy run --config "$ROOT/Caddyfile" >logs/caddy.log 2>&1 &
  pids+=($!)
  echo
  echo "  Chat UI:   http://localhost:8080/"
  echo "  C端试戴:   http://localhost:8080/user/"
  echo "  API:       http://localhost:8080/api/health"
else
  echo "  (Caddy not installed — skipping reverse proxy. Access services directly:)"
  echo "  Chat UI:   http://localhost:8501/"
  echo "  C端试戴:   http://localhost:8503/"
  echo "  API:       http://localhost:8000/health"
fi
echo
echo "Press Ctrl-C to stop everything."
wait
