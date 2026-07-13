#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-UNINSTALL — `metaspace off` cleanly removes the membrane, is idempotent and non-clobbering,
and the agent cannot invoke it.

No mock: real install then real `metaspace off` into a temp HOME; the real settings.json is
inspected. Falsifiable — if `off` left the hook behind, deleted unrelated settings, or if the
agent route were open, this proof fails. Cross-OS.

Run: python run_uninstall_proof.py   (exit 0 iff every check passes)
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CLI = os.path.join(REPO, "cli.py")
HOOK = os.path.join(REPO, "products", "ai_membrane", "session_guard_hook.py")
BIO = os.path.join(REPO, "products", "ai_membrane", "session.constitution.bio")

_ok = True


def check(cond, label):
    global _ok
    _ok = _ok and bool(cond)
    print("  [%s] %s" % ("ok" if cond else "FAIL", label))


def cli(args, home):
    env = dict(os.environ)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run([sys.executable, CLI] + args, capture_output=True, text=True, env=env)


def settings_of(home):
    p = os.path.join(home, ".claude", "settings.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def metaspace_hooks(s):
    pre = (s.get("hooks", {}) or {}).get("PreToolUse", [])
    return [h for h in pre if "session_guard_hook.py" in json.dumps(h)]


def agent_can_run_off(home):
    """Drive the REAL hook with the agent trying `metaspace off` as a Bash command."""
    proj = tempfile.mkdtemp(prefix="ff_proj_")
    env = dict(os.environ)
    env["METASPACE_SESSION_BIO"] = BIO
    env["METASPACE_PROJECT_ROOT"] = proj.replace("\\", "/")
    env["METASPACE_MODE"] = "enforce"
    env["METASPACE_SESSION_AUDIT"] = os.path.join(proj, "audit.jsonl")
    ev = {"tool_name": "Bash", "tool_input": {"command": "metaspace off"}}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(ev),
                       capture_output=True, text=True, env=env)
    shutil.rmtree(proj, ignore_errors=True)
    return p.returncode == 0   # True if the hook ALLOWED it (must be False)


def main():
    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    print("=" * 70)
    print("  P-UNINSTALL (real install -> real `metaspace off`, temp HOME)")
    print("=" * 70)

    # seed unrelated settings to prove non-clobbering removal
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    seed = {"env": {"FOO": "bar"},
            "hooks": {"PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo other", "timeout": 5}]}]}}
    with open(os.path.join(home, ".claude", "settings.json"), "w", encoding="utf-8") as fh:
        json.dump(seed, fh)

    # install, confirm present
    cli(["install", "--enforce"], home)
    s = settings_of(home)
    check(len(metaspace_hooks(s)) == 1, "installed: MetaSpace hook present")
    check("METASPACE_SESSION_BIO" in s.get("env", {}), "installed: MetaSpace env present")

    # off, confirm clean removal + everything else intact
    r = cli(["off"], home)
    check(r.returncode == 0, "`metaspace off` exits 0")
    s2 = settings_of(home)
    check(len(metaspace_hooks(s2)) == 0, "after off: no MetaSpace hook remains")
    check(all(k not in s2.get("env", {}) for k in
              ("METASPACE_SESSION_BIO", "METASPACE_MODE", "METASPACE_PROJECT_ROOT")),
          "after off: MetaSpace env keys removed")
    check(s2.get("env", {}).get("FOO") == "bar", "after off: unrelated env key preserved")
    check(any("echo other" in json.dumps(h) for h in s2.get("hooks", {}).get("PreToolUse", [])),
          "after off: unrelated pre-existing hook preserved")

    # idempotent: a second off is a no-op that does not corrupt anything
    r2 = cli(["off"], home)
    check(r2.returncode == 0, "second `metaspace off` exits 0 (no-op)")
    s3 = settings_of(home)
    check(len(metaspace_hooks(s3)) == 0 and s3.get("env", {}).get("FOO") == "bar",
          "second off: still clean, unrelated settings intact")

    # the agent cannot invoke off (metaspace is not on the shell allowlist)
    check(not agent_can_run_off(home), "a deceived agent's `metaspace off` via Bash is BLOCKED")

    shutil.rmtree(home, ignore_errors=True)
    print("-" * 70)
    print("  RESULT:", "PASS — clean, idempotent, non-clobbering uninstall; agent route closed"
          if _ok else "FAIL — see checks above")
    print("=" * 70)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
