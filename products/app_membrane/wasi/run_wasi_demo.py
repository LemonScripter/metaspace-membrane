#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — WASI substrate DEMO (Product A, real programs)

Runs a REAL compiled program (guest.wasm, built from Rust) under the WASI capability model.
The membrane grants filesystem access only as preopens derived from the .bio. Claim proven:
a real program can PHYSICALLY only write inside the granted sandbox; out-of-scope opens fail
for lack of capability, and there is no ambient path to escape through.

Prebuilt guest.wasm is committed, so this runs with only `pip install wasmtime`. To rebuild
the guest: bash build_guest_wasm.sh
"""

import os
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from wasi_membrane import WasiMembrane  # noqa: E402

BIO = os.path.join(HERE, "app.constitution.bio")
WASM = os.path.join(HERE, "guest.wasm")


def main():
    sandbox = os.path.join(HERE, "sandbox")
    escape = os.path.join(HERE, "escape.txt")
    stdout_path = os.path.join(HERE, "guest_stdout.txt")
    for p in (sandbox,):
        if os.path.isdir(p):
            shutil.rmtree(p)
    for p in (escape, stdout_path):
        if os.path.exists(p):
            os.remove(p)

    if not os.path.exists(WASM):
        print("guest.wasm not found. Build it first:  bash build_guest_wasm.sh")
        return 2

    m = WasiMembrane(BIO, base_dir=HERE)
    m.run(WASM, stdout_path)

    guest_out = ""
    if os.path.exists(stdout_path):
        with open(stdout_path, encoding="utf-8") as fh:
            guest_out = fh.read()

    print("=" * 70)
    print("  WASI SUBSTRATE DEMO  (Product A - real compiled program)")
    print("=" * 70)
    print("  Constitution:", os.path.basename(BIO))
    print("  Guest:        guest.wasm (Rust -> wasm32-wasip1, zero ambient FS)")
    print("  Preopens derived from .bio:")
    for host_dir, guest_path, scope in m.preopens:
        print(f"    '{scope}'  ->  preopen {guest_path}  = {os.path.relpath(host_dir, HERE)}")
    print("-" * 70)
    print("  Guest's own report (its attempts):")
    for line in guest_out.strip().splitlines():
        print("    " + line)
    print("-" * 70)

    ok = True
    # in-scope write performed?
    allowed_file = os.path.join(sandbox, "app_output.txt")
    if os.path.isfile(allowed_file):
        print("   [OK]  granted write PERFORMED:", os.path.relpath(allowed_file, HERE))
    else:
        print("   [FAIL] granted write did NOT happen:", allowed_file)
        ok = False
    # traversal escape must not exist
    if os.path.exists(escape):
        print("   [FAIL] traversal escaped the sandbox (leak!):", escape)
        ok = False
    else:
        print("   [OK]  traversal escape physically prevented:", os.path.relpath(escape, HERE))
    # guest must report exactly 1 WROTE and 2 DENY
    wrote = guest_out.count("WROTE ")
    denied = guest_out.count("DENY ")
    if wrote == 1 and denied == 2:
        print(f"   [OK]  capability pattern correct (WROTE={wrote}, DENY={denied})")
    else:
        print(f"   [FAIL] expected WROTE=1 DENY=2, got WROTE={wrote} DENY={denied}")
        ok = False

    print("=" * 70)
    if ok:
        print("  RESULT: PASS - a real program, contained by the WASI capability model;")
        print("          the .bio scope became the only filesystem it could touch.")
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
