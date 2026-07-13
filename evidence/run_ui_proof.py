#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-UI-API + P-UI-CSRF — the control panel really configures the membrane, and defends itself.

No mock: starts the REAL ui_server on a background thread in a temp HOME, drives it over real
HTTP, then drives the REAL hook against the project the UI just configured. Also asserts the
self-defence: no token -> 403, and a cross-origin POST (a malicious website) -> 403, so a web
page cannot reconfigure the membrane.

Run: python run_ui_proof.py   (exit 0 iff every check passes; cross-OS)
"""

import os
import sys
import json
import time
import shutil
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
HOOK = os.path.join(REPO, "products", "ai_membrane", "session_guard_hook.py")
DEFAULT_BIO = os.path.join(REPO, "products", "ai_membrane", "session.constitution.bio")

_ok = True
HOME = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
os.environ["HOME"] = HOME
os.environ["USERPROFILE"] = HOME


def check(cond, label):
    global _ok
    _ok = _ok and bool(cond)
    print("  [%s] %s" % ("ok" if cond else "FAIL", label))


def req(base, method, path, token=None, origin=None, body=None):
    headers = {}
    if token:
        headers["X-MS-Token"] = token
    if origin:
        headers["Origin"] = origin
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    r = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    for _ in range(20):
        try:
            resp = urllib.request.urlopen(r, timeout=5)
            return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except urllib.error.URLError:
            time.sleep(0.05)   # server thread not accepting yet — retry briefly
    return 0, ""


def drive_hook(project_root, command):
    env = dict(os.environ)
    env["METASPACE_PROJECT_ROOT"] = project_root
    env["METASPACE_SESSION_BIO"] = DEFAULT_BIO
    env["METASPACE_MODE"] = "enforce"
    env["METASPACE_SESSION_AUDIT"] = os.path.join(HOME, "audit.jsonl")
    ev = {"tool_name": "Bash", "tool_input": {"command": command}}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(ev),
                       capture_output=True, text=True, env=env)
    return p.returncode


def main():
    from products.ai_membrane import ui_server
    httpd, url, token = ui_server.make_server(0)
    port = httpd.server_address[1]
    base = "http://127.0.0.1:%d" % port
    good_origin = "http://127.0.0.1:%d" % port
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    print("=" * 74)
    print("  P-UI-API + P-UI-CSRF (real panel -> real hook; localhost self-defence)")
    print("=" * 74)

    # ---- self-defence (P-UI-CSRF) ----
    code, _ = req(base, "GET", "/")                                   # no token
    check(code == 403, "GET / without token -> 403")
    code, _ = req(base, "POST", "/api/project", body={"path": "/x"})  # no token
    check(code == 403, "POST /api/project without token -> 403")
    code, _ = req(base, "POST", "/api/project", token=token,
                  origin="http://evil.example", body={"path": "/x"})  # foreign origin
    check(code == 403, "cross-origin POST (a malicious website) -> 403")

    # ---- real configuration (P-UI-API) ----
    projX = os.path.join(HOME, "work", "projX").replace("\\", "/")
    os.makedirs(projX, exist_ok=True)
    code, out = req(base, "POST", "/api/project", token=token, origin=good_origin,
                    body={"path": projX, "label": "X", "mode": "enforce",
                          "fields": {"shell_allow": ["python", "ls", "echo"]}})
    check(code == 200 and json.loads(out).get("ok"), "authorized POST configures the project")

    code, out = req(base, "GET", "/api/projects", token=token)
    check(code == 200 and any(p["path"] == projX for p in json.loads(out)["projects"]),
          "GET /api/projects lists the configured project")

    # the configured constitution actually drives the real hook
    check(drive_hook(projX, "git status") == 2, "UI-configured project BLOCKS `git status` (not allowlisted)")
    check(drive_hook(projX, "python build.py") == 0, "UI-configured project ALLOWS `python build.py`")

    # ---- edit an existing project: fetch fields, widen the allowlist, confirm the hook reflects it ----
    code, out = req(base, "GET", "/api/project?path=" + urllib.parse.quote(projX), token=token)
    check(code == 200 and "python" in json.loads(out)["fields"].get("shell_allow", []),
          "GET /api/project returns the current fields (for editing)")
    req(base, "POST", "/api/project", token=token, origin=good_origin,
        body={"path": projX, "label": "X", "mode": "enforce",
              "fields": {"shell_allow": ["python", "git", "ls", "echo"]}})
    check(drive_hook(projX, "git status") == 0, "after editing the allowlist, `git status` is now ALLOWED")

    # ---- report endpoint returns a summary ----
    code, out = req(base, "GET", "/api/report?path=" + urllib.parse.quote(projX), token=token)
    rep = json.loads(out)
    check(code == 200 and all(k in rep for k in ("allow", "blocked", "would_block")),
          "GET /api/report returns an activity summary")

    # ---- telemetry: default off, togglable from the panel ----
    check(json.loads(req(base, "GET", "/api/telemetry", token=token)[1]).get("consent") is False,
          "telemetry consent defaults to OFF")
    req(base, "POST", "/api/telemetry", token=token, origin=good_origin, body={"consent": True})
    check(json.loads(req(base, "GET", "/api/telemetry", token=token)[1]).get("consent") is True,
          "telemetry consent can be toggled on from the panel")
    req(base, "POST", "/api/telemetry", token=token, origin=good_origin, body={"consent": False})

    code, html = req(base, "GET", "/?token=" + token)
    check(code == 200 and "MetaSpace Warden" in html, "the panel page loads with a valid token")

    # remove
    code, out = req(base, "DELETE", "/api/project", token=token, origin=good_origin, body={"path": projX})
    check(code == 200 and json.loads(out).get("ok"), "authorized DELETE removes the config")
    code, out = req(base, "GET", "/api/projects", token=token)
    check(not any(p["path"] == projX for p in json.loads(out)["projects"]), "project gone after delete")

    httpd.shutdown()
    httpd.server_close()
    shutil.rmtree(HOME, ignore_errors=True)
    print("-" * 74)
    print("  RESULT:", "PASS — the panel configures the real membrane and rejects unauthorized/cross-origin access"
          if _ok else "FAIL — see checks above")
    print("=" * 74)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
