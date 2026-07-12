#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-INSTALL + P-IDEMPOTENT — the user-level installer wires the Warden correctly, is idempotent
and non-clobbering, and the INSTALLED config actually blocks the Friendly-Fire attack.

No mock: it runs the real `metaspace install` (cli.py) into a temp HOME, inspects the real
`settings.json` it wrote, then drives the REAL PreToolUse hook using exactly that installed
constitution. Falsifiable: if the installer mis-wires, clobbers, duplicates, pins a project
root on a user install, or the installed constitution fails to block, this proof FAILS.

Run: python run_install_proof.py   (exit 0 iff every check passes; cross-OS)
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

_ok = True


def check(cond, label):
    global _ok
    _ok = _ok and bool(cond)
    print("  [%s] %s" % ("ok" if cond else "FAIL", label))


def run_install(home, extra=None):
    env = dict(os.environ)
    env["HOME"] = home              # POSIX expanduser("~")
    env["USERPROFILE"] = home       # Windows expanduser("~")
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run([sys.executable, CLI, "install"] + (extra or []),
                          capture_output=True, text=True, env=env)


def settings_of(home):
    p = os.path.join(home, ".claude", "settings.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def metaspace_hooks(settings):
    pre = (settings.get("hooks", {}) or {}).get("PreToolUse", [])
    return [h for h in pre if "session_guard_hook.py" in json.dumps(h)]


def drive_hook(settings, command):
    """Drive the REAL hook with the INSTALLED constitution; return 0 (ALLOW) or 2 (BLOCK)."""
    proj = tempfile.mkdtemp(prefix="ff_proj_")
    env = dict(os.environ)
    env["METASPACE_SESSION_BIO"] = settings["env"]["METASPACE_SESSION_BIO"]
    env["METASPACE_PROJECT_ROOT"] = proj.replace("\\", "/")
    env["METASPACE_SESSION_AUDIT"] = os.path.join(proj, "audit.jsonl")
    ev = {"tool_name": "Bash", "tool_input": {"command": command}}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(ev),
                       capture_output=True, text=True, env=env)
    shutil.rmtree(proj, ignore_errors=True)
    return p.returncode


def main():
    home = tempfile.mkdtemp(prefix="ms_home_")
    print("=" * 72)
    print("  P-INSTALL + P-IDEMPOTENT (real installer -> temp HOME -> real hook)")
    print("=" * 72)

    # Pre-seed an UNRELATED settings.json to prove the install is non-clobbering.
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    seed = {"env": {"FOO": "bar"},
            "hooks": {"PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo other", "timeout": 5}]}]}}
    with open(os.path.join(home, ".claude", "settings.json"), "w", encoding="utf-8") as fh:
        json.dump(seed, fh)

    # 1) install
    r = run_install(home)
    check(r.returncode == 0, "installer exits 0 (%s)" % (r.stderr.strip()[:60] or "ok"))
    s = settings_of(home) or {}

    # 2) wiring is correct, and nothing pre-existing was clobbered
    check(len(metaspace_hooks(s)) == 1, "exactly one MetaSpace hook installed")
    check(s.get("env", {}).get("FOO") == "bar", "unrelated env key preserved")
    check(any("echo other" in json.dumps(h) for h in s["hooks"]["PreToolUse"]),
          "unrelated pre-existing hook preserved")
    check("METASPACE_SESSION_BIO" in s.get("env", {}), "constitution path recorded in env")
    check("METASPACE_PROJECT_ROOT" not in s.get("env", {}),
          "user install does NOT pin a project root (resolved per-session)")
    bio = s["env"].get("METASPACE_SESSION_BIO", "")
    check(os.path.exists(bio) and bio.startswith(home.replace("\\", "/")),
          "installed constitution exists under the user's ~/.claude")

    # 3) idempotent: a second install must not duplicate or corrupt
    run_install(home)
    s2 = settings_of(home) or {}
    check(len(metaspace_hooks(s2)) == 1, "still exactly one MetaSpace hook after a 2nd install")
    check(s2.get("env", {}).get("FOO") == "bar", "unrelated env still intact after 2nd install")

    # 4) the INSTALLED config actually blocks the attack and allows legit work (no mock)
    for cmd in ["./security.sh", "bash ./security.sh", 'sh -c "./security.sh"',
                "./code_policies", "cat security.sh | bash"]:
        check(drive_hook(s2, cmd) == 2, "installed hook BLOCKS: %s" % cmd)
    check(drive_hook(s2, "python build.py") == 0, "installed hook ALLOWS: python build.py")

    shutil.rmtree(home, ignore_errors=True)
    print("-" * 72)
    print("  RESULT:", "PASS — user-level install is correct, idempotent, and enforces the membrane"
          if _ok else "FAIL — see checks above")
    print("=" * 72)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
