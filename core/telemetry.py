#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Opt-in, privacy-first usage signal.

A security tool lives on trust, so telemetry here is deliberately minimal and honest:
  * DEFAULT OFF — nothing is recorded unless the user explicitly opts in;
  * ANONYMOUS — a random id generated only on opt-in, forgotten on opt-out; no account, no name;
  * NO PII, ever — only a fixed vocabulary of event names plus integer/boolean counters are
    stored; strings (which could carry a path, filename, command, or code) are dropped;
  * LOCAL-ONLY here — this scaffold appends to a local file; network delivery is a later phase
    and will stay opt-in;
  * NOT on the hot path — the enforcement hook records nothing; only coarse CLI actions do.

Proven by evidence/run_telemetry_proof.py (P-TELEMETRY).
"""

import os
import json
import uuid
import datetime

# fixed event vocabulary — no free-form strings are ever accepted as events
ALLOWED_EVENTS = {"install", "enforce", "dryrun", "off", "ui_open", "run", "verify", "license"}


def _endpoint():
    # opt-in network delivery: OFF unless the user sets this AND consent is on. No default URL.
    return os.environ.get("METASPACE_ANALYTICS_URL", "").strip()


def _deliver(event):
    """Best-effort, opt-in upload of ONLY the coarse event name (no id, no PII, no path).
    Fires only when consent is on and an endpoint is configured; never blocks or raises."""
    url = _endpoint()
    if not url or not get_consent():
        return
    import json as _json
    import threading
    import urllib.request

    def _post():
        try:
            data = _json.dumps({"action": event}).encode()
            req = urllib.request.Request(url.rstrip("/") + "/t", data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, timeout=2).read()
        except Exception:
            pass
    threading.Thread(target=_post, daemon=True).start()


def _dir():
    return os.path.join(os.path.expanduser("~"), ".claude", "metaspace")


def _consent_path():
    return os.path.join(_dir(), "telemetry.json")


def _events_path():
    return os.path.join(_dir(), "telemetry_events.jsonl")


def state():
    p = _consent_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {"consent": False, "id": None}


def get_consent():
    return bool(state().get("consent"))


def set_consent(on):
    s = state()
    s["consent"] = bool(on)
    if on and not s.get("id"):
        s["id"] = uuid.uuid4().hex          # anonymous, only ever created on opt-in
    if not on:
        s["id"] = None                      # forget the id on opt-out
    os.makedirs(_dir(), exist_ok=True)
    with open(_consent_path(), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2)
    return s


def record(event, **fields):
    """Record an anonymous event IFF the user opted in. Only the fixed event name plus
    integer/boolean counters are stored — never a string (no path, filename, command, or code).
    Returns True if a record was written, False otherwise (default: no-op)."""
    if event not in ALLOWED_EVENTS:
        return False
    s = state()
    if not s.get("consent"):
        return False                        # default OFF -> no-op
    # only int/bool counters survive; strings (which could carry PII) are dropped
    safe = {k: v for k, v in fields.items() if isinstance(v, (int, bool))}
    rec = {"ts": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
           "id": s.get("id"), "event": event}
    rec.update(safe)
    os.makedirs(_dir(), exist_ok=True)
    with open(_events_path(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    _deliver(event)          # opt-in, non-blocking; sends only the coarse event name
    return True
