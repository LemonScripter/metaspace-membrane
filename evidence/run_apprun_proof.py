#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-APPRUN — the app membrane really confines a running program to its .bio (F8, I-42).

No mock. We grant a program ONE writable directory and nothing else (no network, no
subprocess), run it under the membrane, and prove by real on-disk state that:

  Python backend (any OS):
    - a write INSIDE the granted dir actually happens (the real file exists with its bytes)
    - a write OUTSIDE it is blocked (the file never appears)
    - a network connection is blocked (deny-by-default)
    - a subprocess launch is blocked (deny-by-default)

  Landlock backend (Linux only; section runs only where Landlock is present, and its absence
  does NOT skip the whole proof — the cross-OS Python backend already proves confinement):
    - a native program's write outside the granted dir fails at the KERNEL (EACCES)
"""

import os
import sys
import tempfile
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from core import apprun

APP = r'''
import os, socket, subprocess
BASE = %(base)r
ALLOWED = %(allowed)r
# 1. allowed write -> should succeed
try:
    with open(os.path.join(ALLOWED, "ok.txt"), "w") as f:
        f.write("real work")
    print("wrote ok.txt")
except Exception as e:
    print("allowed write FAILED:", e)
# 1b. RELATIVE allowed write (resolves under root after chdir) -> should succeed
try:
    with open(os.path.join("workspace", "rel.txt"), "w") as f:
        f.write("relative real")
    print("wrote rel.txt")
except Exception as e:
    print("relative allowed write FAILED:", e)
# 2. out-of-scope write -> should be blocked
try:
    with open(os.path.join(BASE, "evil.txt"), "w") as f:
        f.write("should not exist")
    print("wrote evil.txt (BAD)")
except Exception as e:
    print("evil write blocked")
# 3. network -> should be blocked
try:
    socket.create_connection(("example.com", 80), timeout=1)
    print("connected (BAD)")
except Exception as e:
    print("network blocked")
# 4. subprocess -> should be blocked
try:
    subprocess.Popen(["echo", "hi"])
    print("spawned (BAD)")
except Exception as e:
    print("subprocess blocked")
'''


def main():
    fails = []

    def check(cond, msg):
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            fails.append(msg)

    base = tempfile.mkdtemp(prefix="ms_apprun_")
    try:
        allowed = os.path.join(base, "workspace")
        os.makedirs(allowed)
        # use the {{PROJECT_ROOT}} placeholder so this also proves apprun substitutes it
        bio = (
            "CELL App {\n"
            "  CAPABILITIES {\n"
            '    FILESYSTEM write "{{PROJECT_ROOT}}/workspace/**"\n'
            "  }\n"
            "}\n"
        )
        app_py = os.path.join(base, "app.py")
        with open(app_py, "w", encoding="utf-8") as f:
            f.write(APP % {"base": base, "allowed": allowed})

        decisions, out, err, blocked = apprun.run_python(bio, base, app_py)

        # real on-disk truth
        ok_exists = os.path.exists(os.path.join(allowed, "ok.txt"))
        evil_exists = os.path.exists(os.path.join(base, "evil.txt"))
        check(ok_exists, "granted write really happened (workspace/ok.txt exists on disk)")
        if ok_exists:
            with open(os.path.join(allowed, "ok.txt")) as f:
                check(f.read() == "real work", "the granted file has the program's real bytes")
        check(os.path.exists(os.path.join(allowed, "rel.txt")),
              "a RELATIVE granted write resolves under root and happens (chdir works)")
        check(not evil_exists, "out-of-scope write was blocked (evil.txt never created)")

        denied = [d for d in decisions if d["decision"] == "DENY"]
        kinds = {(d["kind"], d["mode"]) for d in denied}
        check(("FILESYSTEM", "write") in kinds, "the out-of-scope write is logged as DENY")
        check(("NETWORK", "out") in kinds, "network was denied (deny-by-default)")
        check(("SUBPROCESS", "exec") in kinds, "subprocess was denied (deny-by-default)")
        check(blocked >= 3, "at least 3 undeclared effects blocked (got %d)" % blocked)

        # --- Landlock backend (Linux only) ---
        try:
            sys.path.insert(0, os.path.join(ROOT, "products", "app_membrane"))
            import sandbox_enforcer
            have_landlock = sandbox_enforcer.landlock_abi() >= 1
        except Exception:
            have_landlock = False

        if have_landlock:
            enforcer = os.path.join(ROOT, "products", "app_membrane", "sandbox_enforcer.py")
            outside = os.path.join(base, "outside_kernel.txt")
            inside = os.path.join(allowed, "kernel_ok.txt")
            script = "echo hi > %s ; echo x > %s ; true" % (inside, outside)
            r = subprocess.run([sys.executable, enforcer, "--write", allowed,
                                "--", "/bin/sh", "-c", script],
                               capture_output=True, text=True)
            check(os.path.exists(inside),
                  "[Landlock] granted native write happened (kernel_ok.txt exists)")
            check(not os.path.exists(outside),
                  "[Landlock] native write outside the grant blocked at the kernel (EACCES)")
        else:
            print("  note: Landlock section not run here (needs Linux); Python backend proved confinement")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print("-" * 60)
    if fails:
        print("RESULT: FAIL —", len(fails), "check(s) failed")
        return 1
    print("RESULT: PASS — a running program is confined to its .bio (granted effects real, the rest blocked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
