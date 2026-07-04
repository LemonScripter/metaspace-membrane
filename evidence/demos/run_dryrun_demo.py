#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — dynamic dry-run ("learning mode") demo

Proves the false-positive problem and its fix, on real code:

  1) STATIC synthesis under-declares a runtime-built path (records only a variable hint).
  2) Enforcing the STATIC-only constitution DENIES the program's real, legitimate write
     -> a false positive that would push a developer toward a dangerous wildcard.
  3) A DRY-RUN runs the program once and observes the CONCRETE effect it actually took.
  4) Merging that observation into the constitution BEFORE ratification makes the same
     real write ALLOWED. No wildcard needed; the human ratifies a constitution that matches reality.
"""

import os
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO_ROOT)
from core.capability_analyzer import analyze_path, synthesize_bio, Findings, Capability  # noqa: E402
from core.guard import Guard, ConstitutionViolation  # noqa: E402
from core.dryrun import dry_run  # noqa: E402

APP_FILE = os.path.join(HERE, "synth_demo", "sample_app_dynamic.py")
SANDBOX = os.path.join(HERE, "dryrun_sandbox")
AUDIT = os.path.join(HERE, "dryrun_audit.jsonl")


def decide(bio, base, kind, mode, target):
    g = Guard(bio, base_dir=base, audit_path=AUDIT, provenance="SYNTHESIZED")
    try:
        g.check(kind, mode, target)
        return "ALLOW"
    except ConstitutionViolation:
        return "DENY"


def caps_of(findings, kind, mode):
    out = []
    for c in findings.capabilities:
        if c.kind == kind and c.mode == mode and c.scope:
            out.append(c.scope)
    return out


def main():
    if os.path.isdir(SANDBOX):
        shutil.rmtree(SANDBOX)
    os.makedirs(os.path.join(SANDBOX, "out"), exist_ok=True)
    if os.path.exists(AUDIT):
        os.remove(AUDIT)

    # 1) static synthesis
    static = analyze_path(APP_FILE)
    static_bio = synthesize_bio("sample_app_dynamic", static)

    # 2) dry-run the real app in the sandbox, observing concrete effects
    sys.path.insert(0, os.path.join(HERE, "synth_demo"))
    import sample_app_dynamic  # noqa: E402
    cwd0 = os.getcwd()
    os.chdir(SANDBOX)
    os.environ["APP_ENV"] = "dev"
    try:
        effects = dry_run(sample_app_dynamic.run)
    finally:
        os.chdir(cwd0)

    # the concrete write the program actually performed
    writes = [t for (k, m, t) in effects if k == "FILESYSTEM" and m == "write"]
    real_target = writes[0] if writes else "(none)"

    # 3) enforce with the STATIC-only constitution -> false positive
    static_decision = decide(static_bio, SANDBOX, "FILESYSTEM", "write", real_target)

    # 4) augment the findings with the observed dynamic effects, re-synthesize
    aug = Findings(capabilities=list(static.capabilities), imports=set(static.imports),
                   invariants=set(static.invariants), smells=list(static.smells))
    for k, m, t in effects:
        aug.capabilities.append(Capability(k, m, "dry-run", 0, scope=t))
    aug_bio = synthesize_bio("sample_app_dynamic", aug)

    # 5) enforce with the AUGMENTED constitution -> allowed
    aug_decision = decide(aug_bio, SANDBOX, "FILESYSTEM", "write", real_target)

    print("=" * 78)
    print("  DRY-RUN (LEARNING MODE) DEMO  —  closing the static-synthesis false-positive gap")
    print("=" * 78)
    print("  App analyzed/run:", os.path.relpath(APP_FILE, REPO_ROOT))
    print("-" * 78)
    print("  [static]   FILESYSTEM write scopes found by name-based analysis :",
          caps_of(static, "FILESYSTEM", "write") or "(only a variable hint — no concrete path)")
    print("  [dry-run]  effects OBSERVED at runtime                          :",
          [(m, t) for (k, m, t) in effects])
    print("  program's real write target                                    :", real_target)
    print("-" * 78)
    print("  Enforcement of the program's REAL write:")
    print("    STATIC-only constitution     ->", static_decision,
          "  <-- FALSE POSITIVE (blocks legitimate behaviour)" if static_decision == "DENY" else "")
    print("    DRY-RUN-augmented constitution->", aug_decision,
          "  <-- correct (observed effect was learned)" if aug_decision == "ALLOW" else "")
    print("=" * 78)

    ok = (static_decision == "DENY" and aug_decision == "ALLOW")
    if ok:
        print("  RESULT: PASS - the dry-run learned the concrete runtime effect and merged it")
        print("          before ratification, turning a false-positive block into a correct allow.")
        return 0
    print(f"  RESULT: FAIL (static={static_decision}, augmented={aug_decision})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
