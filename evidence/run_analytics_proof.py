#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-ANALYTICS — the analytics service counts, stays privacy-first, and can't be broken by a
hostile beacon (F6-2, I-43). No mock: a real server on 127.0.0.1, real HTTP round-trips.

  1. a visit / CTA / CLI beacon each increments the right aggregate counter
  2. counts accumulate (two visits -> 2)
  3. CORS works (POST carries Allow-Origin; OPTIONS preflight -> 204) so the landing can post
  4. a malformed body -> 400 and the server keeps serving (fail-soft, not fail-crash)
  5. PRIVACY: the store has exactly one table `counts(key,n)` — no ip / cookie / user-agent /
     per-event columns exist; there is nothing personal to leak
  6. a hostile beacon (SQL / script / 500-char junk) is sanitised to [a-z0-9_.-], length-capped
"""

import os
import sys
import json
import sqlite3
import tempfile
import shutil
import threading
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "analytics"))

import server as analytics


def _req(url, method="GET", body=None, accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Accept", accept)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(r, timeout=5)


def main():
    fails = []

    def check(cond, msg):
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            fails.append(msg)

    tmp = tempfile.mkdtemp(prefix="ms_an_")
    db = os.path.join(tmp, "a.db")
    httpd = analytics.build(db, port=0, host="127.0.0.1")
    port = httpd.server_address[1]
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    base = "http://127.0.0.1:%d" % port
    try:
        # 1. beacons
        _req(base + "/a", "POST", {"t": "visit", "page": "index", "lang": "en"})
        _req(base + "/a", "POST", {"t": "visit", "page": "index", "lang": "en"})   # 2nd
        _req(base + "/a", "POST", {"t": "cta", "name": "get-started"})
        _req(base + "/t", "POST", {"action": "install"})

        snap = json.loads(_req(base + "/stats").read())
        totals = snap["totals"]
        check(totals.get("web:page.index.en") == 2, "two visits counted (accumulate)")
        check(totals.get("web:cta.get-started") == 1, "a CTA click is counted")
        check(totals.get("cli:install") == 1, "an opt-in CLI action is counted")

        # 3. CORS
        resp = _req(base + "/a", "POST", {"t": "visit", "page": "index", "lang": "ro"})
        check(resp.headers.get("Access-Control-Allow-Origin") == "*", "POST carries CORS allow-origin")
        pre = _req(base + "/a", "OPTIONS")
        check(pre.status == 204 and pre.headers.get("Access-Control-Allow-Origin") == "*",
              "OPTIONS preflight -> 204 with CORS")

        # 4. malformed body -> 400, server survives
        bad_code = None
        try:
            req = urllib.request.Request(base + "/a", data=b"this-is-not-json", method="POST")
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            bad_code = e.code
        check(bad_code == 400, "a malformed body is rejected with 400")
        check(json.loads(_req(base + "/healthz").read()).get("ok") is True,
              "the server keeps serving after bad input (fail-soft)")

        # 5. privacy: schema is only counts(key,n)
        conn = sqlite3.connect(db)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        cols = [r[1] for r in conn.execute("PRAGMA table_info(counts)").fetchall()]
        conn.close()
        check(tables == ["counts"], "exactly one table exists: counts (no per-event/PII tables)")
        check(set(cols) == {"key", "n"}, "counts has only (key, n) — no ip/cookie/user-agent column")

        # 6. hostile beacon sanitised
        _req(base + "/a", "POST", {"t": "cta", "name": "DROP TABLE counts; <script>x</script>"})
        _req(base + "/a", "POST", {"t": "cta", "name": "Z" * 500})
        conn = sqlite3.connect(db)
        keys = [r[0] for r in conn.execute("SELECT key FROM counts").fetchall()]
        conn.close()
        import re
        detail_ok = all(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\|[a-z0-9_.-]+\|[a-z0-9_.-]+", k)
                        for k in keys)
        longest = max(len(k.split("|", 2)[2]) for k in keys)
        check(detail_ok, "every stored key is sanitised to [a-z0-9_.-] (no SQL/script injection)")
        check(longest <= 40, "hostile 500-char name is length-capped (<=40, got %d)" % longest)
        # the table still exists and is intact after the "DROP TABLE" beacon
        conn = sqlite3.connect(db)
        still = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        check(still == ["counts"], "the 'DROP TABLE' beacon did nothing — table intact")
    finally:
        httpd.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    print("-" * 60)
    if fails:
        print("RESULT: FAIL —", len(fails), "check(s) failed")
        return 1
    print("RESULT: PASS — analytics counts, stays cookie-free/aggregate-only, and resists hostile input")
    return 0


if __name__ == "__main__":
    sys.exit(main())
