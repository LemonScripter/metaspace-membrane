#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — REAL program under the WASI membrane (not a toy)

Runs a real log-analysis utility (real_app.wasm, ~90 lines of Rust: directory scan, per-file
parsing, aggregation, ranking, report writing) under the WASI membrane. Two things are proven
at once, on real work:

  1) CORRECTNESS of real work: the program reads real input logs it was granted, and the report
     it writes contains the CORRECT computed statistics (we seed known inputs and check the numbers).
  2) CONTAINMENT: the program's filesystem is bounded to the .bio grant; its attempt to read a
     system file outside the grant is refused by the WASI runtime.

Prebuilt real_app.wasm is committed, so this runs with only `pip install wasmtime`.
Rebuild: bash build_real_app.sh
"""

import os
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "wasi"))
from wasi_membrane import WasiMembrane  # noqa: E402

BIO = os.path.join(HERE, "real_app.constitution.bio")
WASM = os.path.join(HERE, "real_app.wasm")
SANDBOX = os.path.join(HERE, "real_app_sandbox")

# real input logs (known content -> known expected statistics)
LOGS = {
    "app.log": "INFO started\nERROR db connection failed\nWARN slow query\nERROR timeout\nINFO done\n",
    "web.log": "INFO request\nERROR 500 internal\nINFO ok\n",
}
# expected aggregate the Rust program must compute from the above
EXPECT = {"files": 2, "lines": 8, "errors": 3, "warns": 1, "noisiest": "app.log"}


def main():
    if os.path.isdir(SANDBOX):
        shutil.rmtree(SANDBOX)
    in_dir = os.path.join(SANDBOX, "input")
    os.makedirs(in_dir, exist_ok=True)
    for name, content in LOGS.items():
        with open(os.path.join(in_dir, name), "w", encoding="utf-8") as fh:
            fh.write(content)
    stdout_path = os.path.join(SANDBOX, "guest_stdout.txt")

    if not os.path.exists(WASM):
        print("real_app.wasm not found. Build it first:  bash build_real_app.sh")
        return 2

    m = WasiMembrane(BIO, base_dir=SANDBOX)   # preopens: input READ_ONLY, output READ_WRITE
    m.run(WASM, stdout_path)

    guest_out = open(stdout_path, encoding="utf-8").read() if os.path.exists(stdout_path) else ""
    report_path = os.path.join(SANDBOX, "output", "report.txt")
    report = open(report_path, encoding="utf-8").read() if os.path.exists(report_path) else ""

    print("=" * 78)
    print("  REAL PROGRAM UNDER THE WASI MEMBRANE  (real work + containment, one run)")
    print("=" * 78)
    print("  Constitution:", os.path.basename(BIO))
    print("  Program:      real_app.wasm (Rust -> wasm32-wasip1; dir scan + parse + aggregate)")
    print("  Preopens from .bio:")
    for host_dir, guest_path, scope, mode, dperms, fperms in m.preopens:
        print(f"    '{scope}' ({mode:<5}) -> {guest_path:<8} [{dperms.name}]")
    print("-" * 78)
    print("  Program stdout:")
    for line in guest_out.strip().splitlines():
        print("    " + line)
    print("-" * 78)
    print("  Report it wrote (/output/report.txt):")
    for line in report.strip().splitlines():
        print("    " + line)
    print("-" * 78)

    ok = True
    # 1) real work: the report must contain the CORRECT totals
    want = ("TOTAL: files=%d lines=%d errors=%d warns=%d"
            % (EXPECT["files"], EXPECT["lines"], EXPECT["errors"], EXPECT["warns"]))
    if want in report:
        print("   [OK]  real work correct: report TOTAL matches the known input ->", want.split("TOTAL: ")[1])
    else:
        print("   [FAIL] report TOTAL is wrong or missing; expected:", want)
        ok = False
    if ("NOISIEST: %s" % EXPECT["noisiest"]) in report:
        print("   [OK]  aggregation correct: noisiest file identified ->", EXPECT["noisiest"])
    else:
        print("   [FAIL] noisiest-file aggregation wrong")
        ok = False
    # 2) containment: the out-of-grant read was refused
    if "contained: /etc/passwd refused" in guest_out:
        print("   [OK]  containment: the out-of-grant read of /etc/passwd was refused by WASI")
    elif "LEAK" in guest_out:
        print("   [FAIL] the program read a file outside its grant (membrane leak!)")
        ok = False
    else:
        print("   [FAIL] could not confirm the containment attempt")
        ok = False

    print("=" * 78)
    if ok:
        print("  RESULT: PASS - a real program did real work on exactly the files it was granted,")
        print("          and could not touch anything outside its .bio. Real work + real containment.")
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
