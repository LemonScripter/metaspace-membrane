#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — Guard (capability decision engine)

Loads a constitution (the CAPABILITIES block of a `.bio` file), then mediates the
REAL effects of code (filesystem / network / subprocess). Deny-by-default: anything
not present in the constitution is deterministically blocked (ConstitutionViolation)
and written to an audit log.

This is BOTH the membrane (negative guarantee) and the engine behind the conformance
tests (positive): a negative test asserts the guard blocks; a positive test asserts a
granted capability passes.

HONEST LIMIT: monkeypatching at the language level is bypassable (ctypes, direct
syscalls). That is the demo/CI layer; the HARD guarantee is the WebAssembly membrane
(see products/app_membrane). The same `check()` engine powers all layers.
"""

import os
import re
import sys
import json
import builtins
import fnmatch
import datetime

KINDS = {"FILESYSTEM", "NETWORK", "ENV", "SUBPROCESS", "HARDWARE", "IMPORT_PATH"}


class ConstitutionViolation(Exception):
    """An effect outside the constitution — a deterministic block."""


# ---------------------------------------------------------------------------
# .bio CAPABILITIES parser (tolerant: handles both authored and generated formats)
# ---------------------------------------------------------------------------
def parse_capabilities(bio_text: str):
    """-> list of (kind, mode, [scopes])."""
    caps = []
    in_block = False
    for line in bio_text.splitlines():
        if not in_block:
            if re.search(r"\bCAPABILITIES\b\s*\{", line):
                in_block = True
            continue
        if "}" in line:
            break
        m = re.match(r"\s*([A-Z_]+)\s+([a-z0-9_]+)", line)
        if m and m.group(1) in KINDS:
            kind, mode = m.group(1), m.group(2)
            scopes = re.findall(r'"([^"]*)"', line)   # inline OR a 'scope:' comment
            caps.append((kind, mode, scopes))
    return caps


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------
class Guard:
    def __init__(self, bio_text: str, base_dir: str, audit_path: str = None,
                 provenance: str = "SYNTHESIZED", require_ratified: bool = False):
        self.base_dir = os.path.abspath(base_dir)
        self.provenance = provenance
        if require_ratified:
            # production gate: only a RATIFIED constitution may run (fail-closed).
            # lazy import to avoid a circular import (gate -> provenance -> guard).
            _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if _root not in sys.path:
                sys.path.insert(0, _root)
            from core.gate import gate as _gate
            self.provenance = _gate(bio_text, require_ratified=True)   # raises if not RATIFIED
        self.audit_path = audit_path or os.path.join(self.base_dir, "audit.jsonl")
        self.allowed = {}          # (kind, mode) -> [scope globs]
        for kind, mode, scopes in parse_capabilities(bio_text):
            self.allowed.setdefault((kind, mode), []).extend(scopes)
        self._orig = {}
        self.decisions = []        # kept in memory too (the test generator inspects it)

    # --- path normalisation ---
    def _norm(self, p: str) -> str:
        if not os.path.isabs(p):
            p = os.path.join(self.base_dir, p)
        return os.path.normpath(p).replace("\\", "/")

    def _scope_ok(self, target: str, scopes) -> bool:
        if not scopes:            # no scope given -> the kind/mode applies to anything
            return True
        if any(s.strip() in ("*", "**", "/**") for s in scopes):  # match-all
            return True
        t = self._norm(target)
        for s in scopes:
            if fnmatch.fnmatch(t, self._norm(s)):
                return True
        return False

    def _net_ok(self, target: str, scopes) -> bool:
        # network host allowlist — not a path, so handled separately (no _norm)
        if not scopes:
            return True
        host = str(target).split(":")[0].strip()   # "host:port" -> host
        for s in scopes:
            s = s.strip()
            if s in ("*", "**") or fnmatch.fnmatch(host, s):
                return True
        return False

    # --- the decision core ---
    def check(self, kind: str, mode: str, target: str = None) -> bool:
        scopes = self.allowed.get((kind, mode))
        if scopes is None:
            allow, reason = False, f"{kind}/{mode} not in the constitution (deny-by-default)"
        elif kind == "FILESYSTEM" and target is not None and not self._scope_ok(target, scopes):
            allow, reason = False, f"{kind}/{mode} '{target}' outside the granted scope ({scopes})"
        elif kind == "NETWORK" and target is not None and not self._net_ok(target, scopes):
            allow, reason = False, f"{kind}/{mode} '{target}' host not in the allowlist ({scopes})"
        else:
            allow, reason = True, "allowed by the constitution"
        self._log(kind, mode, target, allow, reason)
        if not allow:
            raise ConstitutionViolation(f"[MEMBRANE BLOCK] {kind}/{mode} target={target} :: {reason}")
        return True

    def _log(self, kind, mode, target, allow, reason):
        rec = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "kind": kind, "mode": mode, "target": target,
            "decision": "ALLOW" if allow else "DENY",
            "reason": reason, "provenance": self.provenance,
        }
        self.decisions.append(rec)
        _open = self._orig.get("open", builtins.open)
        with _open(self.audit_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # --- interception (language-level demo layer; bypassable, see module docstring) ---
    def activate(self):
        import socket
        import subprocess

        self._orig = {
            "open": builtins.open,
            "system": os.system,
            "socket": socket.socket,
            "create_connection": socket.create_connection,
            "Popen": subprocess.Popen,
        }
        guard = self

        def g_open(file, mode="r", *a, **k):
            m = "write" if any(ch in str(mode) for ch in "wax+") else "read"
            guard.check("FILESYSTEM", m, str(file))
            return guard._orig["open"](file, mode, *a, **k)

        def g_system(cmd):
            guard.check("SUBPROCESS", "exec", str(cmd))
            return guard._orig["system"](cmd)

        def g_socket(*a, **k):
            guard.check("NETWORK", "out", "socket()")
            return guard._orig["socket"](*a, **k)

        def g_create_connection(address, *a, **k):
            guard.check("NETWORK", "out", str(address))
            return guard._orig["create_connection"](address, *a, **k)

        def g_popen(args, *a, **k):
            guard.check("SUBPROCESS", "exec", str(args))
            return guard._orig["Popen"](args, *a, **k)

        builtins.open = g_open
        os.system = g_system
        socket.socket = g_socket
        socket.create_connection = g_create_connection
        subprocess.Popen = g_popen
        return self

    def deactivate(self):
        import socket
        import subprocess
        if not self._orig:
            return
        builtins.open = self._orig["open"]
        os.system = self._orig["system"]
        socket.socket = self._orig["socket"]
        socket.create_connection = self._orig["create_connection"]
        subprocess.Popen = self._orig["Popen"]

    def __enter__(self):
        return self.activate()

    def __exit__(self, *exc):
        self.deactivate()
        return False
