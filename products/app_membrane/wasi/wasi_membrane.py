#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — WASI substrate membrane (Product A, real programs)

The scalable form of the hard guarantee. Unlike the custom host-import demo (membrane.py),
this runs a REAL compiled program (any language -> wasm32-wasip1) under the STANDARD WASI
capability model:

  * WASI has no ambient filesystem. A guest can only reach directories the host PREOPENS.
  * The membrane derives the preopen set from the .bio CAPABILITIES `FILESYSTEM write` scope.
  * Any path outside a preopen has no capability -> the open fails. There is nothing to bypass.

Because it uses the standard WASI ABI, the same containment applies to any WASI-compiled
program (Rust, C, Go, Python), without per-app host functions.
"""

import os
import sys
import wasmtime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, REPO_ROOT)
from core.guard import parse_capabilities  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


class WasiMembrane:
    """Runs a wasm32-wasip1 guest with filesystem capabilities derived from a .bio."""

    def __init__(self, bio_path: str, base_dir: str = None):
        self.base_dir = os.path.abspath(base_dir or HERE)
        with open(bio_path, encoding="utf-8") as fh:
            bio = fh.read()
        # derive preopens from FILESYSTEM scopes, mapping read/write -> WASI permissions
        self.preopens = []   # (host_dir, guest_path, bio_scope, mode, dir_perms, file_perms)
        for kind, mode, scopes in parse_capabilities(bio):
            if kind == "FILESYSTEM" and mode in ("read", "write"):
                if mode == "write":
                    dperms, fperms = wasmtime.DirPerms.READ_WRITE, wasmtime.FilePerms.READ_WRITE
                else:
                    dperms, fperms = wasmtime.DirPerms.READ_ONLY, wasmtime.FilePerms.READ_ONLY
                for s in scopes:
                    prefix = s.split("/**")[0].split("/*")[0].strip("/")
                    if not prefix:
                        continue
                    host_dir = os.path.join(self.base_dir, prefix)
                    os.makedirs(host_dir, exist_ok=True)
                    self.preopens.append((host_dir, "/" + prefix, s, mode, dperms, fperms))

    def run(self, wasm_path: str, stdout_path: str):
        """Run the guest; its filesystem is limited to the derived preopens."""
        engine = wasmtime.Engine()
        store = wasmtime.Store(engine)
        wasi = wasmtime.WasiConfig()
        wasi.stdout_file = stdout_path
        for host_dir, guest_path, _scope, _mode, dperms, fperms in self.preopens:
            # the ONLY filesystem the guest sees, with read/write granularity from the .bio
            wasi.preopen_dir(host_dir, guest_path, dperms, fperms)
        store.set_wasi(wasi)

        linker = wasmtime.Linker(engine)
        linker.define_wasi()
        module = wasmtime.Module.from_file(engine, wasm_path)
        instance = linker.instantiate(store, module)
        start = instance.exports(store)["_start"]
        try:
            start(store)                      # WASI command entrypoint
        except wasmtime.ExitTrap:
            pass                              # proc_exit(0) is normal termination
        return self.preopens
