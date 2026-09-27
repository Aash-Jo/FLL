#!/usr/bin/env bash
# Set up a Mac (or Linux) to program the SPIKE Prime robots from this folder -
# over Bluetooth by default, USB as a fallback. Safe to re-run at any time.
# Windows uses setup.ps1 instead.
#
#     bash setup.sh [--no-verify] [--skip-vscode]
#
# What it does (all user-level, no sudo):
#   1. Finds Python 3.12 (installs it with Homebrew if brew is present).
#   2. Recreates .venv here and installs requirements.txt into it.
#      (A venv is never portable between machines - it is always rebuilt.)
#   3. Finds VS Code (installs it with Homebrew if brew is present) and
#      installs the extensions listed in .vscode/extensions.json.
#   4. Writes the `spike` command to ~/.local/bin/spike and makes sure that
#      folder is on PATH (appends one line to ~/.zshrc or ~/.bashrc if needed).
#      This is the ONLY thing written outside this folder.
#   5. Checks for Bluetooth.
#   6. Unless --no-verify: looks for a hub and runs programs/hello_hub.py on it
#      over Bluetooth. The hub must be on, Bluetooth light blinking, and not
#      connected to the SPIKE app. On macOS the first Bluetooth scan pops a
#      permission dialog for your terminal (or VS Code) - click Allow.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
VPY="$VENV/bin/python"
TOOL="$ROOT/tools/spike_ble.py"
NOVERIFY=0; SKIPCODE=0
for a in "$@"; do
  case "$a" in
    --no-verify)   NOVERIFY=1 ;;
    --skip-vscode) SKIPCODE=1 ;;
  esac
done
FAILS=0
step() {  # step NAME 0|1 DETAIL
  if [ "$2" = 0 ]; then printf '[ OK ] %s - %s\n' "$1" "$3"
  else printf '[FAIL] %s - %s\n' "$1" "$3"; FAILS=$((FAILS+1)); fi
}

echo; echo "== SPIKE Prime robot setup (macOS / Linux) =="; echo "Project folder: $ROOT"; echo

# ------------------------------------------------------------- 1. Python 3.12
find_py() {
  local c
  for c in python3.12 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 \
           /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12; do
    if command -v "$c" >/dev/null 2>&1; then command -v "$c"; return; fi
    if [ -x "$c" ]; then echo "$c"; return; fi
  done
}
PY="$(find_py)"
if [ -z "$PY" ] && command -v brew >/dev/null 2>&1; then
  echo "Python 3.12 not found - installing with Homebrew..."
  brew install python@3.12
  PY="$(find_py)"
fi
if [ -n "$PY" ]; then
  step "Python 3.12" 0 "$PY ($("$PY" --version 2>&1))"
else
  step "Python 3.12" 1 "not found. Install Python 3.12 from python.org or 'brew install python@3.12', then re-run."
  echo; exit 1
fi

# ------------------------------------------------------------- 2. venv
if [ -d "$VENV" ]; then echo "Removing existing .venv (not portable; rebuilding fresh)..."; rm -rf "$VENV"; fi
if ! "$PY" -m venv "$VENV" || [ ! -x "$VPY" ]; then step ".venv" 1 "python -m venv failed"; echo; exit 1; fi
"$VPY" -m pip install --quiet --upgrade pip
if "$VPY" -m pip install --quiet -r "$ROOT/requirements.txt"; then
  step ".venv + packages" 0 "$("$VPY" -m pip list --format=freeze 2>/dev/null | grep -E '^(bleak|mpremote|pyserial|pyright)==' | tr '\n' ' ')"
else
  step ".venv + packages" 1 "pip install -r requirements.txt failed"
fi

