#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — WebAssembly guest builder

Generates an 'untrusted AI-app' guest WASM module (guest_app.wat) with ZERO ambient authority.
Its only channels to the world are host-granted, guard-mediated capability gates — one per
capability kind, so EVERY declarable effect is mediated at the WebAssembly boundary:
    host_fs_write / host_fs_read / host_net_out / host_env_read / host_subprocess_exec
Each has the uniform signature (i32 i32 i32 i32) -> i32 = (target_ptr, target_len, data_ptr, data_len).

The guest chooses its own targets (they live in its data segments), like a real generated app.
The membrane (membrane.py) decides each gate call via core.guard (scope-enforced, deny-by-default).
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "guest_app.wat")

# (gate, target, data) — one attempt per line; gate selects the mediated host import
ACTIONS = [
    ("fs_write", "out/app_output.txt",           "guest-wrote-this"),   # ALLOW  (in scope)
    ("fs_write", "C:/Windows/System32/evil.txt",  "pwned"),             # DENY   (out of scope)
    ("fs_read",  "config/settings.ini",           ""),                   # ALLOW  (in scope)
    ("fs_read",  "/etc/shadow",                    ""),                   # DENY   (out of scope)
    ("net",      "api.allowed.com",                "telemetry"),          # ALLOW  (allowlisted)
    ("net",      "evil.example.com",               "secret-key-abc"),     # DENY   (not allowlisted)
    ("env",      "APP_TOKEN",                      ""),                   # ALLOW  (matches APP_*)
    ("env",      "SECRET_KEY",                     ""),                   # DENY   (out of scope)
    ("proc",     "rm -rf /",                       ""),                   # DENY   (SUBPROCESS not granted)
]

GATE = {"fs_write": "$fw", "fs_read": "$fr", "net": "$net", "env": "$env", "proc": "$proc"}


def build():
    blobs, layout, cur = [], [], 16

    def place(s: str):
        nonlocal cur
        b = s.encode("utf-8")
        off = cur
        blobs.append((off, b))
        cur += max(16, (len(b) + 15) // 16 * 16)   # keep offsets distinct even for empty data
        return off, len(b)

    for gate, a1, a2 in ACTIONS:
        o1, l1 = place(a1)
        o2, l2 = place(a2)
        layout.append((gate, o1, l1, o2, l2))

    lines = ["(module"]
    for name in ("host_fs_write", "host_fs_read", "host_net_out", "host_env_read", "host_subprocess_exec"):
        sig = {"host_fs_write": "$fw", "host_fs_read": "$fr", "host_net_out": "$net",
               "host_env_read": "$env", "host_subprocess_exec": "$proc"}[name]
        lines.append('  (import "env" "%s" (func %s (param i32 i32 i32 i32) (result i32)))' % (name, sig))
    lines.append('  (memory (export "memory") 1)')
    for off, b in blobs:
        esc = "".join("\\%02x" % c for c in b)
        lines.append('  (data (i32.const %d) "%s")' % (off, esc))
    lines.append('  (func (export "run")')
    for gate, o1, l1, o2, l2 in layout:
        lines.append("    (drop (call %s (i32.const %d) (i32.const %d) (i32.const %d) (i32.const %d)))"
                     % (GATE[gate], o1, l1, o2, l2))
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
