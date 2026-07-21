#!/usr/bin/env bash
# O-16 discovery — where does Antigravity CLI (`agy`) look for hooks.json?
#
# It cannot be read out of the binary: `agy` is a 156 MB Go executable whose string table is
# fully concatenated, so unlike Cursor's JS and Gemini's unminified bundle the path is not
# recoverable statically. Guessing it would mean writing a file nothing reads — an install that
# looks like success and protects nothing. So we ask the program itself.
#
# `agy` logs `hooks_manager.go: loaded N named hooks from M hooks.json file(s)`. A marker placed
# in the right directory moves M from 0 upward, and each marker carries a distinct id so the one
# that was read identifies itself.
#
# SAFE BY CONSTRUCTION:
#   * only ever CREATES hooks.json where none exists; an existing file is left alone and reported
#   * every file it creates is listed at the end so cleanup is one copy-paste
#   * the hook it installs writes a marker into TEMP and nothing else
#
# Usage:  bash evidence/agy_probe/discover.sh

set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$REPO/evidence/agy_probe"
WS="$(mktemp -d)"
CREATED=()

place() {  # place <marker-name> <destination>
  local name="$1" dest="$2"
  if [ -e "$dest" ]; then
    echo "  [skip] $dest already exists — left untouched"
    return
  fi
  mkdir -p "$(dirname "$dest")" 2>/dev/null
  if cp "$SRC/hooks.$name.json" "$dest" 2>/dev/null; then
    echo "  [put ] $dest"
    CREATED+=("$dest")
  else
    echo "  [fail] could not write $dest"
  fi
}

echo "=== 1. placing distinct markers in every candidate location ==="
place home_antigravity "$HOME/.antigravity/hooks.json"
place home_agy         "$HOME/.agy/hooks.json"
place gemini_agycli    "$HOME/.gemini/antigravity-cli/hooks.json"
place gemini_root      "$HOME/.gemini/hooks.json"
place project_agy      "$WS/.agy/hooks.json"
place project_root     "$WS/hooks.json"

echo
echo "=== 2. log line count before the run ==="
LOGDIR="$HOME/.gemini/antigravity-cli/log"
BEFORE=$(ls -1 "$LOGDIR" 2>/dev/null | wc -l)
echo "  existing log files: $BEFORE"

echo
echo "=== 3. one agy run in the throwaway workspace ==="
echo "  workspace: $WS"
cd "$WS" || exit 1
timeout 240 agy -p "Reply with the single word OK. Do not use any tools." 2>&1 | tail -8

echo
echo "=== 4. what the hooks manager reported ==="
grep -h "hooks_manager\|hooks.json\|unsupported hook type\|MS_PROBE" \
     "$LOGDIR"/*.log "$HOME/.gemini/antigravity-cli/cli.log" 2>/dev/null | tail -15

echo
echo "=== 5. did any marker hook actually fire? ==="
ls -1 "${TMP:-/tmp}"/agy_fired_*.txt 2>/dev/null || ls -1 /c/Users/*/AppData/Local/Temp/agy_fired_*.txt 2>/dev/null || echo "  (none fired — expected if the run used no tools)"

echo
echo "=== 6. CLEANUP — remove exactly what this script created ==="
if [ ${#CREATED[@]} -eq 0 ]; then
  echo "  (nothing was created)"
else
  for f in "${CREATED[@]}"; do echo "  rm \"$f\""; done
  echo
  echo "  workspace to discard: $WS"
fi
