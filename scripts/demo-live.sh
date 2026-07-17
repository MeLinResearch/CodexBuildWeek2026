#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  printf '%s\n' 'OPENAI_API_KEY must be set for the live demo runtime' >&2
  exit 1
fi

codex_executable="${RELEASE_ASSURANCE_CODEX_EXECUTABLE:-codex}"
if ! resolved_codex_executable="$(command -v -- "$codex_executable")"; then
  printf 'Codex executable not found: %s\n' "$codex_executable" >&2
  exit 1
fi
"$resolved_codex_executable" --version

temporary_directory="$(mktemp -d)"
export RELEASE_ASSURANCE_DB_PATH="$temporary_directory/live.sqlite"
api_pid=""
web_pid=""

cleanup() {
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
  fi
  if [[ -n "$web_pid" ]] && kill -0 "$web_pid" 2>/dev/null; then
    kill "$web_pid" 2>/dev/null || true
  fi
  if [[ -n "$api_pid" ]]; then
    wait "$api_pid" 2>/dev/null || true
  fi
  if [[ -n "$web_pid" ]]; then
    wait "$web_pid" 2>/dev/null || true
  fi
  rm -rf -- "$temporary_directory"
}

trap cleanup EXIT INT TERM

python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 9001 &
api_pid=$!
(
  cd frontend
  bun run dev
) &
web_pid=$!

printf '%s\n' 'Live demo runtime starting'
printf '%s\n' 'Open http://127.0.0.1:9000 and choose Live GPT + Codex'
printf '%s\n' 'No paid model call occurs until the live button is clicked'

set +e
wait -n "$api_pid" "$web_pid"
status=$?
set -e
exit "$status"
