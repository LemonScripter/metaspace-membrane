#!/usr/bin/env bash
# O-16 step 4 — which event name makes an Antigravity hook actually FIRE?
#
# Step 3 left the gap: the spec validates ("loaded 1 named hooks") but never executes, and a write
# outside scope went through unmediated. Validation accepted the file; acceptance is not semantics.
#
# Candidates come from the binary's own type names — jsonhook.preToolPromptResponse,
# postToolPromptResponse, stopPromptResponse — suggesting the native value is `preTool` rather than
# `PreToolUse`, which most likely belongs to its `agy plugin import claude` path.
#
# The schema is a MAP of named hooks, so every candidate is defined at once, each writing a
# DISTINCT marker. One agy run tests all of them and the marker that appears names the event. A
# singular `event` variant and a no-event variant are included because the field name itself is
# only inferred from a struct tag.
#
# PATH DISCIPLINE: this runs under MSYS bash but agy and the hook commands are Windows programs,
# and the two disagree about what /tmp means — bash maps it inside AppData, Windows Python reads
# it as C:\tmp. That mismatch already produced one false "the write did not happen" in step 3, so
# every path handed to a Windows process here goes through cygpath -w.
set -u
DEST="$HOME/.gemini/antigravity-cli/hooks.json"
LOGDIR="$HOME/.gemini/antigravity-cli/log"
MARK="$(mktemp -d)"; WS="$(mktemp -d)"; CFG="$(mktemp -d)/agy_events.json"
MARK_WIN="$(cygpath -w "$MARK" | sed 's|\\|/|g')"

echo "markers   -> $MARK   (windows: $MARK_WIN)"
echo "workspace -> $WS"

python - "$MARK_WIN" "$CFG" <<'PY'
import json, sys
mark, out = sys.argv[1], sys.argv[2]
def cmd(tag):
    return 'python -c "import pathlib;pathlib.Path(r\'%s/%s.txt\').write_text(\'fired\')"' % (mark, tag)
spec = {}
for ev in ("preTool", "PreTool", "beforeTool", "BeforeTool", "PreToolUse", "pre_tool"):
    spec["probe_" + ev] = {"enabled": True, "type": "command", "command": cmd("ev_" + ev),
                           "timeout": 30, "events": [ev]}
# the field NAME is itself only inferred from a struct tag, so test singular and absent too
spec["probe_singular"] = {"enabled": True, "type": "command", "command": cmd("ev_singular"),
                          "timeout": 30, "event": "preTool"}
spec["probe_noevent"] = {"enabled": True, "type": "command", "command": cmd("ev_noevent"),
                         "timeout": 30}
open(out, "w", encoding="utf-8").write(json.dumps(spec, indent=2))
print("generated %d named hooks -> %s" % (len(spec), out))
PY

[ -f "$CFG" ] || { echo "config generation failed"; exit 1; }
[ -f "$DEST" ] && cp "$DEST" "$DEST.metaspace.bak" 2>/dev/null
cp "$CFG" "$DEST" && echo "installed: $DEST"

echo
echo "=== agy run: make it USE a tool, so a pre-tool hook has something to intercept ==="
cd "$WS" || exit 1
timeout 300 agy -p "Create a file called note.txt in the current directory containing the word hello. Use your file writing tool." 2>&1 | tail -8

echo
echo "=== which event fired? ==="
found=0
for f in "$MARK"/ev_*.txt; do
  [ -e "$f" ] || continue
  echo "  FIRED -> $(basename "$f" .txt | sed 's/^ev_//')"
  found=1
done
[ $found -eq 0 ] && echo "  (none fired)"

echo
echo "=== agy hooks log ==="
grep -h "hooks_manager\|jsonhook\|named hook" "$LOGDIR"/*.log 2>/dev/null | tail -5

echo
echo "=== did the tool actually run? ==="
[ -f "$WS/note.txt" ] && echo "  note.txt created — the tool ran, so a pre-tool hook had its chance" \
                      || echo "  note.txt missing — the tool may not have run at all"

echo
echo "cleanup:  rm \"$DEST\""
