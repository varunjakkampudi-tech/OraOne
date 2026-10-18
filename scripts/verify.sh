#!/usr/bin/env bash
# OraOne test gate. Runs every check in order and stops at the first failure with a non-zero exit.
#
#   1. backend: ruff check, ruff format --check
#   2. backend: pytest -m "smoke or critical", then the full backend suite (regression)
#   3. frontend: typecheck, eslint, prettier check, vitest
#
# Works in Git Bash on Windows and on Linux. Backend tools come from backend/.venv when it
# exists (Scripts/ on Windows, bin/ elsewhere), otherwise from the python on PATH.
# Usage: bash scripts/verify.sh

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

if [ -x "$BACKEND/.venv/Scripts/python.exe" ]; then
  PY="$BACKEND/.venv/Scripts/python.exe"
elif [ -x "$BACKEND/.venv/bin/python" ]; then
  PY="$BACKEND/.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PY="python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "verify: no Python interpreter found. Create backend/.venv or install Python 3.12." >&2
  exit 1
fi

if command -v bun >/dev/null 2>&1; then
  RUN="bun run"
elif command -v npm >/dev/null 2>&1; then
  RUN="npm run"
else
  echo "verify: neither bun nor npm is on PATH." >&2
  exit 1
fi

step() {
  echo
  echo "==> $1"
}

fail() {
  echo
  echo "verify: FAILED at: $1" >&2
  exit 1
}

# Runs one command; on failure, names the step and exits.
run() {
  local name="$1"
  shift
  step "$name"
  if ! "$@"; then
    fail "$name"
  fi
}

cd "$ROOT" || exit 1

# ───────────── backend static checks ─────────────
run "backend: ruff check" bash -c "cd \"$BACKEND\" && \"$PY\" -m ruff check ."
run "backend: ruff format --check" bash -c "cd \"$BACKEND\" && \"$PY\" -m ruff format --check ."

# ───────────── backend tests ─────────────
# Smoke and critical scenarios run first. The full suite only runs once they pass.
run "backend: pytest smoke and critical" \
  bash -c "cd \"$BACKEND\" && \"$PY\" -m pytest -m \"smoke or critical\" -q -p no:cacheprovider"
run "backend: pytest full regression" \
  bash -c "cd \"$BACKEND\" && \"$PY\" -m pytest -q -p no:cacheprovider"

# ───────────── frontend checks ─────────────
run "frontend: typecheck" $RUN typecheck
run "frontend: eslint" $RUN lint
run "frontend: prettier check" $RUN format:check
run "frontend: vitest" $RUN test

echo
echo "verify: all checks passed."
exit 0
