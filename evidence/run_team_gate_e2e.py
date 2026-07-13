#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — Team / CI gate proof (M4).

The team surface: a repository commits a ratified `metaspace.bio`, and CI runs
`metaspace gate metaspace.bio`, which exits 0 ONLY if the constitution is RATIFIED (human-
approved) and unchanged since. This makes "the effect boundary in this repo is human-ratified
and has not been silently broadened" a build-breaking condition — the same content-bound
ratification as the runtime gate, now enforced at merge time.

This proof drives the REAL `metaspace` CLI through exactly what CI would do:
  1. an unratified constitution  -> gate exits non-zero  (CI RED: not ratified)
  2. a human ratifies it         -> gate exits 0          (CI GREEN)
  3. someone broadens it after ratifying -> gate exits non-zero (CI RED: TAMPERED)

It needs no hosted CI: the gate is a local command, and its exit code is the build signal.
(GitHub Actions is disabled on this repo, so there is no hosted-CI badge; the gate is verified
locally and on real Linux instead — an honest, stated limitation.)

Run:  python evidence/run_team_gate_e2e.py     (exit 0 if the gate behaves as a CI gate must)
"""

import os
import sys
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
CLI = os.path.join(REPO_ROOT, "cli.py")

TEAM_BIO = """CELL TeamApp {
  CAPABILITIES {
    FILESYSTEM write "src/**";
    NETWORK    out   "api.example.com";
  }
}
"""


def gate(bio_path):
    """Run `metaspace gate` as CI would; return its exit code (0 = green)."""
    p = subprocess.run([sys.executable, CLI, "gate", bio_path],
                       capture_output=True, text=True)
    return p.returncode


def main():
    repo = tempfile.mkdtemp(prefix="team_repo_")
    bio = os.path.join(repo, "metaspace.bio")
    with open(bio, "w", encoding="utf-8") as f:
        f.write(TEAM_BIO)

    steps = []

    # 1) committed but NOT ratified -> CI must fail
    rc1 = gate(bio)
    steps.append(("unratified constitution -> gate FAILS the build (exit != 0)", rc1 != 0))

    # 2) a human ratifies it (metaspace ratify --yes) -> CI must pass
    r = subprocess.run([sys.executable, CLI, "ratify", bio, "--yes"],
                       capture_output=True, text=True)
    steps.append(("`metaspace ratify --yes` succeeds (exit 0)", r.returncode == 0))
    rc2 = gate(bio)
    steps.append(("ratified constitution -> gate PASSES the build (exit 0)", rc2 == 0))

    # 3) someone broadens the ENFORCED policy AFTER ratifying (widens the write scope in place,
    #    src/** -> /**) -> the content-bound fingerprint no longer matches -> CI must fail
    ratified = open(bio, encoding="utf-8").read()
    assert '"src/**"' in ratified, "expected the ratified policy to still contain the scope"
    with open(bio, "w", encoding="utf-8") as f:
        f.write(ratified.replace('"src/**"', '"/**"'))   # sneaky post-ratification broadening
    rc3 = gate(bio)
    steps.append(("broadened-after-ratify -> gate FAILS the build (TAMPERED, exit != 0)", rc3 != 0))

    print("=" * 72)
    print("  MetaSpace TEAM / CI gate proof (M4)")
    print("=" * 72)
    print("  repo constitution :", bio)
    print("  (each step is exactly what `metaspace gate` returns to CI)")
    print("-" * 72)
    ok = True
    for name, cond in steps:
        print("  [%s]  %s" % ("OK" if cond else "FAIL", name))
        ok = ok and bool(cond)
    print("=" * 72)
    if ok:
        print("  RESULT: PASS — the CI gate admits only a human-ratified, unbroadened constitution;")
        print("          an unratified or post-ratification-widened one breaks the build.")
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
