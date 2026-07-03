#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — ratification gate demo (production enforcement)

The gate closes the provenance chain: a Guard created with require_ratified=True runs ONLY
if the constitution is RATIFIED. This proves the end-to-end policy:

  synthesized (not reviewed)      -> REFUSED  (fail-closed)
  ratified   (human-approved)     -> RUNS, and enforces deny-by-default
  tampered   (widened afterwards) -> REFUSED  (fingerprint mismatch)

A policy becomes enforceable only by human ratification, and cannot be broadened afterwards.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO_ROOT)
from core.capability_analyzer import analyze_path, synthesize_bio  # noqa: E402
from core.provenance import ratify                                 # noqa: E402
from core.guard import Guard, ConstitutionViolation                # noqa: E402
from core.gate import UnratifiedConstitution                       # noqa: E402

APP = os.path.join(HERE, "synth_demo", "sample_app.py")
BASE = os.path.dirname(APP)
AUDIT = os.path.join(HERE, "gate_audit.jsonl")


def try_load(bio):
    """Attempt to build a production (ratified-only) Guard. -> ('RUNS', guard) or ('REFUSED', None)."""
    try:
        g = Guard(bio, base_dir=BASE, audit_path=AUDIT, require_ratified=True)
        return "RUNS", g
    except UnratifiedConstitution:
        return "REFUSED", None


def decide(g, kind, mode, target):
    try:
        g.check(kind, mode, target)
        return "ALLOW"
    except ConstitutionViolation:
        return "DENY"


def main():
    if os.path.exists(AUDIT):
        os.remove(AUDIT)

    bio = synthesize_bio("sample_app", analyze_path(APP))
    ratified = ratify(bio, when="2026-07-03")
    tampered = ratified.replace("CAPABILITIES {", "CAPABILITIES {\n    SUBPROCESS exec ;", 1)

    r1, _ = try_load(bio)         # SYNTHESIZED -> expect REFUSED
    r2, g = try_load(ratified)    # RATIFIED    -> expect RUNS
    r3, _ = try_load(tampered)    # TAMPERED    -> expect REFUSED

    # when the ratified constitution runs, confirm it still enforces deny-by-default
    enforce = "n/a"
    enforce_ok = True
    if g is not None:
        a = decide(g, "FILESYSTEM", "read", "config.json")   # declared -> ALLOW
        b = decide(g, "SUBPROCESS", "exec", "anything")      # undeclared -> DENY
        enforce = f"declared read={a}, undeclared subprocess={b}"
        enforce_ok = (a == "ALLOW" and b == "DENY")

    print("=" * 70)
    print("  RATIFICATION GATE DEMO  (production: only RATIFIED runs)")
    print("=" * 70)
    print(f"  synthesized (not reviewed)      -> {r1}")
    print(f"  ratified   (human-approved)     -> {r2}   [{enforce}]")
    print(f"  tampered   (widened afterwards) -> {r3}")
    print("=" * 70)

    ok = (r1 == "REFUSED" and r2 == "RUNS" and r3 == "REFUSED" and enforce_ok)
    if ok:
        print("  RESULT: PASS - the gate admits only a RATIFIED constitution; unreviewed and")
        print("          tampered policies are refused (fail-closed), and the admitted one enforces.")
        return 0
    print(f"  RESULT: FAIL (synthesized={r1}, ratified={r2}, tampered={r3}, enforce_ok={enforce_ok})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
