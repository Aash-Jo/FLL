#!/usr/bin/env bash
# FLL patch v1 - apply the status-bar buttons to an FLL folder that has the old setup.
# macOS (also fine on Linux). Double-click me, or:  bash apply.command
#
#   1. Copies files/** into the FLL folder (the folder this patch_v1 sits in),
#      backing up anything it replaces into backup-<date>/ here.
#   2. Installs the VS Code extension that draws the buttons.
#   3. Checks the folder's .venv still runs the tool.
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(dirname "$HERE")"
EXT="spencerwmiles.vscode-task-buttons"
UNWANTED="peterstaev.lego-spikeprime-mindstorms-vscode"

done_() { echo; read -r -p "Press Enter to close" _; exit "$1"; }
is_fll() { [ -n "$1" ] && [ -f "$1/hubs.json" ] && [ -f "$1/tools/spike_ble.py" ]; }

echo "FLL patch v1 - status-bar buttons"
echo "=================================="
if ! is_fll "$TARGET"; then
  echo "This patch_v1 folder is not inside an FLL folder (no hubs.json / tools/spike_ble.py next to it)."
  read -r -p "Type or drag in the FLL folder on this Mac: " TARGET
  TARGET="${TARGET%/}"; TARGET="${TARGET//\\ / }"
  if ! is_fll "$TARGET"; then echo "That is not the FLL folder either. Nothing was changed."; done_ 1; fi
fi
echo "FLL folder: $TARGET"

# ---- 1. copy files -----------------------------------------------------------
FILES="$HERE/files"
BACKUP="$HERE/backup-$(date +%Y%m%d-%H%M%S)"
echo
echo "Files:"
while IFS= read -r -d '' src; do
  rel="${src#"$FILES"/}"
  dest="$TARGET/$rel"
  if [ -e "$dest" ]; then
    mkdir -p "$(dirname "$BACKUP/$rel")"
    cp -p "$dest" "$BACKUP/$rel"
    what="replaced"
  else
    what="added   "
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "  $what  $rel"
done < <(find "$FILES" -type f -print0)
[ -d "$BACKUP" ] && echo "  (old versions saved in $BACKUP)"

# ---- 2. VS Code extension ----------------------------------------------------
echo
CODE=""
if command -v code >/dev/null 2>&1; then CODE="$(command -v code)"
elif [ -x "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ]; then
  CODE="/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
fi
EXT_OK=1
if [ -n "$CODE" ]; then
  "$CODE" --install-extension "$EXT" --force >/dev/null 2>&1
  LIST="$("$CODE" --list-extensions 2>/dev/null)"
  if printf '%s\n' "$LIST" | grep -qx "$EXT"; then
    EXT_OK=0; echo "Extension: $EXT installed."
  else
    echo "Extension: could not confirm $EXT. In VS Code, Extensions (Cmd+Shift+X), search 'Task Buttons', Install."
  fi
  if printf '%s\n' "$LIST" | grep -qx "$UNWANTED"; then
    echo "Note: the LEGO SPIKE Prime extension ($UNWANTED) is installed. It cannot talk to these hubs;"
    echo "      its 'LEGO Hub: Disconnected' status item is unrelated to the buttons. Uninstalling it is optional."
  fi
else
  echo "Extension: VS Code's 'code' command was not found. In VS Code, Extensions (Cmd+Shift+X), search 'Task Buttons', Install."
fi

# ---- 3. venv check -----------------------------------------------------------
echo
VPY="$TARGET/.venv/bin/python"
VENV_OK=1
if [ -x "$VPY" ]; then
  OUT="$(cd "$TARGET" && "$VPY" tools/spike_ble.py send ping 2>&1)"
  # "no session open" normally; "[session] connected" if a session happens to be open.
  case "$OUT" in *"no session open"*|*"[session] connected"*) VENV_OK=0 ;; esac
fi
if [ "$VENV_OK" = 0 ]; then
  echo "Python: .venv runs the new tool. No rebuild needed."
else
  echo "Python: .venv did not run the tool. Rebuild it once (safe, takes a minute):"
  echo "    bash \"$TARGET/setup.sh\" --no-verify"
fi

# ---- summary -----------------------------------------------------------------
echo
echo "Next: open FLL.code-workspace in VS Code. Buttons (Connect / Run / Stop / Disconnect / Robots)"
echo "are at the bottom-left. If they are missing, Cmd+Shift+P -> 'Reload Window'."
if [ "$EXT_OK" = 0 ] && [ "$VENV_OK" = 0 ]; then done_ 0; else done_ 1; fi
