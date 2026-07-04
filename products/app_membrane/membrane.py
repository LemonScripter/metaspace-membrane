#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — WebAssembly membrane (Product A: the HARD guarantee)

Difference from the language-level guard (which is bypassable via ctypes / direct
syscalls):
  * Language level: the code has ambient authority (it has `open`, sockets); the guard
    mediates by getting in the way -> BYPASSABLE.
  * WebAssembly (this): the guest module has NO ambient authority. No WASI, no syscalls,
    no `open`. Its ONLY channel to the outside world is a host-granted import function.
    Every such gate goes through core.guard.Guard.check() (the same engine that powers
    the app and agent membranes). What we do not grant, the guest physically cannot do
    -> there is nothing to bypass. That is unbypassability.

On ALLOW the membrane PERFORMS the real effect (filesystem: an actual write); on DENY it
does not perform it and returns an error code to the guest.
"""

import os
import sys
import wasmtime

# reuse the shared decision engine (core/guard.py)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
from core.guard import Guard, ConstitutionViolation  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# guest -> membrane call result codes
R_ALLOW = 0
R_DENY = 1


class WasmMembrane:
    """Deny-by-default WebAssembly host: the guest only sees the granted, guarded gates."""

    def __init__(self, bio_path: str, base_dir: str = None, audit_path: str = None):
        self.base_dir = os.path.abspath(base_dir or HERE)
        with open(bio_path, encoding="utf-8") as fh:
            bio_text = fh.read()
        self.guard = Guard(
            bio_text, base_dir=self.base_dir,
            audit_path=audit_path or os.path.join(HERE, "wasm_audit.jsonl"),
            provenance="SYNTHESIZED",
        )
        self.events = []          # (kind, mode, target, decision) - inspected by the demo
        self._ctx = {}            # after instantiate: {"memory": Memory}
        self.engine = wasmtime.Engine()
        self.store = wasmtime.Store(self.engine)

    # --- read guest memory (ptr, len) ---
    def _read(self, ptr: int, length: int) -> str:
        mem = self._ctx["memory"]
        raw = mem.read(self.store, ptr, ptr + length)
        return bytes(raw).decode("utf-8", "replace")

    # --- the two granted gates (both guarded) ---
    def _host_fs_write(self, path_ptr, path_len, data_ptr, data_len):
        target = self._read(path_ptr, path_len)
        data = self._read(data_ptr, data_len)
        try:
            self.guard.check("FILESYSTEM", "write", target)
        except ConstitutionViolation:
            self.events.append(("FILESYSTEM", "write", target, "DENY"))
            return R_DENY
        # ALLOW -> REAL effect: write into the sandbox
        abs_path = target if os.path.isabs(target) else os.path.join(self.base_dir, target)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(data)
        self.events.append(("FILESYSTEM", "write", target, "ALLOW"))
        return R_ALLOW

    def _host_net_out(self, host_ptr, host_len, data_ptr, data_len):
        target = self._read(host_ptr, host_len)
        _payload = self._read(data_ptr, data_len)
        try:
            self.guard.check("NETWORK", "out", target)
        except ConstitutionViolation:
            self.events.append(("NETWORK", "out", target, "DENY"))
            return R_DENY
        # ALLOW -> the real outbound call would go here; simulated in the demo (no actual
        # network). The point is the deterministic decision and the mediation.
        self.events.append(("NETWORK", "out", target, "ALLOW"))
        return R_ALLOW

    def _decide(self, kind, mode, target):
        try:
            self.guard.check(kind, mode, target)
            self.events.append((kind, mode, target, "ALLOW"))
            return R_ALLOW
        except ConstitutionViolation:
            self.events.append((kind, mode, target, "DENY"))
            return R_DENY

    def _host_fs_read(self, path_ptr, path_len, _dp, _dl):
        return self._decide("FILESYSTEM", "read", self._read(path_ptr, path_len))

    def _host_env_read(self, name_ptr, name_len, _dp, _dl):
        return self._decide("ENV", "read", self._read(name_ptr, name_len))

    def _host_subprocess_exec(self, cmd_ptr, cmd_len, _dp, _dl):
        # the decision is the point; on ALLOW the exec is simulated (no real subprocess)
        return self._decide("SUBPROCESS", "exec", self._read(cmd_ptr, cmd_len))

    def make_linker(self):
        """The membrane defines the GRANTED gates by NAME (capability import) — one per
        capability kind, so every declarable effect is mediated. Anything not put here yields
        'unknown import' for the guest -> no ambient authority. This is the capability membrane."""
        i32x4 = wasmtime.FuncType([wasmtime.ValType.i32()] * 4, [wasmtime.ValType.i32()])
        linker = wasmtime.Linker(self.engine)
        gates = {
            "host_fs_write": self._host_fs_write,
            "host_fs_read": self._host_fs_read,
            "host_net_out": self._host_net_out,
            "host_env_read": self._host_env_read,
            "host_subprocess_exec": self._host_subprocess_exec,
        }
        for name, fn in gates.items():
            linker.define(self.store, "env", name, wasmtime.Func(self.store, i32x4, fn))
        return linker

    # --- load + run guest ---
    def run_guest(self, wat_path: str):
        module = wasmtime.Module.from_file(self.engine, wat_path)
        linker = self.make_linker()
        instance = linker.instantiate(self.store, module)   # name-based linking
        exports = instance.exports(self.store)
        self._ctx["memory"] = exports["memory"]
        exports["run"](self.store)          # the guest calls the gates here
        return self.events
