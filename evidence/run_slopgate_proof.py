#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-SLOPGATE — the authenticity gate really distinguishes a genuine program from AI "slop",
by observing effects rather than trusting output.

No mock: three REAL Python programs are written to disk and run under the recording membrane.
  * genuine — actually writes its output file  -> effects match the claim   -> CONSISTENT
  * slop    — prints "saved 1,000,000 rows!" but writes nothing -> hollow   -> HOLLOW
  * hidden  — writes its file AND phones home to an undeclared host          -> HIDDEN-EFFECT
The gate's verdict comes from the observed effect-trace, so a program cannot fake its way past it
by printing a success message. Nothing dangerous happens (writes go to a sandbox; network is
recorded and blocked). Cross-OS.

Run: python run_slopgate_proof.py   (exit 0 iff every verdict is correct)
"""

import os
import sys
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

_ok = True

GENUINE = (
    "with open('result.csv', 'w') as f:\n"
    "    f.write('a,b\\n1,2\\n')\n"
    "print('Saved result.csv')\n"
)
SLOP = (
    "print('Saved 1,000,000 rows to result.csv. Done!')\n"   # claims a write, does nothing
)
HIDDEN = (
    "with open('out.txt', 'w') as f:\n"
    "    f.write('ok')\n"
    "import socket\n"
    "try:\n"
    "    socket.create_connection(('telemetry.evil.example', 80), timeout=1)\n"
    "except Exception:\n"
    "    pass\n"
    "print('done')\n"
)
COMPUTE = (
    "print('sum =', sum(range(1000)))\n"                      # pure computation, claims nothing
)


def check(cond, label):
    global _ok
    _ok = _ok and bool(cond)
    print("  [%s] %s" % ("ok" if cond else "FAIL", label))


def verdict_of(src, expect):
    from core import verify
    d = tempfile.mkdtemp(prefix="ms_app_")
    box = tempfile.mkdtemp(prefix="ms_box_")
    try:
        p = os.path.join(d, "app.py")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(src)
        effects, _out, _err = verify.run_and_record(p, box)
        return verify.analyze(effects, expect)
    finally:
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(box, ignore_errors=True)


def main():
    print("=" * 74)
    print("  P-SLOPGATE (authenticity gate: real effects vs. claimed — genuine / slop / hidden)")
    print("=" * 74)

    g = verdict_of(GENUINE, ["writes"])
    check(g["verdict"] == "CONSISTENT", "genuine app (really writes) -> CONSISTENT")

    s = verdict_of(SLOP, ["writes"])
    check(s["verdict"] == "HOLLOW", "slop app (claims a save, writes nothing) -> HOLLOW")
    check("writes" in s["missing"], "  slop: the claimed 'writes' is flagged as never attempted")

    h = verdict_of(HIDDEN, ["writes"])
    check(h["verdict"] == "HIDDEN-EFFECT", "app that phones home to an undeclared host -> HIDDEN-EFFECT")
    check("network" in h["hidden"], "  hidden: the undeclared network effect is flagged")

    c = verdict_of(COMPUTE, [])
    check(c["verdict"] == "NO-EFFECTS", "pure-compute app claiming nothing -> NO-EFFECTS (not falsely hollow)")

    print("-" * 74)
    print("  RESULT:", "PASS — the gate tells a real program from slop by its effects, not its output"
          if _ok else "FAIL — see checks above")
    print("=" * 74)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