# ------------------------------------------------------------- 3. VS Code
if [ "$SKIPCODE" = 0 ]; then
  find_code() {
    if command -v code >/dev/null 2>&1; then command -v code; return; fi
    local app="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
    [ -x "$app" ] && echo "$app"
  }
  CODE="$(find_code)"
  if [ -z "$CODE" ] && command -v brew >/dev/null 2>&1; then
    echo "VS Code not found - installing with Homebrew..."
    brew install --cask visual-studio-code
    CODE="$(find_code)"
  fi
  if [ -n "$CODE" ]; then
    # extensions.json has // comments; let Python strip them and read the list.
    EXTS="$("$VPY" - "$ROOT/.vscode/extensions.json" <<'PYEOF'
import json, re, sys
text = open(sys.argv[1], encoding="utf-8").read()
text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
print(" ".join(json.loads(text)["recommendations"]))
PYEOF
)"
    for e in $EXTS; do "$CODE" --install-extension "$e" --force >/dev/null 2>&1; done
    step "VS Code + extensions" 0 "$CODE ; $EXTS"
  else
    step "VS Code" 1 "not found. Install from code.visualstudio.com, run 'Shell Command: Install code command in PATH' inside it, then re-run (or pass --skip-vscode)."
  fi
fi

# ------------------------------------------------------------- 4. spike command
BIN="$HOME/.local/bin"; mkdir -p "$BIN"
cat > "$BIN/spike" <<EOF
#!/usr/bin/env bash
exec "$VPY" "$TOOL" "\$@"
EOF
chmod +x "$BIN/spike"
NOTE="$BIN/spike"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    if [ "$(uname)" = "Darwin" ]; then RC="$HOME/.zshrc"; else RC="$HOME/.bashrc"; fi
    if ! grep -qs '\.local/bin' "$RC"; then
      printf '\n# FLL robots: the spike command lives here\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$RC"
      NOTE="$NOTE  (added ~/.local/bin to PATH in $RC - open a new terminal)"
    else
      NOTE="$NOTE  (~/.local/bin is not on PATH in this shell - open a new terminal)"
    fi ;;
esac
step "spike command" 0 "$NOTE"

# ------------------------------------------------------------- 5. Bluetooth
if [ "$(uname)" = "Darwin" ]; then
  if system_profiler SPBluetoothDataType 2>/dev/null | grep -qi 'bluetooth'; then
    step "Bluetooth" 0 "present. First scan will ask to allow Bluetooth for your terminal / VS Code - click Allow (System Settings > Privacy & Security > Bluetooth)."
  else
    step "Bluetooth" 1 "no Bluetooth controller reported - Bluetooth path will not work; USB still will"
  fi
else
  step "Bluetooth" 0 "not checked on Linux (bleak uses BlueZ; make sure bluetooth.service is running)"
fi

# ------------------------------------------------------------- 6. verify
if "$VPY" "$TOOL" --help >/dev/null 2>&1; then step "tool runs" 0 "tools/spike_ble.py --help"
else step "tool runs" 1 "tools/spike_ble.py --help failed"; fi

if [ "$NOVERIFY" = 0 ]; then
  echo; echo "Looking for hubs (Bluetooth, then USB)..."
  "$VPY" "$TOOL" discover --seconds 6
  echo; echo "Running programs/hello_hub.py over Bluetooth on whichever hub is advertising..."
  if "$VPY" "$TOOL" -v run "$ROOT/programs/hello_hub.py" --timeout 20; then
    step "hello_hub over Bluetooth" 0 "program ran on the hub and its print() came back"
  else
    step "hello_hub over Bluetooth" 1 "no hub reachable, or run failed. Hub on? Light blinking? SPIKE app closed? Then: spike run programs/hello_hub.py"
  fi
fi

# ------------------------------------------------------------- summary
echo
if [ "$FAILS" = 0 ]; then
  echo "All steps passed."
  echo "Next:  code \"$ROOT\"   then open a program and press Cmd+Shift+B (Ctrl+Shift+B on Linux)"
  echo "  or:  spike session      (in a new terminal, from this folder)"
  exit 0
else
  echo "$FAILS step(s) need attention - see above."
  exit 1
fi
