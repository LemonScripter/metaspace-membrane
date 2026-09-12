#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — C-75 proof: ANY Linux process, in ANY language, is FILESYSTEM-write-
confined to its `.bio` — including a *Python* program, because the interpreter is launched
as the confined program rather than asked to cooperate.

WHAT MAKES THIS DIFFERENT FROM C-04 (`run_landlock_demo`). C-04 proves the mechanism with a
single `builtins.open` write. C-75 must answer the measurement that defeated the language-level
membrane (O-30): `io.open`, `pathlib.Path.write_text`, `os.open` + `os.write` and `os.rename`
are independent syscall wrappers, and four of eight probes wrote outside the constitution with
no adversarial code at all. This proof drives EXACTLY those routes at the substrate.

TWO LEGS, because a green result is only evidence if the instrument can go red:

  LEG A (the claim)    — the same probe under `sandbox_enforcer.py` (Landlock).
                         Expect: every out-of-scope route refused by the KERNEL (EACCES),
                         a granted write succeeding (positive control), and a subprocess's
                         out-of-scope write also refused (Landlock is inherited across
                         fork/exec — this is the structural closure, not a longer patch list).

  LEG B (the control)  — the identical probe under the language backend (`core.apprun`).
                         Expect: the O-30 routes SUCCEED in writing outside. This is the
                         differential: it shows the probe is capable of writing, so LEG A's
                         refusals are containment rather than a probe that never ran.
                         If LEG B also showed zero writes, LEG A would prove nothing.

⚠️ `PYTHONDONTWRITEBYTECODE=1` is set for the confined interpreter. `__pycache__` is a write
like any other and lands outside a typical scope; without this the run measures a false failure
(the program dies on import and every route reports "denied" for the wrong reason).

Linux + Landlock only. Elsewhere prints PROOF_SKIPPED and exits 0 — a skip, not a pass.

