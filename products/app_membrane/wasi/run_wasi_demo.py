#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — WASI substrate DEMO (Product A, real programs)

Runs a REAL compiled program (guest.wasm, built from Rust) under the WASI capability model.
The membrane maps each .bio FILESYSTEM capability to a WASI preopen with matching permissions
(read -> READ_ONLY, write -> READ_WRITE). Claim proven: a real program can read the input,
write the output, and PHYSICALLY cannot write into the read-only input or touch anything
outside the granted preopens.

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
    input_dir = os.path.join(HERE, "input")
    output_dir = os.path.join(HERE, "output")
    stdout_path = os.path.join(HERE, "guest_stdout.txt")

    for d in (input_dir, output_dir):
        if os.path.isdir(d):
            shutil.rmtree(d)
    if os.path.exists(stdout_path):
        os.remove(stdout_path)

    # seed the read-only input the guest will read
    os.makedirs(input_dir, exist_ok=True)
    with open(os.path.join(input_dir, "data.txt"), "w", encoding="utf-8") as fh:
        fh.write("hello from the host input")

    if not os.path.exists(WASM):
        print("guest.wasm not found. Build it first:  bash build_guest_wasm.sh")
        return 2

    m = WasiMembrane(BIO, base_dir=HERE)
    m.run(WASM, stdout_path)

    guest_out = ""
    if os.path.exists(stdout_path):
        with open(stdout_path, encoding="utf-8") as fh:
            guest_out = fh.read()

    print("=" * 72)
    print("  WASI SUBSTRATE DEMO  (Product A - real compiled program)")
    print("=" * 72)
    print("  Constitution:", os.path.basename(BIO))
    print("  Guest:        guest.wasm (Rust -> wasm32-wasip1, zero ambient FS)")
    print("  Preopens derived from .bio (read -> READ_ONLY, write -> READ_WRITE):")
    for host_dir, guest_path, scope, mode, dperms, fperms in m.preopens:
        print(f"    '{scope}' ({mode:<5}) -> {guest_path:<8} [{dperms.name}] = {os.path.relpath(host_dir, HERE)}")
    print("-" * 72)
    print("  Guest's own report (its attempts):")
    for line in guest_out.strip().splitlines():
        print("    " + line)
    print("-" * 72)

    ok = True
    # output write performed?
    report = os.path.join(output_dir, "report.txt")
    if os.path.isfile(report):
        print("   [OK]  write to writable output PERFORMED:", os.path.relpath(report, HERE))
    else:
        print("   [FAIL] output write did NOT happen:", report)
        ok = False
    # write into read-only input must have been refused
    tamper = os.path.join(input_dir, "tamper.txt")
    if os.path.exists(tamper):
        print("   [FAIL] write into READ_ONLY input succeeded (leak!):", tamper)
        ok = False
    else:
        print("   [OK]  write into READ_ONLY input refused (no write capability):",
              os.path.relpath(tamper, HERE))
    # capability pattern from the guest's report
    reads = guest_out.count("READ ")
    wrote = guest_out.count("WROTE ")
    denied = guest_out.count("DENY ")
    if reads == 1 and wrote == 1 and denied == 2:
        print(f"   [OK]  capability pattern correct (READ={reads}, WROTE={wrote}, DENY={denied})")
    else:
        print(f"   [FAIL] expected READ=1 WROTE=1 DENY=2, got READ={reads} WROTE={wrote} DENY={denied}")
        ok = False

    print("=" * 72)
    if ok:
        print("  RESULT: PASS - a real program under WASI: the .bio read/write scopes became")
        print("          the only filesystem it could touch, at the right permission level.")
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
