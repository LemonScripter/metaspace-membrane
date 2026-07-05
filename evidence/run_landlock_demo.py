#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — SandboxEnforcer proof (M3): a real program, OS-confined by its `.bio`.

Launches a stock `python` interpreter under the Landlock SandboxEnforcer with a constitution
that grants write to ONE directory. The program then proves the confinement from the inside:
it CAN create a file in the granted directory, and it CANNOT create one elsewhere — the write
is refused by the kernel (EACCES), not by the program's cooperation. We also confirm from the
outside that the denied file was never created.

This is Product A's OS-sandbox path (beside the WebAssembly substrate): the guarantee is the
kernel's, and it holds for ANY native binary, not just WASM-compiled ones.

Linux + Landlock only. On any other platform it prints PROOF_SKIPPED and exits 0 (a skip, not
a pass): an OS guarantee can only be verified where the OS provides it.

Run:  python evidence/run_landlock_demo.py
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


def _skip(reason):
    print("PROOF_SKIPPED:", reason)
    print("  (Landlock is a Linux kernel feature; this proof runs where the OS provides it.)")
    return 0


CHILD = r"""
import os, json
r = {}
out = os.environ["LL_OUT"]; secret = os.environ["LL_SECRET"]
try:
    with open(os.path.join(out, "ok.txt"), "w") as f: f.write("granted write\n")
    r["wrote_granted"] = True
except Exception as e:
    r["wrote_granted"] = False; r["grant_err"] = type(e).__name__ + ": " + str(e)
try:
    with open(os.path.join(secret, "evil.txt"), "w") as f: f.write("exfiltrate\n")
    r["blocked_denied"] = False
except PermissionError:
    r["blocked_denied"] = True
except Exception as e:
    r["blocked_denied"] = False; r["deny_err"] = type(e).__name__ + ": " + str(e)
print("RESULT_JSON=" + json.dumps(r))
"""


def main():
    if platform.system() != "Linux":
        return _skip("not Linux (%s)" % platform.system())
    import sandbox_enforcer
    abi = sandbox_enforcer.landlock_abi()
    if abi < 1:
        return _skip("Landlock LSM not available on this kernel")

    proj = tempfile.mkdtemp(prefix="landlock_proj_")
    out = os.path.join(proj, "out")
    os.makedirs(out, exist_ok=True)
    secret = tempfile.mkdtemp(prefix="landlock_secret_")   # a directory OUTSIDE the grant

    bio = os.path.join(proj, "app.bio")
    with open(bio, "w", encoding="utf-8") as f:
        f.write('CELL App {\n  CAPABILITIES {\n'
                '    FILESYSTEM write "{{PROJECT_ROOT}}/out/**";\n'
                '  }\n}\n')

    env = dict(os.environ)
    env["LL_OUT"] = out
    env["LL_SECRET"] = secret

    p = subprocess.run([sys.executable, ENFORCER, "--bio", bio, "--root", proj,
                        "--", sys.executable, "-c", CHILD],
                       capture_output=True, text=True, env=env)

    m = re.search(r"RESULT_JSON=(\{.*\})", p.stdout)
    res = json.loads(m.group(1)) if m else {}

    print("=" * 72)
    print("  MetaSpace SandboxEnforcer proof (M3) — a real program, OS-confined by .bio")
    print("=" * 72)
    print("  Landlock ABI :", abi)
    print("  granted (rw) :", out)
    print("  denied       :", secret)
    print("  enforcer     :", (p.stderr.strip().splitlines() or ["<none>"])[-1])
    print("-" * 72)

    checks = [
        ("enforcer applied Landlock (stderr)", "Landlock ABI" in p.stderr),
        ("program COULD write the granted dir", res.get("wrote_granted") is True),
        ("program was DENIED writing elsewhere (kernel EACCES)", res.get("blocked_denied") is True),
        ("granted file exists on disk", os.path.exists(os.path.join(out, "ok.txt"))),
        ("denied file was never created", not os.path.exists(os.path.join(secret, "evil.txt"))),
    ]
    ok = True
    for name, cond in checks:
        print("  [%s]  %s" % ("OK" if cond else "FAIL", name))
        ok = ok and bool(cond)
    if not ok and res:
        print("  ---- child result:", res)
    print("=" * 72)
    if ok:
        print("  RESULT: PASS — a stock native program was contained to its .bio write scope by")
        print("          the kernel; an out-of-constitution write was refused (EACCES).")
        return 0
    print("  RESULT: FAIL")
    if p.stderr:
        sys.stderr.write(p.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
