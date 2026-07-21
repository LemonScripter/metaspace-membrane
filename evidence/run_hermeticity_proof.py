#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-HERMETIC — the evidence does not depend on the machine that produces it (C-61 / O-17).

Most proofs never set `METASPACE_MODE`; they silently relied on "unset means enforce". That held
until C-54 made the user-level config file authoritative for hosts that do not propagate `env` —
after which a developer whose own `~/.claude/metaspace/config.json` said `dryrun` saw four core
proofs fail. The proofs had been reading the developer's own membrane configuration all along.

That is a worse problem than four red lines. A suite whose verdict depends on the state of the
machine running it cannot support "claim = proof": the same commit would be green on one laptop
and red on another, and neither result would mean anything.

This proof reproduces the pollution and pins the fix, both against a REAL hook run:

  leg 1  a polluted HOME (config.json saying `dryrun`) makes the hook observe instead of block —
         the failure mode is reproduced, so the danger is real and not hypothetical
  leg 2  the same polluted HOME with the suite's baseline applied blocks correctly
  leg 3  `run_proofs.py` actually passes that baseline to its children — the mechanism is
         present, not merely described in a comment

FALSIFIABLE: remove the baseline from `run_proofs.py` and leg 3 fails; if the hook ever stopped
honouring the user-level config, leg 1 would stop reproducing.

Run: python evidence/run_hermeticity_proof.py     (exit 0 = PASS)
"""

import os
import re
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOOK = os.path.join(REPO, "products", "ai_membrane", "session_guard_hook.py")
RUNNER = os.path.join(REPO, "run_proofs.py")

failures = []


def check(cond, msg):
    print(("    [ok]   " if cond else "    [FAIL] ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def main():
    print("=" * 72)
    print("  P-HERMETIC — the evidence does not depend on the machine (C-61)")
    print("=" * 72)

    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    project = tempfile.mkdtemp(prefix="ms_proj_").replace("\\", "/")
    ms_dir = os.path.join(home, ".claude", "metaspace")
    os.makedirs(ms_dir, exist_ok=True)

    bio = os.path.join(ms_dir, "session.constitution.bio")
    with open(bio, "w", encoding="utf-8") as fh:
        fh.write("CELL H {\n  CAPABILITIES {\n"
                 f'    FILESYSTEM write "{project}/**";\n'
                 "  }\n}\n")

    # the pollution: a developer machine configured for observe-mode
    with open(os.path.join(ms_dir, "config.json"), "w", encoding="utf-8") as fh:
        json.dump({"mode": "dryrun", "bio": bio}, fh)

    outside = os.path.join(tempfile.gettempdir(), "ms_hermetic_out.txt").replace("\\", "/")
    event = json.dumps({"tool_name": "Write", "tool_input": {"file_path": outside}})

    def run(extra_env):
        env = dict(os.environ)
        for k in ("METASPACE_MODE", "METASPACE_SESSION_BIO", "CLAUDE_PROJECT_DIR"):
            env.pop(k, None)
        env["HOME"] = home
        env["USERPROFILE"] = home
        env["METASPACE_PROJECT_ROOT"] = project
        env["METASPACE_SESSION_AUDIT"] = os.path.join(project, "audit.jsonl")
        env.update(extra_env or {})
        p = subprocess.run([sys.executable, HOOK], input=event, capture_output=True,
                           text=True, env=env)
        return p.returncode

    try:
        # --------------------------------------------------- 1. the pollution is real
        print("\n  1. an inherited developer config really does change the verdict")
        rc_polluted = run({})
        check(rc_polluted == 0,
              f"with the machine's config (dryrun) the hook OBSERVES, does not block (exit {rc_polluted})")

        # --------------------------------------------------- 2. the baseline neutralises it
        print("\n  2. the suite's baseline makes the same machine irrelevant")
        rc_pinned = run({"METASPACE_MODE": "enforce"})
        check(rc_pinned == 2,
              f"with the pinned baseline the same call is BLOCKED (exit {rc_pinned})")
        check(rc_polluted != rc_pinned,
              "the two differ — which is exactly why the baseline is necessary")

        # --------------------------------------------------- 3. the runner really pins it
        print("\n  3. run_proofs.py passes that baseline to its children")
        src = open(RUNNER, encoding="utf-8").read()
        check(re.search(r"base_env\s*\[\s*[\"']METASPACE_MODE[\"']\s*\]\s*=", src) is not None,
              "the runner sets METASPACE_MODE for children")
        check(re.search(r"base_env\.pop\(\s*[\"']METASPACE_SESSION_BIO[\"']", src) is not None,
              "…and drops an inherited METASPACE_SESSION_BIO")
        # the call spans lines and contains nested parens, so bound the window instead of
        # trying to exclude ')' — an over-clever pattern here would fail on correct code
        check(re.search(r"subprocess\.run\(.{0,300}?env\s*=\s*base_env", src, re.S) is not None,
              "…and actually passes it to subprocess.run (not just computes it)")
    finally:
        shutil.rmtree(home, ignore_errors=True)
        shutil.rmtree(project, ignore_errors=True)

    print("\n" + "-" * 72)
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} check(s) failed")
        for f in failures:
            print("    -", f)
        return 1
    print("  RESULT: PASS — same commit, same verdict, regardless of the machine")
    print("-" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
