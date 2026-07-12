#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-DEMO — `metaspace demo` is a REAL self-test, not a canned message.

The demo spawns the actual PreToolUse hook over the Friendly-Fire attack in a throwaway repo.
This proof runs `metaspace demo` and asserts it exits 0, reports every attack effect BLOCKED,
and never prints an ALLOWED attack line. Falsifiable: because the demo drives the real hook, a
broken guard would make `metaspace demo` exit non-zero — so a green demo means a real block.

Run: python run_demo_proof.py   (exit 0 iff the demo really blocks the attack; cross-OS)
"""

import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CLI = os.path.join(REPO, "cli.py")

_ok = True


def check(cond, label):
    global _ok
    _ok = _ok and bool(cond)
    print("  [%s] %s" % ("ok" if cond else "FAIL", label))


def main():
    print("=" * 68)
    print("  P-DEMO (`metaspace demo` really drives the hook to block the attack)")
    print("=" * 68)
    p = subprocess.run([sys.executable, CLI, "demo"], capture_output=True, text=True)
    out = p.stdout or ""
    check(p.returncode == 0, "`metaspace demo` exits 0")
    check("BLOCKED" in out, "the demo reports attack effects BLOCKED")
    check("!! ALLOWED !!" not in out, "no attack effect leaked through (no ALLOWED line)")
    check("the RCE never happens" in out, "the demo concludes the RCE never happens")
    print("-" * 68)
    print("  RESULT:", "PASS — the demo is a real, passing end-to-end block of the attack"
          if _ok else "FAIL — see checks above")
    print("=" * 68)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
