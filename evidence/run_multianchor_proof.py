#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-ANCHORS — self-protection covers every host's anchor, not just Claude's (O-14).

C-33 ("a deceived agent cannot disable the membrane") holds because the config that switches the
membrane on is inside a `FILESYSTEM deny` scope. That deny used to name exactly one location,
`{{CLAUDE_HOME}}`. It covered Claude Code and — by luck, not design — Cursor, which reads the
same `~/.claude/settings.json`. **Gemini CLI has its own anchor**, `~/.gemini/settings.json`.
Supporting a host whose anchor is undefended would hand a deceived agent a fresh way to turn the
membrane off on that host: the exact attack C-33 exists to prevent. Every new host would
otherwise be another unlocked back door.

THE POINT OF THIS PROOF is the constitution it uses: one that **only** denies `{{CLAUDE_HOME}}`,
exactly like every constitution written before other hosts were known, and like one a user might
hand-edit. If the other anchors are still protected under that constitution, then
self-protection is a structural property of the membrane rather than a line of policy text that
can be deleted or simply predate a host.

FALSIFIABLE: remove the `deny_scopes()` injection from the hook and legs 2–4 fail — the membrane
would let an agent rewrite `~/.cursor/hooks.json` or `~/.gemini/settings.json` and uninstall
itself there, while still looking correct on Claude Code.

Run: python evidence/run_multianchor_proof.py     (exit 0 = PASS)
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOOK = os.path.join(REPO, "products", "ai_membrane", "session_guard_hook.py")
sys.path.insert(0, REPO)

failures = []


def check(cond, msg):
    print(("    [ok]   " if cond else "    [FAIL] ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def main():
    print("=" * 72)
    print("  P-ANCHORS — every host's config anchor is defended (O-14)")
    print("=" * 72)

    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    project = home                      # WORST CASE: the project is opened AT the home dir,
                                        # so every anchor sits inside the granted write scope.

    # A deliberately OLD-STYLE constitution: it grants the whole project and denies only the
    # Claude anchor — what every pre-existing or hand-edited constitution looks like.
    bio = os.path.join(home, "legacy.constitution.bio")
    with open(bio, "w", encoding="utf-8") as fh:
        fh.write("CELL Legacy {\n  CAPABILITIES {\n"
                 f'    FILESYSTEM write "{home}/**";\n'
                 # reads are granted broadly on purpose: leg 4 checks that the anchor deny is
                 # write-only. Without this the Read would be refused by deny-by-default and the
                 # check would pass for the wrong reason.
                 f'    FILESYSTEM read  "{home}/**";\n'
                 '    FILESYSTEM deny  "{{CLAUDE_HOME}}/**";\n'
                 "  }\n}\n")

    def hook(tool, path):
        env = dict(os.environ)
        for k in ("METASPACE_MODE", "METASPACE_SESSION_BIO", "CLAUDE_PROJECT_DIR"):
            env.pop(k, None)
        env["HOME"] = home
        env["USERPROFILE"] = home
        env["METASPACE_MODE"] = "enforce"
        env["METASPACE_SESSION_BIO"] = bio
        env["METASPACE_PROJECT_ROOT"] = project
        env["METASPACE_SESSION_AUDIT"] = os.path.join(home, "audit.jsonl")
        ev = {"tool_name": tool, "tool_input": {"file_path": path}}
        p = subprocess.run([sys.executable, HOOK], input=json.dumps(ev),
                           capture_output=True, text=True, env=env)
        return p.returncode

    from core.agent_anchors import USER_ANCHORS

    # --------------------------------------------------------- 1. the old guarantee still holds
    print("\n  1. the original anchor is still protected (no regression)")
    claude_settings = f"{home}/.claude/settings.json"
    check(hook("Write", claude_settings) == 2, "write ~/.claude/settings.json -> BLOCK")
    check(hook("Edit", claude_settings) == 2, "edit  ~/.claude/settings.json -> BLOCK")

    # ------------------------------------ 2. the anchors this constitution never heard of
    print("\n  2. anchors the constitution does NOT mention are protected anyway")
    for anchor, f in (("cursor", "hooks.json"), ("cursor", "mcp.json"),
                      ("gemini", "settings.json")):
        target = f"{home}/.{anchor}/{f}"
        check(hook("Write", target) == 2, f"write ~/.{anchor}/{f} -> BLOCK")

    # ------------------------------------------------ 3. every listed anchor, uniformly
    print("\n  3. every anchor in the list is denied, with no gaps")
    missed = [a for a in USER_ANCHORS if hook("Write", f"{home}/{a}/x.json") != 2]
    check(not missed, f"all {len(USER_ANCHORS)} user anchors block a write ({missed or 'none missed'})")
    nested = f"{home}/.gemini/deep/nested/evil.json"
    check(hook("Write", nested) == 2, "a nested path under an anchor is blocked too")

    # ---------------------------------------------------------- 4. no over-blocking
    print("\n  4. ordinary work in the project is unaffected")
    check(hook("Write", f"{home}/src/app.py") == 0, "normal in-project write -> ALLOW")
    check(hook("Write", f"{home}/.claudette/notes.md") == 0,
          "a directory that merely LOOKS like an anchor is not blocked (prefix, not substring)")
    check(hook("Read", claude_settings) == 0,
          "READING an agent config is still allowed — the attack is writing, not reading")

    shutil.rmtree(home, ignore_errors=True)

    print("\n" + "-" * 72)
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} check(s) failed")
        for f in failures:
            print("    -", f)
        return 1
    print("  RESULT: PASS — self-protection is structural, not a line of policy text")
    print("-" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
