#!/usr/bin/env bash
# O-16 step 2 — converge on Antigravity's hooks.json schema by letting its validator correct us.
#
# Step 1 established two facts by experiment: `agy` reads
#   ~/.gemini/hooks.json  and  ~/.gemini/antigravity-cli/hooks.json
# and the top level is a MAP of hook name -> jsonhook.JSONHookSpec (hence "named hooks" in its
# log; my earlier Claude-shaped file failed with `cannot unmarshal string into ... JSONHookSpec`).
#
# The field names below were harvested from the binary's struct tags: type, command, prompt,
# model, enabled, timeout, tools, tool, events, event, description, name. Which of them are
# required, and what values they accept, is NOT knowable statically — so this asks the program.
# `setDefaultsAndValidate` will either accept the file (loaded 1 named hook) or say what is wrong.
#
# Safe: writes ONE file to the agy-specific location, backs up anything already there, tidies the
# four dead candidates from step 1, and prints exactly what to remove.
#
# Usage:  bash evidence/agy_probe/try_schema.sh

set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="$HOME/.gemini/antigravity-cli/hooks.json"
LOGDIR="$HOME/.gemini/antigravity-cli/log"
WS="$(mktemp -d)"

echo "=== 1. tidy the dead candidates from step 1 (they were never read) ==="
for f in "$HOME/.antigravity/hooks.json" "$HOME/.agy/hooks.json" "$HOME/.gemini/hooks.json"; do
  if [ -f "$f" ] && grep -q "MS_PROBE_" "$f" 2>/dev/null; then
    rm -f "$f" && echo "  [rm  ] $f"
  fi
done

echo
echo "=== 2. install the candidate schema at the location agy actually reads ==="
if [ -f "$DEST" ] && ! grep -q "MS_PROBE_" "$DEST" 2>/dev/null; then
  cp "$DEST" "$DEST.metaspace.bak" && echo "  [bak ] $DEST.metaspace.bak"
fi
cp "$REPO/evidence/agy_probe/hooks.candidate.json" "$DEST" && echo "  [put ] $DEST"

echo
echo "=== 3. one agy run ==="
cd "$WS" || exit 1
timeout 240 agy -p "Reply with the single word OK. Do not use any tools." 2>&1 | tail -6

echo
echo "=== 4. what the validator said (this is the answer) ==="
grep -h "hooks_manager\|jsonhook\|hooks.json\|named hook" "$LOGDIR"/*.log 2>/dev/null | tail -8

echo
echo "=== 5. cleanup if you want it gone ==="
echo "  rm \"$DEST\""
[ -f "$DEST.metaspace.bak" ] && echo "  # restore original:  mv \"$DEST.metaspace.bak\" \"$DEST\""
echo "  workspace to discard: $WS"
