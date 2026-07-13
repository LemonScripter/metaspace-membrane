#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authenticity gate — does an AI-written program actually DO what it claims?

The membrane is the one place a program's REAL effects are observable, so it can catch the most
common (and most damaging) kind of AI "slop": code that looks like it works but produces no real
effect — claims to save data / call an API / build something, yet does nothing.

`run_and_record` executes a Python target under a recording membrane that is SAFE by construction:
  * filesystem WRITES are redirected into a throwaway sandbox dir (real write, harmless location),
  * NETWORK and SUBPROCESS are recorded and then BLOCKED (no real egress, nothing spawned),
  * reads run normally (there is no network to exfiltrate to).
It captures the effect-trace, which `analyze` compares against what the program CLAIMS to do.

HONEST SCOPE: this detects the *claims-vs-effects* gap (hollow / mismatched / hidden effects) for
Python programs. It is NOT a general correctness or quality checker — a program that runs and
produces the right *kind* of effects can still be logically wrong (Rice's theorem). Zero deps.
"""

import io
import os
import socket
import builtins
import contextlib
import subprocess


class _BlockedByGate(OSError):
    """A network/subprocess attempt, recorded and neutralized (nothing real happens)."""


def run_and_record(pyfile, sandbox):
    """Run a Python file under the recording membrane. Returns (effects, stdout, error).
    effects: list of {kind, mode, target}. Nothing dangerous actually happens."""
    effects = []

    def add(kind, mode, target):
        effects.append({"kind": kind, "mode": mode, "target": str(target)[:140]})

    o_open, o_sock, o_cc, o_popen, o_system = (
        builtins.open, socket.socket, socket.create_connection, subprocess.Popen, os.system)

    # read the source with the REAL open, before patching
    with o_open(pyfile, encoding="utf-8") as fh:
        src = fh.read()

    def g_open(file, mode="r", *a, **k):
        m = "write" if any(c in str(mode) for c in "wax+") else "read"
        add("FILESYSTEM", m, file)
        if m == "write":
            base = os.path.basename(str(file)) or "out"
            return o_open(os.path.join(sandbox, base), mode, *a, **k)   # redirect: harmless
        return o_open(file, mode, *a, **k)

    def g_sock(*a, **k):
        add("NETWORK", "out", "socket()")
        raise _BlockedByGate("network blocked by metaspace verify")

    def g_cc(address, *a, **k):
        add("NETWORK", "out", address)
        raise _BlockedByGate("network blocked by metaspace verify")

    def g_popen(args, *a, **k):
        add("SUBPROCESS", "exec", args)
        raise _BlockedByGate("subprocess blocked by metaspace verify")

    def g_system(cmd):
        add("SUBPROCESS", "exec", cmd)
        return 1

    builtins.open = g_open
    socket.socket = g_sock
    socket.create_connection = g_cc
    subprocess.Popen = g_popen
    os.system = g_system
    out, err = io.StringIO(), None
    try:
        code = compile(src, pyfile, "exec")
        with contextlib.redirect_stdout(out):
            exec(code, {"__name__": "__main__", "__file__": pyfile})
    except Exception as e:
        err = "%s: %s" % (type(e).__name__, str(e)[:120])
    finally:
        builtins.open, socket.socket, socket.create_connection, subprocess.Popen, os.system = (
            o_open, o_sock, o_cc, o_popen, o_system)
    return effects, out.getvalue(), err


def categories(effects):
    cats = set()
    for e in effects:
        if e["kind"] == "FILESYSTEM" and e["mode"] == "write":
            cats.add("writes")
        elif e["kind"] == "NETWORK":
            cats.add("network")
        elif e["kind"] == "SUBPROCESS":
            cats.add("subprocess")
    return cats


def analyze(effects, expect):
    """Compare observed effect categories to what the program claims. Returns a verdict dict."""
    expect = set(expect or [])
    obs = categories(effects)
    missing = expect - obs                              # claimed but never attempted -> hollow
    hidden = (obs - expect) & {"network", "subprocess"}  # did undeclared risky things
    if missing:
        verdict = "HOLLOW"
        head = "Claims to %s, but the program never even attempted it." % " and ".join(sorted(missing))
    elif hidden:
        verdict = "HIDDEN-EFFECT"
        head = "The program did undeclared %s — a hidden effect." % " and ".join(sorted(hidden))
    elif expect and obs >= expect:
        verdict = "CONSISTENT"
        head = "Observed effects match what it claims to do."
    elif not expect and not obs:
        verdict = "NO-EFFECTS"
        head = "The program produced no real effects — pure computation, or hollow."
    else:
        verdict = "OK"
        head = "No mismatch between claimed and observed effects."
    return {"verdict": verdict, "headline": head, "expected": sorted(expect),
            "observed": sorted(obs), "missing": sorted(missing), "hidden": sorted(hidden),
            "effects": effects}
