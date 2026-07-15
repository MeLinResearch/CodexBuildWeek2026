#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

api_pid=""
web_pid=""

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
  fi
  if [[ -n "$web_pid" ]] && kill -0 "$web_pid" 2>/dev/null; then
    kill "$web_pid" 2>/dev/null || true
  fi
  wait "$api_pid" 2>/dev/null || true
  wait "$web_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 9001 &
api_pid=$!
(
  cd frontend
  bun run dev
) &
web_pid=$!

set +e
wait -n "$api_pid" "$web_pid"
status=$?
set -e
exit "$status"
