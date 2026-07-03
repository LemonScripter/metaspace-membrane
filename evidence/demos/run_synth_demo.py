#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — code -> constitution -> enforcement (closed loop)

Demonstrates the full "an app that writes its own constitution and then may only do what
is in it" vision on real code:

  1) SYNTHESIZE : statically analyze sample_app.py and emit a .bio constitution.
  2) LOAD       : feed that synthesized constitution straight into the runtime membrane.
  3) ENFORCE    : the membrane allows exactly the effects the app declared, and denies
                  everything else (deny-by-default) — including an effect the app never had.

No human edited the constitution between steps 1 and 2: the code's own effects became the
policy that now bounds it.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO_ROOT)
from core.capability_analyzer import analyze_path, synthesize_bio  # noqa: E402
from core.guard import Guard, ConstitutionViolation                # noqa: E402

APP = os.path.join(HERE, "synth_demo", "sample_app.py")


def decide(guard, kind, mode, target):
    try:
        guard.check(kind, mode, target)
        return "ALLOW"
    except ConstitutionViolation:
        return "DENY"


def main():
    audit = os.path.join(HERE, "synth_audit.jsonl")
    if os.path.exists(audit):
        os.remove(audit)

    # 1) code -> constitution
    findings = analyze_path(APP)
    bio = synthesize_bio("sample_app", findings)

    print("=" * 74)
    print("  CODE -> CONSTITUTION -> ENFORCEMENT  (closed loop, no human in between)")
    print("=" * 74)
    print("  Analyzed:", os.path.relpath(APP, REPO_ROOT))
    print("-" * 74)
    print("  SYNTHESIZED constitution:")
    for line in bio.splitlines():
        print("    " + line)
    print("-" * 74)

    # 2) load the synthesized constitution straight into the membrane
    base = os.path.dirname(APP)
    guard = Guard(bio, base_dir=base, audit_path=audit, provenance="SYNTHESIZED")

    # 3) the membrane enforces exactly what was synthesized
    cases = [
        ("FILESYSTEM", "read",  "config.json",   "ALLOW", "declared read"),
        ("FILESYSTEM", "write", "logs/app.log",  "ALLOW", "declared write"),
        ("FILESYSTEM", "write", "config.json",   "DENY",  "write outside the write scope (config is read-only)"),
        ("SUBPROCESS", "exec",  "rm -rf /",      "DENY",  "UNDECLARED capability -> deny-by-default (the app never did this)"),
        ("NETWORK",    "out",   "api.example.com", "ALLOW", "declared network host (auto-derived from the URL)"),
        ("NETWORK",    "out",   "evil.example.com", "DENY", "host not in the synthesized allowlist"),
    ]

    print("  Enforcement against the synthesized constitution:")
    ok = True
    for kind, mode, target, expected, why in cases:
        got = decide(guard, kind, mode, target)
        match = (got == expected)
        ok = ok and match
        flag = "OK " if match else "!! "
        print(f"    [{flag}{got:<5}] {kind}/{mode:<5} {target:<16} <{why}>")
    print("=" * 74)
    if ok:
        print("  RESULT: PASS - the code's own effects became the policy that bounds it;")
        print("          undeclared effects are denied by default.")
        print("  Note: the constitution is SYNTHESIZED (not ratified) - a human reviews and")
        print("        ratifies it before it is trusted; the runtime membrane is the guarantee.")
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
