#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio — privacy-first analytics service (F6-2).

Counts, nothing more. Cookie-free, no IP stored, no user-agent stored, no per-event rows —
only aggregate counters in SQLite. So there is nothing personal to leak: the store literally
cannot answer "who", only "how many".

Endpoints (all JSON, permissive CORS so the landing page and the CLI can post):
  POST /a   landing beacon     body {"t":"visit"|"cta", "page":..., "lang":..., "name":...}
  POST /t   opt-in CLI signal  body {"action":...}          (sent only if the user opted in)
  GET  /stats                  -> {"totals":{...}, "today":{...}}  (+ a tiny HTML view)
  GET  /healthz                -> ok

Every stored token is sanitised to [a-z0-9_.-], lower-cased, length-capped — a hostile beacon
cannot inject arbitrary strings or blow up the store. Zero third-party deps (stdlib only).
"""

import os
import re
import json
import sqlite3
import datetime
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_SANI = re.compile(r"[^a-z0-9_.-]+")
_LOCK = threading.Lock()


def sanitize(s, default="_", maxlen=32):
    s = _SANI.sub("_", str(s or "").strip().lower())[:maxlen].strip("_")
    return s or default


def _db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS counts (key TEXT PRIMARY KEY, n INTEGER NOT NULL)")
    conn.commit()
    return conn


def bump(path, key, n=1):
    with _LOCK:
        conn = _db(path)
        try:
            conn.execute(
                "INSERT INTO counts(key, n) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET n = n + ?", (key, n, n))
            conn.commit()
        finally:
            conn.close()


def snapshot(path):
    conn = _db(path)
    try:
        rows = conn.execute("SELECT key, n FROM counts").fetchall()
    finally:
        conn.close()
    today = datetime.date.today().isoformat()
    totals, today_map = {}, {}
    for key, n in rows:
        # key = "YYYY-MM-DD|kind|detail"
        parts = key.split("|", 2)
        if len(parts) != 3:
            continue
        day, kind, detail = parts
        tk = kind + ":" + detail
        totals[tk] = totals.get(tk, 0) + n
        if day == today:
            today_map[tk] = today_map.get(tk, 0) + n
    return {"totals": totals, "today": today_map}


def _key(kind, detail):
    return "%s|%s|%s" % (datetime.date.today().isoformat(), sanitize(kind), sanitize(detail))


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "msbio-analytics"

        def log_message(self, *a):
            pass  # never log request lines (no IPs in logs either)

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _send(self, code, payload, ctype="application/json"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if n <= 0 or n > 4096:
                    return None
                return json.loads(self.rfile.read(n).decode("utf-8", "replace"))
            except Exception:
                return None

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_POST(self):
            data = self._read_json()
            if not isinstance(data, dict):
                return self._send(400, {"ok": False, "error": "bad-json"})
            if self.path.startswith("/a"):
                t = sanitize(data.get("t"), "visit")
                if t == "cta":
                    detail = "cta." + sanitize(data.get("name"), "unknown")
                else:
                    detail = "page." + sanitize(data.get("page"), "index") + "." + sanitize(data.get("lang"), "xx")
                bump(db_path, _key("web", detail))
                return self._send(200, {"ok": True})
            if self.path.startswith("/t"):
                bump(db_path, _key("cli", sanitize(data.get("action"), "unknown")))
                return self._send(200, {"ok": True})
            return self._send(404, {"ok": False, "error": "no-such-endpoint"})

        def do_GET(self):
            if self.path.startswith("/healthz"):
                return self._send(200, {"ok": True})
            path = self.path.split("?", 1)[0]
            if path in ("/", "") or path.startswith("/stats"):
                snap = snapshot(db_path)
                # the dashboard (root or /stats in a browser) is HTML; /stats with a JSON
                # Accept header (or an API client) gets JSON
                wants_json = path.startswith("/stats") and "text/html" not in (self.headers.get("Accept") or "")
                if wants_json:
                    return self._send(200, snap)
                return self._send(200, _html(snap).encode(), ctype="text/html; charset=utf-8")
            return self._send(404, {"ok": False, "error": "no-such-endpoint"})

    return Handler


def _html(snap):
    def rows(m):
        return "".join("<tr><td>%s</td><td>%d</td></tr>" % (k, v)
                       for k, v in sorted(m.items(), key=lambda x: -x[1])) or "<tr><td>(none)</td><td>0</td></tr>"
    return ("<!doctype html><meta charset=utf-8><title>MetaSpace.Bio stats</title>"
            "<style>body{font:15px system-ui;max-width:640px;margin:40px auto;color:#111}"
            "table{border-collapse:collapse;width:100%%;margin:12px 0}td{border-bottom:1px solid #ddd;padding:6px}"
            "td:last-child{text-align:right;font-variant-numeric:tabular-nums}h2{margin-top:28px}</style>"
            "<h1>MetaSpace.Bio — usage</h1><p>Cookie-free, aggregate counts only.</p>"
            "<h2>Today</h2><table>%s</table><h2>All time</h2><table>%s</table>"
            % (rows(snap["today"]), rows(snap["totals"])))


def build(db_path, port=0, host="127.0.0.1"):
    return ThreadingHTTPServer((host, port), make_handler(db_path))


def main():
    port = int(os.environ.get("PORT", "8080"))
    db_path = os.environ.get("METASPACE_ANALYTICS_DB", "analytics.db")
    httpd = build(db_path, port=port, host="0.0.0.0")
    print("analytics on :%d db=%s" % (port, db_path), flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
