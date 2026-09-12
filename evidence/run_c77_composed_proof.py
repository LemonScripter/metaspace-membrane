#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — C-77 proof: `metaspace run --hard` composes the two membranes, and
refuses rather than degrading when the substrate is absent.

WHY COMPOSE AT ALL. The two backends are not a strength ordering, so replacing one with the
other is a trade, not a fix:

    FILESYSTEM write : language guard leaks (O-30)      · Landlock = HARD (C-75)
    NETWORK / SUBPROC: language guard = COOPERATIVE      · Landlock = nothing at all
    decision log     : language guard produces one       · Landlock produces none

`--hard` runs the interpreter under Landlock *and* the guard inside it, so a single run has a
kernel-enforced filesystem boundary and a mediated, logged NETWORK/SUBPROCESS surface.

TWO LEGS, one per platform — this proof asserts something everywhere rather than skipping:

  ON LINUX WITH LANDLOCK — the composition:
    * a granted write succeeds, in a scope directory that did NOT exist beforehand
      (the enforcer creates declared scopes instead of silently dropping them)
    * an out-of-scope write via `pathlib` is refused by the KERNEL (EACCES), the route that
      walks straight past the language guard
    * in the SAME run, `socket()` is refused by the guard and appears in the decision log
    * verified from outside: the denied file was never created

  EVERYWHERE ELSE — fail-closed:
    * `--hard` REFUSES (exit 3) and the program does not run at all; no output file appears.
      `--hard` is a requirement, not a request: silently dropping to a weaker tier is the one
      outcome a flag like this must never have.

Run:  python evidence/run_c77_composed_proof.py
"""

import os
import re
import sys
import json
import shutil
import tempfile
import platform
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
CLI = os.path.join(REPO_ROOT, "cli.py")

PROBE = r'''
import os, json, socket, pathlib
r = {}
try:
    with open(os.path.join("out", "ok.txt"), "w") as f:
        f.write("granted\n")
    r["granted"] = "WROTE"
except Exception as e:
    r["granted"] = "%s: %s" % (type(e).__name__, e)
try:
    pathlib.Path(os.environ["C77_SECRET"], "leak.txt").write_text("x")
    r["outside_pathlib"] = "WROTE"
except PermissionError as e:
    r["outside_pathlib"] = "DENIED:EACCES:%d" % e.errno
except OSError as e:
    r["outside_pathlib"] = "DENIED:%s" % type(e).__name__
try:
    socket.socket()
    r["network"] = "ALLOWED"
except Exception as e:
    r["network"] = "DENIED:%s" % type(e).__name__
print("C77_JSON=" + json.dumps(r))
'''


def _setup():
    proj = tempfile.mkdtemp(prefix="c77_proj_")
    secret = tempfile.mkdtemp(prefix="c77_secret_")
    bio = os.path.join(proj, "app.bio")
    with open(bio, "w", encoding="utf-8") as f:
        # grants writes under out/ and NOTHING else -- note that out/ is deliberately absent
        f.write('CELL App {\n  CAPABILITIES {\n'
                '    FILESYSTEM write "{{PROJECT_ROOT}}/out/**";\n'
                '  }\n}\n')
    probe = os.path.join(proj, "probe.py")
    with open(probe, "w", encoding="utf-8") as f:
        f.write(PROBE)
    return proj, secret, bio, probe


def main():
    proj, secret, bio, probe = _setup()
    env = dict(os.environ)
    env["C77_SECRET"] = secret
    p = subprocess.run([sys.executable, CLI, "run", "--hard", "--bio", bio,
                        "--root", proj, probe],
                       capture_output=True, text=True, env=env)
    out_file = os.path.join(proj, "out", "ok.txt")
    leak = os.path.join(secret, "leak.txt")
    m = re.search(r"C77_JSON=(\{.*\})", p.stdout or "")
    res = json.loads(m.group(1)) if m else {}

    linux_hard = "FILESYSTEM: HARD, kernel-enforced" in (p.stdout or "")

    print("=" * 74)
    print("  C-77 — `metaspace run --hard`: both membranes, or none at all")
    print("=" * 74)
    print("  platform     :", platform.system())
    print("  mode reached :", "COMPOSED" if linux_hard else "REFUSED (fail-closed)")
    print("  exit code    :", p.returncode)
    print("-" * 74)

    if linux_hard:
        checks = [
            ("composed banner names the kernel tier", linux_hard),
            ("composed banner names the cooperative tier",
             "NETWORK / SUBPROCESS: COOPERATIVE" in p.stdout),
            ("granted write succeeded", res.get("granted") == "WROTE"),
            ("the granted scope dir was CREATED, not dropped", os.path.exists(out_file)),
            ("out-of-scope pathlib write refused by the KERNEL",
             str(res.get("outside_pathlib", "")).startswith("DENIED:EACCES")),
            ("denied file never created (checked from outside)", not os.path.exists(leak)),
            ("network refused by the guard IN THE SAME RUN",
             str(res.get("network", "")).startswith("DENIED")),
            ("the decision log survived the composition",
             "BLOCKED  NETWORK/out" in p.stdout),
        ]
        verdict = ("PASS — one run, two boundaries: the kernel refused every out-of-scope write\n"
                   "          and the guard still mediated and logged the network effect.")
    else:
        checks = [
            ("refused with exit 3", p.returncode == 3),
            ("the refusal says REFUSED", "REFUSED" in (p.stderr or "")),
            ("it names what to do instead", "--hard" in (p.stderr or "")),
            ("the program did NOT run (no output file)", not os.path.exists(out_file)),
            ("the program produced no result at all", not res),
            ("nothing leaked outside the scope", not os.path.exists(leak)),
        ]
        verdict = ("PASS — the substrate was unavailable and --hard refused to run rather than\n"
                   "          quietly delivering a weaker tier than the flag promises.")

    ok = True
    for name, cond in checks:
        print("  [%s]  %s" % ("OK" if cond else "FAIL", name))
        ok = ok and bool(cond)
    print("-" * 74)
    if res:
        print("  probe:", res)
    if not linux_hard and p.stderr:
        print("  refusal:", (p.stderr.strip().splitlines() or [""])[0])
    print("=" * 74)
    print("  RESULT:", verdict if ok else "FAIL")
    if not ok:
        sys.stderr.write((p.stdout or "")[-1200:] + "\n" + (p.stderr or "")[-1200:] + "\n")
    for d in (proj, secret):
        shutil.rmtree(d, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