Run:  python evidence/run_c75_interpreter_proof.py
"""

import os
import re
import sys
import json
import tempfile
import platform
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
APP = os.path.join(REPO_ROOT, "products", "app_membrane")
ENFORCER = os.path.join(APP, "sandbox_enforcer.py")
sys.path.insert(0, APP)
sys.path.insert(0, REPO_ROOT)


def _skip(reason):
    print("PROOF_SKIPPED:", reason)
    print("  (Landlock is a Linux kernel feature; this proof runs where the OS provides it.)")
    return 0


# The probe is a real FILE, not `-c`: C-75 is about running a program, and a file is what a
# user actually runs. Each route is attempted independently; a refusal on one must not stop
# the next, or a single early denial would masquerade as full containment.
PROBE = r'''
import os, io, sys, json, pathlib, subprocess

OUT    = os.environ["C75_OUT"]      # granted by the .bio
SECRET = os.environ["C75_SECRET"]   # outside every scope
r = {}

def attempt(name, fn):
    try:
        fn()
        r[name] = "WROTE"
    except PermissionError as e:
        r[name] = "DENIED:EACCES:%d" % e.errno
    except OSError as e:
        r[name] = "DENIED:%s:%d" % (type(e).__name__, e.errno or 0)
    except Exception as e:
        r[name] = "ERROR:%s" % type(e).__name__

# --- positive control: the constitution GRANTS this one -----------------------
attempt("granted_write", lambda: open(os.path.join(OUT, "ok.txt"), "w").write("granted\n"))

# --- the four routes that defeated the language membrane (O-30) ---------------
attempt("builtins_open", lambda: open(os.path.join(SECRET, "a_builtins.txt"), "w").write("x"))
attempt("io_open",       lambda: io.open(os.path.join(SECRET, "b_io.txt"), "w").write("x"))
attempt("pathlib",       lambda: pathlib.Path(os.path.join(SECRET, "c_pathlib.txt")).write_text("x"))

def _os_open():
    fd = os.open(os.path.join(SECRET, "d_osopen.txt"), os.O_WRONLY | os.O_CREAT, 0o644)
    try:
        os.write(fd, b"x")
    finally:
        os.close(fd)
attempt("os_open_write", _os_open)

def _os_rename():
    src = os.path.join(OUT, "to_move.txt")
    with open(src, "w") as f:
        f.write("x")
    os.rename(src, os.path.join(SECRET, "e_renamed.txt"))
attempt("os_rename", _os_rename)

# --- the subprocess leg: Landlock is inherited across fork/exec ----------------
try:
    p = subprocess.run([sys.executable, "-c",
                        "open(%r,'w').write('x')" % os.path.join(SECRET, "f_child.txt")],
                       capture_output=True, text=True, timeout=30)
    r["child_write"] = "WROTE" if p.returncode == 0 else "DENIED:child_rc=%d" % p.returncode
    r["child_stderr_tail"] = (p.stderr or "").strip().splitlines()[-1:] or [""]
except Exception as e:
    r["child_write"] = "ERROR:%s" % type(e).__name__

print("RESULT_JSON=" + json.dumps(r))
'''

# LEG B driver: runs the SAME probe file through the language-level backend, in its own
# process so the proof's own builtins are never monkeypatched.
LEGB_DRIVER = r'''
import os, sys, json
sys.path.insert(0, %(repo)r)
from core import apprun
bio = open(%(bio)r, encoding="utf-8").read()
decisions, out, err, blocked = apprun.run_python(bio, %(proj)r, %(probe)r)
sys.stdout.write(out)
print("LEGB_META=" + json.dumps({"blocked": blocked, "err": err}))
'''


def _routes(res):
    return [k for k in ("builtins_open", "io_open", "pathlib", "os_open_write", "os_rename")
            if k in res]


def main():
    if platform.system() != "Linux":
        return _skip("not Linux (%s)" % platform.system())
    import sandbox_enforcer
    abi = sandbox_enforcer.landlock_abi()
    if abi < 1:
        return _skip("Landlock LSM not available on this kernel")

    proj = tempfile.mkdtemp(prefix="c75_proj_")
    out = os.path.join(proj, "out")
    os.makedirs(out, exist_ok=True)
    secret = tempfile.mkdtemp(prefix="c75_secret_")

    bio = os.path.join(proj, "app.bio")
    with open(bio, "w", encoding="utf-8") as f:
        f.write('CELL App {\n  CAPABILITIES {\n'
                '    FILESYSTEM write "{{PROJECT_ROOT}}/out/**";\n'
                '  }\n}\n')

    probe = os.path.join(proj, "probe.py")
    with open(probe, "w", encoding="utf-8") as f:
        f.write(PROBE)

    env = dict(os.environ)
    env["C75_OUT"] = out
    env["C75_SECRET"] = secret
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    # ---------------- LEG A: the substrate -----------------------------------
    pa = subprocess.run([sys.executable, ENFORCER, "--bio", bio, "--root", proj,
                         "--", sys.executable, probe],
                        capture_output=True, text=True, env=env)
    ma = re.search(r"RESULT_JSON=(\{.*\})", pa.stdout)
    A = json.loads(ma.group(1)) if ma else {}

    # ---------------- LEG B: the language backend (differential control) ------
    drv = os.path.join(proj, "legb.py")
    with open(drv, "w", encoding="utf-8") as f:
        f.write(LEGB_DRIVER % {"repo": REPO_ROOT, "bio": bio, "proj": proj, "probe": probe})
    secret_b = tempfile.mkdtemp(prefix="c75_secretB_")
    envb = dict(env)
    envb["C75_SECRET"] = secret_b
    pb = subprocess.run([sys.executable, drv], capture_output=True, text=True, env=envb)
    mb = re.search(r"RESULT_JSON=(\{.*\})", pb.stdout)
    B = json.loads(mb.group(1)) if mb else {}

    # ---------------- report --------------------------------------------------
    print("=" * 74)
    print("  C-75 — any Linux process, any language, FILESYSTEM-write-confined by its .bio")
    print("=" * 74)
    print("  Landlock ABI :", abi)
    print("  granted (rw) :", out)
    print("  denied       :", secret)
    print("  enforcer     :", (pa.stderr.strip().splitlines() or ["<none>"])[-1])
    print("-" * 74)
    print("  %-16s %-26s %s" % ("route", "LEG A (substrate)", "LEG B (language backend)"))
    for k in ("granted_write",) + tuple(_routes(A) or _routes(B)) + ("child_write",):
        print("  %-16s %-26s %s" % (k, A.get(k, "-"), B.get(k, "-")))
    print("-" * 74)

    routes = _routes(A)
    denied_all = bool(routes) and all(str(A.get(k, "")).startswith("DENIED") for k in routes)
    leaked = [f for f in os.listdir(secret)] if os.path.isdir(secret) else ["<missing>"]
    b_wrote = [k for k in _routes(B) if B.get(k) == "WROTE"]

    checks = [
        ("enforcer applied Landlock (stderr names the ABI)", "Landlock ABI" in pa.stderr),
        ("probe ran under the substrate (produced a result)", bool(A)),
        ("positive control: the GRANTED write succeeded", A.get("granted_write") == "WROTE"),
        ("all five O-30 routes refused by the kernel", denied_all),
        ("subprocess leg: the child's out-of-scope write refused",
         str(A.get("child_write", "")).startswith("DENIED")),
        ("outside verification: nothing was created in the denied dir", leaked == []),
        ("CONTROL — the same probe DID write outside under the language backend",
         len(b_wrote) > 0),
    ]
    ok = True
    for name, cond in checks:
        print("  [%s]  %s" % ("OK" if cond else "FAIL", name))
        ok = ok and bool(cond)

    print("-" * 74)
    print("  leg A denied routes : %s" % ", ".join("%s=%s" % (k, A.get(k)) for k in routes))
    print("  leg B wrote outside : %s" % (", ".join(b_wrote) or "<none>"))
    if leaked:
        print("  files in denied dir : %s" % leaked)
    print("=" * 74)
    if ok:
        print("  RESULT: PASS — a Python program was confined by the KERNEL to its .bio write")
        print("          scope through every route that defeats the language-level membrane,")
        print("          and its subprocess inherited the confinement. The control leg shows")
        print("          the same probe writing outside when only the language backend is used.")
        return 0
    print("  RESULT: FAIL")
    for label, p in (("LEG A", pa), ("LEG B", pb)):
        if p.stderr.strip():
            sys.stderr.write("---- %s stderr ----\n%s\n" % (label, p.stderr.strip()[-1500:]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
