#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App membrane — run a program CONFINED to its .bio (deny-by-default effects). (F8)

This is the app-side counterpart of the Warden (which guards the coding *agent*). Here we
contain a *running program* — including one an AI wrote — so it can only produce the effects
its constitution grants.

Two backends, chosen by target and OS (see cli.py `metaspace run`):
  * Python target, ANY OS  -> `run_python`: an in-process membrane. WRITES / NETWORK / SUBPROCESS
    are checked against the .bio (deny-by-default) via core.guard.Guard; declared effects hit the
    REAL resource, undeclared ones raise and are blocked. READS pass through (MVP scope: confine
    effects, not reads — mirrors the Landlock enforcer).
  * Native binary, Linux    -> products/app_membrane/sandbox_enforcer.py: kernel-enforced
    (Landlock) write confinement of any program. Hard boundary.

HONEST SCOPE: the Python backend is a *language-level* membrane — usable and cross-OS, and a
real deny-by-default gate for ordinary and AI-written programs, but bypassable by adversarial
native code that rebinds builtins. For a hard boundary against untrusted binaries use the
Landlock backend (Linux). This is stated the same way in core/guard.py.
"""

import io
import os
import socket
import builtins
import contextlib
import subprocess


def run_python(bio_text, base_dir, pyfile, audit_path=False):
    """Execute a Python file under the in-process app membrane defined by bio_text.

    Returns (decisions, stdout, error, blocked): `decisions` is the guard's ALLOW/DENY log,
    `blocked` is the count of denied effects. Declared effects really happen; undeclared ones
    are blocked (the guard raises inside the program)."""
    import sys as _sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in _sys.path:
        _sys.path.insert(0, root)
    from core.guard import Guard, ConstitutionViolation

    # substitute the same placeholders the agent hook does, so a portable .bio confines correctly
    bio_text = bio_text.replace("{{PROJECT_ROOT}}", base_dir.replace("\\", "/"))
    claude_home = os.path.join(os.path.expanduser("~"), ".claude").replace("\\", "/")
    bio_text = bio_text.replace("{{CLAUDE_HOME}}", claude_home)

    guard = Guard(bio_text, base_dir, audit_path=audit_path)

    o_open, o_sock, o_cc, o_popen, o_system = (
        builtins.open, socket.socket, socket.create_connection, subprocess.Popen, os.system)

    with o_open(pyfile, encoding="utf-8") as fh:
        src = fh.read()

    def g_open(file, mode="r", *a, **k):
        if any(c in str(mode) for c in "wax+"):
            guard.check("FILESYSTEM", "write", str(file))   # raises if denied
        # reads pass through (MVP scope)
        return o_open(file, mode, *a, **k)

    def g_sock(*a, **k):
        guard.check("NETWORK", "out", "socket()")
        return o_sock(*a, **k)

    def g_cc(address, *a, **k):
        guard.check("NETWORK", "out", str(address))
        return o_cc(address, *a, **k)

    def g_popen(args, *a, **k):
        guard.check("SUBPROCESS", "exec", str(args))
        return o_popen(args, *a, **k)

    def g_system(cmd):
        guard.check("SUBPROCESS", "exec", str(cmd))
        return o_system(cmd)

    builtins.open = g_open
    socket.socket = g_sock
    socket.create_connection = g_cc
    subprocess.Popen = g_popen
    os.system = g_system
    out, err = io.StringIO(), None
    cwd0 = os.getcwd()
    try:
        # run the program in its own root so its relative paths resolve the way the membrane
        # normalises them (guard checks relative targets against base_dir)
        if os.path.isdir(base_dir):
            os.chdir(base_dir)
        code = compile(src, pyfile, "exec")
        with contextlib.redirect_stdout(out):
            exec(code, {"__name__": "__main__", "__file__": pyfile})
    except ConstitutionViolation as e:
        err = "BLOCKED: %s" % str(e)[:160]
    except Exception as e:
        err = "%s: %s" % (type(e).__name__, str(e)[:140])
    finally:
        os.chdir(cwd0)
        builtins.open, socket.socket, socket.create_connection, subprocess.Popen, os.system = (
            o_open, o_sock, o_cc, o_popen, o_system)
    blocked = sum(1 for d in guard.decisions if d.get("decision") == "DENY")
    return guard.decisions, out.getvalue(), err, blocked
