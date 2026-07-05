#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — self-falsification audit (anti-slop proof)

'AI-slop' would be proofs that pass regardless of the code. This proof tests the opposite and
FAILS if the repo is hollow. Three falsification probes:

  P1  the decision READS the constitution      -> mutate the .bio, the decision must flip
  P2  the proofs are COUPLED to the code        -> sabotage guard.check(), a proof must FAIL
  P3  enforcement is by a REAL substrate        -> wasmtime itself refuses an ungranted syscall

If all three hold, the other proofs are measuring real behaviour, not printing PASS. This file
is deliberately included so the repository can falsify itself.
"""

import os
import io
import sys
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "evidence", "demos"))
sys.path.insert(0, os.path.join(REPO_ROOT, "products", "app_membrane"))

AUDIT = os.path.join(HERE, "_falsify_audit.jsonl")
APP_BIO = os.path.join(REPO_ROOT, "products", "app_membrane", "app.constitution.bio")


def probe1():
    from core.guard import Guard, ConstitutionViolation

    def decide(bio, k, m, t):
        g = Guard(bio, base_dir=REPO_ROOT, audit_path=AUDIT)
        try:
            g.check(k, m, t); return "ALLOW"
        except ConstitutionViolation:
            return "DENY"

    no_grant = decide("CAPABILITIES {\n}", "SUBPROCESS", "exec", "ls")
    granted = decide('CAPABILITIES {\n  SUBPROCESS exec "*"\n}', "SUBPROCESS", "exec", "ls")
    ok = (no_grant == "DENY" and granted == "ALLOW")
    print("P1  mutate the .bio, watch the decision flip:")
    print(f"      SUBPROCESS not granted -> {no_grant}   granted -> {granted}")
    print(f"      => data-driven, not hardcoded: {'YES' if ok else 'NO (SLOP)'}")
    return ok


def probe2():
    import core.guard as gmod
    import run_threat_matrix_demo as demo

    orig = gmod.Guard.check
    gmod.Guard.check = lambda self, *a, **k: True     # sabotage: allow everything
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc_broken = demo.main()
    finally:
        gmod.Guard.check = orig                        # restore
    with contextlib.redirect_stdout(io.StringIO()):
        rc_ok = demo.main()
    ok = (rc_broken != 0 and rc_ok == 0)
    print("P2  sabotage guard.check() to always-ALLOW, re-run a proof:")
    print(f"      sabotaged -> exit {rc_broken} (must be nonzero)   restored -> exit {rc_ok} (must be 0)")
    print(f"      => proof is coupled to real enforcement: {'YES' if ok else 'NO (SLOP)'}")
    return ok


def probe3():
    import wasmtime
    from membrane import WasmMembrane

    m = WasmMembrane(APP_BIO, base_dir=os.path.dirname(APP_BIO))
    mal = ('(module (import "wasi_snapshot_preview1" "path_open" '
           '(func (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32))) '
           '(memory (export "memory") 1) (func (export "run")))')
    try:
        m.make_linker().instantiate(m.store, wasmtime.Module(m.engine, mal))
        ok, msg = False, "guest linked (BAD)"
    except Exception as e:
        msg = str(e).splitlines()[0]
        ok = "unknown import" in msg.lower()
    print("P3  a guest reaching an ungranted syscall is refused by wasmtime itself:")
    print(f"      -> {msg}")
    print(f"      => enforced by a real substrate, not simulated: {'YES' if ok else 'NO'}")
    return ok


def main():
    print("=" * 80)
    print("  SELF-FALSIFICATION AUDIT  (the repo tries to prove itself hollow — and fails to)")
    print("=" * 80)
    results = [probe1(), print("") or probe2(), print("") or probe3()]
    if os.path.exists(AUDIT):
        os.remove(AUDIT)
    print("=" * 80)
    ok = all(results)
    print("  RESULT:", "PASS - proofs are real, code-coupled, substrate-enforced (NOT slop)"
          if ok else "FAIL - falsification succeeded (the proofs are hollow)")
    print("=" * 80)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
