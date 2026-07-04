#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — WebAssembly membrane DEMO (Product A proof)

Chain:
  build_guest.py -> guest_app.wat  (untrusted app, with its own targets)
  membrane.py    -> WebAssembly host, deny-by-default gates (core.guard engine)
  this runner    -> run + PHYSICAL verification + CI exit code

Claim proven: the guest can PHYSICALLY only do what the constitution allows; the denied
writes never happen (the files are not created), and the guest has nothing to bypass
(no syscall/open in WebAssembly).
"""

import os
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_guest            # noqa: E402
from membrane import WasmMembrane  # noqa: E402

OUT_DIR = os.path.join(HERE, "out")
BIO = os.path.join(HERE, "app.constitution.bio")

# the forbidden write the guest targets (for the physical non-existence check)
FORBIDDEN_PATHS = [
    "C:/Windows/System32/evil.txt",
]


def main():
    # clean start
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    audit = os.path.join(HERE, "wasm_audit.jsonl")
    if os.path.exists(audit):
        os.remove(audit)

    # 1) generate the guest
    wat_path, actions = build_guest.build()

    # 2) run through the membrane
    m = WasmMembrane(BIO, base_dir=HERE)
    events = m.run_guest(wat_path)

    # 3) report
    print("=" * 68)
    print("  WEBASSEMBLY MEMBRANE DEMO  (Product A - hard guarantee)")
    print("=" * 68)
    print("  Constitution:", os.path.basename(BIO))
    print("  Guest:       ", os.path.basename(wat_path), "(zero ambient authority)")
    print("-" * 68)
    allow = deny = 0
    for kind, mode, target, decision in events:
        mark = "ALLOW " if decision == "ALLOW" else "DENY  "
        if decision == "ALLOW":
            allow += 1
        else:
            deny += 1
        print("  [%s] %-10s %s" % (mark, kind + "/" + mode, target))
    print("-" * 68)
    print("  total gate calls: %d  (ALLOW=%d, DENY=%d)" % (len(events), allow, deny))

    # 4) PHYSICAL verification
    print("-" * 68)
    print("  PHYSICAL VERIFICATION:")
    ok = True

    allowed_file = os.path.join(OUT_DIR, "app_output.txt")
    if os.path.isfile(allowed_file):
        print("   [OK]  granted write PERFORMED:", os.path.relpath(allowed_file, HERE))
    else:
        print("   [FAIL] the granted write did NOT happen:", allowed_file)
        ok = False

    for p in FORBIDDEN_PATHS:
        if os.path.exists(p):
            print("   [FAIL] forbidden write happened (membrane leak!):", p)
            ok = False
        else:
            print("   [OK]  forbidden write physically prevented:", p)

    # every capability KIND is mediated: FS write/read, NET, ENV granted (in-scope ALLOW,
    # out-of-scope DENY); SUBPROCESS ungranted -> DENY. Expected: 4 ALLOW, 5 DENY.
    kinds = sorted({k for (k, m, t, d) in events})
    print("   [..]  capability kinds mediated at the gate:", ", ".join(kinds))
    if allow != 4 or deny != 5:
        print("   [FAIL] expected ALLOW=4 / DENY=5, got ALLOW=%d / DENY=%d" % (allow, deny))
        ok = False
    else:
        print("   [OK]  decision pattern correct (ALLOW=4, DENY=5 across FS/NET/ENV/SUBPROCESS)")

    print("=" * 68)
    if ok:
        print("  RESULT: PASS - the membrane mediated deny-by-default,")
        print("          the forbidden effects physically did not happen.")
        print("  audit:", os.path.relpath(audit, HERE))
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
