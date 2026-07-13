#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-TELEMETRY — the opt-in usage signal is private by construction.

Asserts, with the real module in a temp HOME: default is OFF (record is a no-op, nothing is
even created); opt-in is anonymous (a random id, forgotten on opt-out); and no string a caller
passes (a path, filename, command) is ever written — only the fixed event name plus int/bool
counters. Falsifiable: weaken any of these and the proof fails.

Run: python run_telemetry_proof.py   (exit 0 iff every check passes)
"""

import os
import sys
import json
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

_ok = True
HOME = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
os.environ["HOME"] = HOME
os.environ["USERPROFILE"] = HOME


def check(cond, label):
    global _ok
    _ok = _ok and bool(cond)
    print("  [%s] %s" % ("ok" if cond else "FAIL", label))


def main():
    from core import telemetry
    events = os.path.join(HOME, ".claude", "metaspace", "telemetry_events.jsonl")

    print("=" * 72)
    print("  P-TELEMETRY (opt-in, anonymous, no PII, default off)")
    print("=" * 72)

    # 1) default OFF -> record is a pure no-op, nothing written
    check(telemetry.get_consent() is False, "consent defaults to OFF")
    check(telemetry.record("install", count=1) is False, "record() with consent OFF is a no-op")
    check(telemetry.record("install", path="/secret/thing") is False, "still a no-op even with a string field")
    check(not os.path.exists(events), "no events file is created while OFF")

    # 2) opt-in -> anonymous id
    s = telemetry.set_consent(True)
    check(telemetry.get_consent() is True, "opt-in enables consent")
    check(bool(s.get("id")) and len(s["id"]) >= 16, "an anonymous id is generated on opt-in")

    # 3) recording drops any string (PII), keeps only int/bool counters
    ok = telemetry.record("install", count=1, blocked=3, path="/home/user/secret.py",
                          command="rm something")
    check(ok is True, "record() writes when opted in")
    line = open(events, encoding="utf-8").read().strip()
    rec = json.loads(line.splitlines()[-1])
    check("/home/user/secret.py" not in line and "secret" not in line, "no path/PII string is stored")
    check("command" not in rec and rec.get("count") == 1 and rec.get("blocked") == 3,
          "only the event + int/bool counters are stored")
    check(rec.get("event") == "install" and rec.get("id") == s["id"], "event name + anonymous id present")

    # 4) unknown event names are rejected (no free-form strings become events)
    check(telemetry.record("exfiltrate_secrets") is False, "an event outside the fixed vocabulary is rejected")

    # 5) opt-out forgets the id and returns to no-op
    telemetry.set_consent(False)
    check(telemetry.state().get("id") is None, "opt-out forgets the anonymous id")
    check(telemetry.record("enforce", count=1) is False, "after opt-out, record is a no-op again")

    shutil.rmtree(HOME, ignore_errors=True)
    print("-" * 72)
    print("  RESULT:", "PASS — telemetry is off by default, anonymous when on, and never stores PII"
          if _ok else "FAIL — see checks above")
    print("=" * 72)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
