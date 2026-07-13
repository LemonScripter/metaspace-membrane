#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-DRYRUN — a fresh install starts in dry-run/observe mode (warn about what WOULD be blocked,
but let it through so the first session is never over-blocked); `metaspace enforce` turns on
blocking.

No mock: the real installer writes the mode into settings.json, and the REAL hook is driven
with exactly that setting. Falsifiable — if install did not default to dry-run, or dry-run
blocked, or enforce did not block, this proof fails. Cross-OS.

Run: python run_dryrun_mode_proof.py   (exit 0 iff every check passes)
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


def cli(args, home):
    env = dict(os.environ)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run([sys.executable, CLI] + args, capture_output=True, text=True, env=env)


def settings_of(home):
    return json.load(open(os.path.join(home, ".claude", "settings.json"), encoding="utf-8"))


def drive(home, settings, command):
    """Drive the REAL hook with the settings the installer wrote (incl. METASPACE_MODE)."""
    proj = tempfile.mkdtemp(prefix="ff_proj_")
    audit = os.path.join(proj, "audit.jsonl")
    env = dict(os.environ)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env.update(settings.get("env", {}))            # SESSION_BIO + MODE (as Claude Code injects settings.env)
    env["METASPACE_PROJECT_ROOT"] = proj.replace("\\", "/")
    env["METASPACE_SESSION_AUDIT"] = audit
    ev = {"tool_name": "Bash", "tool_input": {"command": command}}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(ev),
                       capture_output=True, text=True, env=env)
    recs = []
    if os.path.exists(audit):
        recs = [json.loads(l) for l in open(audit, encoding="utf-8") if l.strip()]
    shutil.rmtree(proj, ignore_errors=True)
    return p.returncode, recs, (p.stderr or "")


def main():
    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    print("=" * 72)
    print("  P-DRYRUN (real install -> dry-run observes; `metaspace enforce` -> blocks)")
    print("=" * 72)

    # 1) fresh install must default to dry-run
    r = cli(["install"], home)
    check(r.returncode == 0, "installer exits 0")
    s = settings_of(home)
    check(s["env"].get("METASPACE_MODE") == "dryrun", "fresh install defaults to dry-run")

    # 2) in dry-run an attack vector is ALLOWED but recorded + warned as WOULD-block
    rc, recs, err = drive(home, s, "./security.sh")
    check(rc == 0, "dry-run: ./security.sh is ALLOWED (observe, not blocked)")
    check(any(rec.get("would_block") for rec in recs), "dry-run: audit records a WOULD-block")
    check("DRY-RUN" in err, "dry-run: warns loudly on stderr")

    # 3) a legit command is allowed with no would-block noise
    rc_ok, recs_ok, _ = drive(home, s, "python build.py")
    check(rc_ok == 0 and not any(rec.get("would_block") for rec in recs_ok),
          "dry-run: legit command allowed with no would-block")

    # 4) `metaspace enforce` turns on blocking
    e = cli(["enforce"], home)
    check(e.returncode == 0, "`metaspace enforce` exits 0")
    s2 = settings_of(home)
    check(s2["env"].get("METASPACE_MODE") == "enforce", "mode flipped to enforce")
    rc2, _, _ = drive(home, s2, "./security.sh")
    check(rc2 == 2, "enforce: ./security.sh is BLOCKED")

    # 5) install --enforce skips dry-run
    home2 = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    cli(["install", "--enforce"], home2)
    s3 = settings_of(home2)
    check(s3["env"].get("METASPACE_MODE") == "enforce", "install --enforce starts blocking")
    shutil.rmtree(home2, ignore_errors=True)

    shutil.rmtree(home, ignore_errors=True)
    print("-" * 72)
    print("  RESULT:", "PASS — dry-run observes then `enforce` blocks; no over-blocking on first run"
          if _ok else "FAIL — see checks above")
    print("=" * 72)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
