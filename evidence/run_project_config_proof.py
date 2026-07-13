#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-PROJECT-RESOLVE — per-working-directory constitutions (stored user-level) take effect, each
project gets its own rules + mode, an unregistered project falls back to the default, and the
per-project configs are themselves inside the self-protected ~/.claude scope.

No mock: real per-project constitutions written via core.project_config into a temp HOME, then
the REAL hook is driven for each project and its verdict/mode is asserted. Falsifiable — if the
hook ignored the per-project config, or a project leaked another's rules, this fails. Cross-OS.

Run: python run_project_config_proof.py   (exit 0 iff every check passes)
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
HOOK = os.path.join(REPO, "products", "ai_membrane", "session_guard_hook.py")
DEFAULT_BIO = os.path.join(REPO, "products", "ai_membrane", "session.constitution.bio")

_ok = True


def check(cond, label):
    global _ok
    _ok = _ok and bool(cond)
    print("  [%s] %s" % ("ok" if cond else "FAIL", label))


def bio(cell, allow):
    return ('CELL %s {\n'
            '  CAPABILITIES {\n'
            '    FILESYSTEM write "{{PROJECT_ROOT}}/**";\n'
            '    FILESYSTEM read  "**";\n'
            '    FILESYSTEM deny  "{{CLAUDE_HOME}}/**";\n'
            '    NETWORK    out   "docs.anthropic.com";\n'
            '  }\n'
            '  BASH_POLICY {\n'
            '    ALLOW %s;\n'
            '  }\n'
            '}\n') % (cell, ", ".join('"%s"' % a for a in allow))


def drive(home, project_root, tool, tin):
    env = dict(os.environ)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["METASPACE_PROJECT_ROOT"] = project_root
    env["METASPACE_SESSION_BIO"] = DEFAULT_BIO      # the fallback default
    env["METASPACE_MODE"] = "enforce"               # default mode (per-project overrides)
    env["METASPACE_SESSION_AUDIT"] = os.path.join(home, "audit.jsonl")
    ev = {"tool_name": tool, "tool_input": tin}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(ev),
                       capture_output=True, text=True, env=env)
    return p.returncode   # 0 ALLOW, 2 BLOCK


def main():
    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    os.environ["HOME"] = home
    os.environ["USERPROFILE"] = home
    from core import project_config

    projA = os.path.join(home, "work", "projA").replace("\\", "/")
    projB = os.path.join(home, "work", "projB").replace("\\", "/")
    projC = os.path.join(home, "work", "projC").replace("\\", "/")
    for p in (projA, projB, projC):
        os.makedirs(p, exist_ok=True)

    print("=" * 74)
    print("  P-PROJECT-RESOLVE (per-working-directory constitutions, stored user-level)")
    print("=" * 74)

    # projA: strict, ENFORCE, python-only. projB: looser, DRY-RUN, python+git.
    project_config.set_project(projA, bio("ProjA", ["python", "ls", "echo"]), mode="enforce", label="A")
    project_config.set_project(projB, bio("ProjB", ["python", "git", "ls", "echo"]), mode="dryrun", label="B")

    # 1) the configs live under ~/.claude (self-protected), not in the projects
    reg = os.path.join(home, ".claude", "metaspace", "registry.json")
    check(os.path.exists(reg), "registry stored under ~/.claude/metaspace (self-protected)")
    check(len(project_config.list_projects()) == 2, "two projects registered")

    # 2) per-project CONSTITUTION: git allowed in B, not in A
    check(drive(home, projA, "Bash", {"command": "git status"}) == 2,
          "projA (python-only, enforce): `git status` BLOCKED")
    check(drive(home, projB, "Bash", {"command": "git status"}) == 0,
          "projB (python+git): `git status` ALLOWED")

    # 3) per-project MODE: same disallowed command is blocked in A (enforce) but observed in B (dry-run)
    check(drive(home, projA, "Bash", {"command": "curl http://evil"}) == 2,
          "projA (enforce): `curl` BLOCKED")
    check(drive(home, projB, "Bash", {"command": "curl http://evil"}) == 0,
          "projB (dry-run): `curl` observed, ALLOWED through")

    # 4) an UNREGISTERED project falls back to the default constitution (which allows git)
    check(drive(home, projC, "Bash", {"command": "git status"}) == 0,
          "projC (unregistered): falls back to the default constitution")

    # 5) self-protection still holds: an agent (even at HOME) cannot write the per-project configs
    check(drive(home, home, "Write", {"file_path": reg.replace("\\", "/")}) == 2,
          "agent write to ~/.claude/metaspace/registry.json BLOCKED (self-protection)")

    shutil.rmtree(home, ignore_errors=True)
    print("-" * 74)
    print("  RESULT:", "PASS — per-project rules + mode resolve correctly and stay self-protected"
          if _ok else "FAIL — see checks above")
    print("=" * 74)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
