#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — dynamic dry-run ("learning mode")

Static synthesis is name-based and under-declares on dynamic code (a path or host built at
runtime is only a variable hint, not a concrete value). If such an incomplete constitution is
ratified, the runtime membrane blocks perfectly normal behaviour — a false positive that pushes
developers toward dangerous wildcards.

The dry-run closes that gap. It runs the program once with the real effect functions
(`builtins.open`, `socket`, `subprocess`) intercepted in RECORD mode — it observes, it does not
block — and reports the CONCRETE effects the program actually took. Those observed effects are
merged into the statically synthesized constitution BEFORE a human ratifies it, so the human
approves a constitution that matches reality.

This module records; it does not enforce. The enforcement is still the runtime membrane.
"""

import os
import builtins


class Recorder:
    """Intercepts real effects in RECORD mode (observe, never block)."""

    def __init__(self):
        self.effects = []          # list of (kind, mode, target)
        self._orig = {}

    def _add(self, kind, mode, target):
        rec = (kind, mode, str(target))
        if rec not in self.effects:
            self.effects.append(rec)

    def __enter__(self):
        import socket
        import subprocess
        rec = self
        self._orig = {
            "open": builtins.open,
            "create_connection": socket.create_connection,
            "Popen": subprocess.Popen,
            "socket_mod": socket,
            "subprocess_mod": subprocess,
        }

        def g_open(file, mode="r", *a, **k):
            m = "write" if any(ch in str(mode) for ch in "wax+") else "read"
            rec._add("FILESYSTEM", m, file)
            return rec._orig["open"](file, mode, *a, **k)

        def g_cc(address, *a, **k):
            host = address[0] if isinstance(address, tuple) and address else address
            rec._add("NETWORK", "out", host)
            return rec._orig["create_connection"](address, *a, **k)

        def g_popen(args, *a, **k):
            prog = args[0] if isinstance(args, (list, tuple)) and args else args
            rec._add("SUBPROCESS", "exec", prog)
            return rec._orig["Popen"](args, *a, **k)

        builtins.open = g_open
        socket.create_connection = g_cc
        subprocess.Popen = g_popen
        return self

    def __exit__(self, *exc):
        builtins.open = self._orig["open"]
        self._orig["socket_mod"].create_connection = self._orig["create_connection"]
        self._orig["subprocess_mod"].Popen = self._orig["Popen"]
        return False


def dry_run(entry, *args, **kwargs):
    """Run `entry(*args, **kwargs)` with effects recorded. -> list of (kind, mode, target)."""
    rec = Recorder()
    with rec:
        entry(*args, **kwargs)
    return rec.effects
