#!/usr/bin/env bash
# Runs automatically when the folder opens in VS Code (see tasks.json).
# Silent when this machine is set up; otherwise prints the one command to run.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
problems=()
[ -x "$ROOT/.venv/bin/python" ] || problems+=("no .venv")
if ! command -v spike >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/spike" ]; then problems+=("no 'spike' command"); fi
[ ${#problems[@]} -eq 0 ] && exit 0
{
  echo
  echo "FLL is not set up on this machine yet ($(IFS=', '; echo "${problems[*]}")). Run this once, then reopen VS Code:"
  echo
  echo "    bash \"$ROOT/setup.sh\""
  echo
} >&2
exit 1
