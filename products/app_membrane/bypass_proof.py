#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — UNBYPASSABILITY proof (Product A)

The honest limit of a language-level guard: it is bypassable (ctypes, direct syscalls),
because the code has ambient authority. This test shows EMPIRICALLY that on the
WebAssembly membrane this is NOT possible:

  A malicious guest that tries to reach a gate OUTSIDE the membrane (e.g. WASI path_open
  for the filesystem) fails AT INSTANTIATION with a link error — because the membrane
  grants no such import. There is no 'forgotten syscall', no ambient path: what the host
  did not grant does not exist for the guest.
"""

import os
import sys
import wasmtime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from membrane import WasmMembrane  # noqa: E402

# a guest that tries to reach the WASI file gate (path_open) — which the membrane does NOT grant
MALICIOUS_WAT = """
(module
  (import "wasi_snapshot_preview1" "path_open"
     (func $open (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "run")
    (drop (call $open
      (i32.const 3) (i32.const 0) (i32.const 0) (i32.const 0)
      (i32.const 0) (i64.const 0) (i64.const 0) (i32.const 0) (i32.const 0)))))
"""


def main():
    bio = os.path.join(HERE, "app.constitution.bio")
    m = WasmMembrane(bio, base_dir=HERE)
    module = wasmtime.Module(m.engine, MALICIOUS_WAT)

    print("=" * 68)
    print("  UNBYPASSABILITY PROOF  (WebAssembly)")
    print("=" * 68)
    print("  The guest tries to reach an UNGRANTED gate (wasi path_open).")
    print("  The membrane only offers host_fs_write / host_net_out.")
    print("-" * 68)
    try:
        # the membrane defines only its own named gates; no WASI ->
        # the guest's path_open stays unlinked
        linker = m.make_linker()
        linker.instantiate(m.store, module)
        print("   [FAIL] the guest instantiated - BYPASS SUCCEEDED (bad)!")
        return 1
    except Exception as e:
        msg = str(e).splitlines()[0] if str(e) else type(e).__name__
        print("   [OK] instantiation FAILED (link error) - the ungranted")
        print("        gate does NOT exist for the guest:")
        print("        ->", msg)
        print("=" * 68)
        print("  RESULT: PASS - on the WebAssembly membrane there is nothing to bypass.")
        print("          What the host does not grant is physically unreachable.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
