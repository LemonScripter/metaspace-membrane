#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Warden — control panel (localhost web UI).

Configure the membrane per working directory in a browser: pick a folder, set what the agent
may write / reach / run, choose Observe or Enforce. Writes per-project constitutions under
~/.claude/metaspace (self-protected). Zero third-party deps (stdlib http.server).

Security (this UI edits security-critical config, so it defends itself):
  * binds 127.0.0.1 only — never a public interface;
  * a random per-launch TOKEN gates EVERY request (page + API); no token -> 403;
  * state-changing requests (POST/DELETE) must be same-origin localhost (Host + Origin checks),
    so a malicious website cannot drive the panel even if it guessed the port.
Proven by evidence/run_ui_proof.py (P-UI-API + P-UI-CSRF).
"""

import os
import re
import sys
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _page(token):
    return PAGE_HTML.replace("__TOKEN__", token)


def _report_summary(project):
    """Summarize a project's session audit (what the membrane allowed / blocked / would-block).
    Runs against the project-local `.metaspace/session_audit.jsonl` the hook writes."""
    audit = os.path.join(project, ".metaspace", "session_audit.jsonl")
    allow = blocked = would = 0
    examples = []
    if project and os.path.exists(audit):
        try:
            with open(audit, encoding="utf-8") as fh:
                for ln in fh:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        r = json.loads(ln)
                    except Exception:
                        continue
                    if r.get("would_block"):
                        would += 1
                        examples.append({"type": "would", "kind": r.get("kind"),
                                         "target": str(r.get("target"))[:80]})
                    elif r.get("decision") == "DENY":
                        blocked += 1
                        examples.append({"type": "blocked", "kind": r.get("kind"),
                                         "target": str(r.get("target"))[:80]})
                    elif r.get("decision") == "ALLOW":
                        allow += 1
        except Exception:
            pass
    return {"allow": allow, "blocked": blocked, "would_block": would, "examples": examples[-8:]}


def make_handler(token, port):
    from core import project_config, bio_fields

    def origin_ok(headers):
        host = (headers.get("Host") or "").lower()
        if host not in ("127.0.0.1:%d" % port, "localhost:%d" % port):
            return False
        origin = headers.get("Origin")
        if origin and origin.lower() not in ("http://127.0.0.1:%d" % port,
                                              "http://localhost:%d" % port):
            return False
        return True

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _token_ok(self):
            m = re.search(r"[?&]token=([^&]+)", self.path)
            q = m.group(1) if m else None
            return secrets.compare_digest(q or self.headers.get("X-MS-Token", ""), token)

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj), "application/json; charset=utf-8")

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return {}

        # ---- GET: page + read-only API ----
        def do_GET(self):
            if not self._token_ok():
                return self._send(403, "forbidden: missing or bad token", "text/plain")
            path = self.path.split("?")[0]
            if path == "/":
                return self._send(200, _page(token), "text/html; charset=utf-8")
            if path == "/api/projects":
                return self._json(200, {"projects": project_config.list_projects()})
            if path == "/api/default":
                return self._json(200, {"fields": bio_fields.SAFE_DEFAULTS})
            if path == "/api/commands":
                from core import command_catalog
                return self._json(200, {"commands": command_catalog.catalog()})
            if path == "/api/project":
                m = re.search(r"[?&]path=([^&]+)", self.path)
                import urllib.parse
                p = urllib.parse.unquote(m.group(1)) if m else ""
                text = project_config.read_bio(p) or ""
                return self._json(200, {"path": p, "fields": bio_fields.fields_from_bio(text)})
            if path == "/api/report":
                import urllib.parse
                m = re.search(r"[?&]path=([^&]+)", self.path)
                p = urllib.parse.unquote(m.group(1)) if m else ""
                return self._json(200, _report_summary(p))
            if path == "/api/telemetry":
                from core import telemetry
                st = telemetry.state()
                return self._json(200, {"consent": bool(st.get("consent")), "has_id": bool(st.get("id"))})
            if path == "/api/license":
                from core import license as lic
                if not lic.available():
                    return self._json(200, {"available": False, "tier": "free"})
                cur = lic.current()
                return self._json(200, {"available": True, "tier": cur.get("tier", "free"),
                                        "email": cur.get("email"), "expires": cur.get("expires")})
            return self._send(404, "not found", "text/plain")

        # ---- POST: create/update ----
        def do_POST(self):
            if not self._token_ok():
                return self._send(403, "forbidden: missing or bad token", "text/plain")
            if not origin_ok(self.headers):
                return self._send(403, "forbidden: cross-origin", "text/plain")
            path = self.path.split("?")[0]
            b = self._body()
            if path == "/api/project":
                proj = (b.get("path") or "").strip()
                if not proj:
                    return self._json(400, {"error": "path required"})
                label = b.get("label") or os.path.basename(proj.rstrip("/\\")) or "project"
                mode = "enforce" if b.get("mode") == "enforce" else "dryrun"
                text = bio_fields.bio_from_fields(b.get("fields") or {}, cell=label)
                h = project_config.set_project(proj, text, mode=mode, label=label)
                return self._json(200, {"ok": True, "hash": h})
            if path == "/api/mode":
                ok = project_config.set_mode((b.get("path") or "").strip(),
                                             "enforce" if b.get("mode") == "enforce" else "dryrun")
                return self._json(200 if ok else 404, {"ok": ok})
            if path == "/api/telemetry":
                from core import telemetry
                telemetry.set_consent(bool(b.get("consent")))
                return self._json(200, {"ok": True, "consent": telemetry.get_consent()})
            if path == "/api/license":
                from core import license as lic
                if not lic.available():
                    return self._json(200, {"ok": False,
                                            "error": "Pro needs: pip install metaspace-membrane[pro]"})
                if b.get("remove"):
                    lic.remove_license()
                    return self._json(200, {"ok": True, "tier": "free"})
                p = lic.install_license((b.get("key") or "").strip())
                if not p:
                    return self._json(200, {"ok": False, "error": "Invalid or expired licence key"})
                return self._json(200, {"ok": True, "tier": p.get("tier"),
                                        "email": p.get("email"), "expires": p.get("expires")})
            if path == "/api/verify":
                import tempfile
                import shutil
                from core import verify as vf
                f = (b.get("file") or "").strip()
                if not f or not os.path.exists(f):
                    return self._json(400, {"error": "file not found"})
                sandbox = tempfile.mkdtemp(prefix="ms_verify_")
                try:
                    effects, out, err = vf.run_and_record(os.path.abspath(f), sandbox)
                finally:
                    shutil.rmtree(sandbox, ignore_errors=True)
                rep = vf.analyze(effects, b.get("expect") or [])
                return self._json(200, {"verdict": rep["verdict"], "headline": rep["headline"],
                                        "observed": rep["observed"], "error": err})
            if path == "/api/run":
                from core import apprun
                f = (b.get("file") or "").strip()
                proj = (b.get("path") or "").strip()
                if not f or not os.path.exists(f):
                    return self._json(400, {"error": "file not found"})
                if not f.endswith(".py"):
                    return self._json(400, {"error": "the panel runs Python files (.py) under the app membrane"})
                bio_text = project_config.read_bio(proj) if proj else None
                if not bio_text:
                    return self._json(400, {"error": "add this folder above first, then run"})
                decisions, out, err, blocked = apprun.run_python(
                    bio_text, proj, os.path.abspath(f))
                denied = [{"kind": d["kind"], "mode": d["mode"], "target": str(d.get("target"))[:80]}
                          for d in decisions if d["decision"] == "DENY"]
                allowed = sum(1 for d in decisions if d["decision"] == "ALLOW")
                return self._json(200, {"allowed": allowed, "blocked": len(denied),
                                        "denied": denied[:8], "error": err, "stdout": (out or "")[:400]})
            return self._send(404, "not found", "text/plain")

        # ---- DELETE: remove ----
        def do_DELETE(self):
            if not self._token_ok():
                return self._send(403, "forbidden: missing or bad token", "text/plain")
            if not origin_ok(self.headers):
                return self._send(403, "forbidden: cross-origin", "text/plain")
            if self.path.split("?")[0] == "/api/project":
                ok = project_config.remove_project((self._body().get("path") or "").strip())
                return self._json(200, {"ok": ok})
            return self._send(404, "not found", "text/plain")

    return Handler


def make_server(port=0):
    """Create the localhost server. Returns (httpd, url, token). port=0 picks a free port."""
    token = secrets.token_urlsafe(24)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(token, 0))
    actual = httpd.server_address[1]
    # rebuild the handler now that we know the real port (for Host checks)
    httpd.RequestHandlerClass = make_handler(token, actual)
    url = "http://127.0.0.1:%d/?token=%s" % (actual, token)
    return httpd, url, token


def serve(port=0, open_browser=True):
    httpd, url, _ = make_server(port)
    print("=" * 66)
    print("  MetaSpace Warden — control panel")
    print("=" * 66)
    print("  Open in your browser:")
    print("   ", url)
    print("  (localhost only; press Ctrl+C to stop)")
    print("=" * 66)
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


PAGE_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MetaSpace Warden</title>
<style>
:root{--bg:#0b1020;--card:#141b2e;--fg:#e8ecf5;--mut:#93a1bd;--line:#243049;--ok:#2ecc71;--warn:#3aa0ff;--danger:#ff5c6c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:28px 18px 60px}
h1{font-size:26px;margin:0 0 2px}.sub{color:var(--mut);margin:0 0 22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:12px 0}
.row{display:flex;justify-content:space-between;align-items:center;gap:12px}
.path{color:var(--mut);font-size:13px;word-break:break-all}
.badge{font-size:12px;padding:3px 9px;border-radius:999px;border:1px solid var(--line)}
.badge.enforce{color:var(--ok);border-color:var(--ok)}.badge.dryrun{color:var(--warn);border-color:var(--warn)}
button{background:#1e2942;color:var(--fg);border:1px solid var(--line);border-radius:9px;padding:8px 13px;cursor:pointer;font-size:14px}
button:hover{border-color:#3a4a6b}button.primary{background:var(--warn);border-color:var(--warn);color:#04122b;font-weight:600}
button.ghost{background:transparent}button.danger{color:var(--danger);border-color:var(--danger)}
label{display:block;color:var(--mut);font-size:13px;margin:12px 0 4px}
input[type=text]{width:100%;background:#0e1526;color:var(--fg);border:1px solid var(--line);border-radius:9px;padding:9px 11px;font-size:14px}
.hint{color:var(--mut);font-size:12px;margin-top:3px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.chip{background:#0e1526;border:1px solid var(--line);border-radius:999px;padding:3px 9px;font-size:12px;display:flex;gap:6px;align-items:center}
.chip b{cursor:pointer;color:var(--mut)}
.modes{display:flex;gap:8px;margin-top:6px}.modes label{display:flex;gap:6px;align-items:center;margin:0;color:var(--fg);cursor:pointer}
.hidden{display:none}pre{background:#0e1526;border:1px solid var(--line);border-radius:9px;padding:12px;overflow:auto;font-size:12px;color:#bcd}
.foot{color:var(--mut);font-size:12px;margin-top:20px}
</style></head><body><div class="wrap">
<h1>MetaSpace Warden</h1>
<p class="sub">A safety membrane for your AI coding agent. Configure it per working directory.</p>
<div id="list"></div>
<div style="margin:14px 0"><button class="primary" onclick="showForm()">➕ Add a working directory</button></div>
<div id="form" class="card hidden"></div>
<div id="tools" class="card"></div>
<div id="license" class="card"></div>
<div id="consent" class="card"></div>
<datalist id="cmdlist"></datalist>
<style>
dialog.modal2{border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--fg);max-width:580px;width:calc(100% - 40px);padding:16px 18px}
dialog.modal2::backdrop{background:rgba(4,8,14,.62)}
.m2head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.m2head b{font-size:15px}
.mx2{background:none;border:0;color:var(--mut);font-size:15px;cursor:pointer}
#cmdfilter{width:100%;background:#0e1526;color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:10px}
.cmdlist2{max-height:60vh;overflow:auto;display:flex;flex-direction:column}
.cmdrow{display:grid;grid-template-columns:96px 1fr;gap:10px;padding:8px 4px;border-bottom:1px solid var(--line);font-size:13px;align-items:baseline}
.cmdrow code{color:var(--warn);font-size:12.5px}.cmdrow span{color:var(--mut)}
.cmdinfo-link{font-size:12px;color:var(--warn);text-decoration:none;margin-left:8px}
.tglangs{display:flex;gap:6px;align-items:center}
.tglang{background:#0e1526;border:1px solid var(--line);color:var(--mut);border-radius:7px;padding:3px 9px;font-size:12px;cursor:pointer}
.tglang.active{color:#04122b;background:var(--warn);border-color:var(--warn);font-weight:600}
.tg-body h4{margin:15px 0 4px;font-size:14px}
.tg-body p{margin:4px 0;font-size:13px;color:var(--fg)}
.tg-body .tg-intro{color:var(--mut)}
.tg-body .tg-note{margin-top:14px;padding-top:10px;border-top:1px solid var(--line);color:var(--mut);font-size:12.5px}
.tg-body code{color:var(--warn);font-size:12px}.tg-body b{color:var(--fg)}
</style>
<dialog id="cmdinfo" class="modal2">
  <div class="m2head"><b>What can these commands do?</b><button class="mx2" onclick="document.getElementById('cmdinfo').close()" aria-label="Close">✕</button></div>
  <input id="cmdfilter" type="text" placeholder="filter commands…" oninput="renderCmdInfo(this.value)">
  <div id="cmdlist2" class="cmdlist2"></div>
</dialog>
<dialog id="toolsinfo" class="modal2">
  <div class="m2head"><b>How do these tools work?</b>
    <span style="margin-left:auto;display:flex;gap:8px;align-items:center">
      <span class="tglangs"><button id="tglang-en" class="tglang" onclick="setToolsLang('en')">EN</button><button id="tglang-hu" class="tglang" onclick="setToolsLang('hu')">HU</button><button id="tglang-ro" class="tglang" onclick="setToolsLang('ro')">RO</button></span>
      <button class="mx2" onclick="document.getElementById('toolsinfo').close()" aria-label="Close">✕</button>
    </span>
  </div>
  <div id="tg-body" class="tg-body"></div>
</dialog>
<p class="foot">Settings are stored under <code>~/.claude</code> — outside your projects, so a
prompt-injected agent cannot change or disable them. Restart Claude Code after changes.</p>
</div>
<script>
const TOKEN="__TOKEN__";
const H={'Content-Type':'application/json','X-MS-Token':TOKEN};
const api=(m,u,b)=>fetch(u+(u.includes('?')?'&':'?')+'token='+TOKEN,{method:m,headers:H,body:b?JSON.stringify(b):undefined}).then(r=>r.json());
let DEF={};let CMDS=[];
function chip(v,on){return `<span class="chip">${v}<b onclick="${on}('${v.replace(/'/g,"")}')">✕</b></span>`}
function renderChips(id,arr){document.getElementById(id).innerHTML=arr.map(v=>chip(v,'rm_'+id)).join('')}
function mkChipField(id,arr){window['arr_'+id]=arr.slice();window['rm_'+id]=v=>{window['arr_'+id]=window['arr_'+id].filter(x=>x!==v);renderChips(id,window['arr_'+id])};
 setTimeout(()=>renderChips(id,window['arr_'+id]),0);
 return `<div class="chips" id="${id}"></div><input type="text" placeholder="type and press Enter to add" onkeydown="if(event.key==='Enter'){event.preventDefault();var v=this.value.trim();if(v){window['arr_'+'${id}'].push(v);renderChips('${id}',window['arr_'+'${id}']);this.value=''}}">`}
function mkCmdField(id,arr){window['arr_'+id]=arr.slice();window['rm_'+id]=v=>{window['arr_'+id]=window['arr_'+id].filter(x=>x!==v);renderChips(id,window['arr_'+id])};
 setTimeout(()=>renderChips(id,window['arr_'+id]),0);
 return `<div class="chips" id="${id}"></div><input type="text" list="cmdlist" placeholder="type to search commands, Enter to add" onkeydown="if(event.key==='Enter'){event.preventDefault();var v=this.value.trim();if(v){window['arr_'+'${id}'].push(v);renderChips('${id}',window['arr_'+'${id}']);this.value=''}}"><a href="#" class="cmdinfo-link" onclick="event.preventDefault();openCmdInfo()">What can these do?</a>`}
function openCmdInfo(){renderCmdInfo('');var d=document.getElementById('cmdinfo');if(d.showModal)d.showModal();}
function renderCmdInfo(q){q=(q||'').toLowerCase();
 document.getElementById('cmdlist2').innerHTML=CMDS.filter(c=>c.name.indexOf(q)>=0||c.desc.toLowerCase().indexOf(q)>=0)
  .map(c=>`<div class="cmdrow"><code>${c.name}</code><span>${c.desc}</span></div>`).join('')||'<div class="hint">No matching command.</div>';}
const TOOLS_GUIDE={
 en:`<p class="tg-intro">Both tools <b>run</b> the program you point them at (they don't just scan it), so you give the <b>one file you'd start with <code>python</code></b> — its entry point. That single file covers the whole run, including the files it imports. Currently they work on <b>Python</b> programs.</p>
<h4>&#128269; Authenticity check — is a program real, or "slop"?</h4>
<p><b>What it's for:</b> to tell whether an AI-written program actually <i>does</i> what it claims, or just looks finished while doing nothing.</p>
<p><b>How to use it:</b> paste the path to the program's entry file (the <code>.py</code> you would run). It runs it inside a safe recording membrane — writes go to a throwaway sandbox, network and subprocess calls are blocked — and watches the <b>real effects</b>.</p>
<p><b>What you get:</b> <b>CONSISTENT</b> — it does what it claims · <b>HOLLOW</b> — claims an effect but never even attempts it · <b>HIDDEN-EFFECT</b> — does undeclared risky things (network/subprocess) · <b>NO-EFFECTS</b> — pure computation.</p>
<h4>&#128737;&#65039; Run under a membrane — it can only do what's allowed</h4>
<p><b>What it's for:</b> to lock a finished program (even one an AI wrote) to its own rules, deny-by-default — so it can only produce the effects its constitution grants.</p>
<p><b>How to use it:</b> paste the entry file <b>and</b> the folder that holds its rules (the working directory you added above). Writes, network and subprocess are checked against those rules: allowed ones really happen, everything else is blocked.</p>
<p><b>What you get:</b> a count — <code>allowed: N · blocked: M</code> — plus what was blocked.</p>
<div class="tg-note"><b>&#8505;&#65039; Good to know:</b> the authenticity check compares <i>claims vs. real effects</i>, not general correctness — a program can run and still be logically wrong. Reads never affect the verdict; only writes, network and subprocess do. Interactive/GUI scripts may need a headless run. For a hard boundary against untrusted <i>binaries</i> (not just Python), use the Landlock backend on Linux.</div>`,
 hu:`<p class="tg-intro">Mindkét eszköz <b>lefuttatja</b> a programot, amelyre rámutatsz (nem csak beolvassa), ezért <b>azt az egy fájlt add meg, amit <code>python</code>-nal indítanál</b> — a belépőpontot. Ez az egy fájl lefedi az egész futást, a benne importált fájlokat is. Jelenleg <b>Python</b>-programokon működnek.</p>
<h4>&#128269; Hitelesség-ellenőrzés — valódi a program, vagy csak „slop"?</h4>
<p><b>Mire jó:</b> megmondja, hogy egy MI-írta program tényleg <i>megteszi-e</i>, amit állít, vagy csak késznek látszik, miközben semmit sem csinál.</p>
<p><b>Hogyan használd:</b> írd be a program belépő fájljának útvonalát (a <code>.py</code>, amit indítanál). Egy biztonságos, rögzítő membrán alatt futtatja — az írások eldobható sandboxba mennek, a hálózat és az alfolyamat blokkolva —, és figyeli a <b>valós effekteket</b>.</p>
<p><b>Mit kapsz:</b> <b>CONSISTENT</b> — azt teszi, amit állít · <b>HOLLOW</b> — állít egy effektet, de meg sem próbálja · <b>HIDDEN-EFFECT</b> — nem-deklarált kockázatos dolgot tesz (hálózat/alfolyamat) · <b>NO-EFFECTS</b> — tiszta számítás.</p>
<h4>&#128737;&#65039; Futtatás membrán alatt — csak azt teheti, amit szabad</h4>
<p><b>Mire jó:</b> egy kész programot (akár MI-írtat) a saját szabályaihoz zár, deny-by-default — így csak azokat az effekteket keltheti, amelyeket az alkotmánya megenged.</p>
<p><b>Hogyan használd:</b> add meg a belépő fájlt <b>és</b> a mappát, amelyben a szabályai vannak (a fent hozzáadott munkakönyvtár). Az írást, hálózatot és alfolyamatot a szabályokhoz méri: az engedettek valóban megtörténnek, minden más blokkolva.</p>
<p><b>Mit kapsz:</b> egy számot — <code>allowed: N · blocked: M</code> — plusz azt, hogy mit blokkolt.</p>
<div class="tg-note"><b>&#8505;&#65039; Jó tudni:</b> a hitelesség-ellenőrzés az <i>állítást</i> veti össze a <i>valós effekttel</i>, nem az általános helyességet — egy program futhat úgy is, hogy logikailag hibás. Az olvasás sosem befolyásolja a verdiktet, csak az írás, a hálózat és az alfolyamat. Interaktív/GUI szkripthez headless futás kellhet. Nem megbízható <i>binárisok</i> (nem csak Python) kemény határához használd a Landlock backendet Linuxon.</div>`,
 ro:`<p class="tg-intro">Ambele instrumente <b>rulează</b> programul pe care îl indici (nu doar îl scanează), așa că introduci <b>fișierul pe care l-ai porni cu <code>python</code></b> — punctul de intrare. Acest singur fișier acoperă întreaga rulare, inclusiv fișierele pe care le importă. Momentan funcționează pe programe <b>Python</b>.</p>
<h4>&#128269; Verificarea autenticității — programul e real sau „slop"?</h4>
<p><b>La ce folosește:</b> îți spune dacă un program scris de AI chiar <i>face</i> ce pretinde, sau doar pare terminat fără să facă nimic.</p>
<p><b>Cum se folosește:</b> introdu calea către fișierul de intrare al programului (fișierul <code>.py</code> pe care l-ai rula). Îl rulează sub o membrană sigură de înregistrare — scrierile merg într-un sandbox temporar, rețeaua și subprocesele sunt blocate — și observă <b>efectele reale</b>.</p>
<p><b>Ce primești:</b> <b>CONSISTENT</b> — face ce pretinde · <b>HOLLOW</b> — pretinde un efect, dar nici măcar nu-l încearcă · <b>HIDDEN-EFFECT</b> — face lucruri riscante nedeclarate (rețea/subproces) · <b>NO-EFFECTS</b> — calcul pur.</p>
<h4>&#128737;&#65039; Rulare sub o membrană — poate face doar ce e permis</h4>
<p><b>La ce folosește:</b> blochează un program finalizat (chiar și unul scris de AI) la propriile reguli, deny-by-default — astfel poate produce doar efectele permise de constituția sa.</p>
<p><b>Cum se folosește:</b> introdu fișierul de intrare <b>și</b> folderul care conține regulile sale (directorul de lucru adăugat mai sus). Scrierile, rețeaua și subprocesele sunt verificate față de aceste reguli: cele permise chiar se întâmplă, restul sunt blocate.</p>
<p><b>Ce primești:</b> un număr — <code>allowed: N · blocked: M</code> — plus ce a fost blocat.</p>
<div class="tg-note"><b>&#8505;&#65039; Bine de știut:</b> verificarea autenticității compară <i>ce pretinde</i> cu <i>efectele reale</i>, nu corectitudinea generală — un program poate rula și totuși să fie greșit logic. Citirile nu afectează niciodată verdictul; doar scrierile, rețeaua și subprocesele. Scripturile interactive/GUI pot necesita rulare headless. Pentru o barieră dură împotriva <i>binarelor</i> nesigure (nu doar Python), folosește backendul Landlock pe Linux.</div>`};
function renderToolsInfo(l){if(!TOOLS_GUIDE[l])l='en';document.getElementById('tg-body').innerHTML=TOOLS_GUIDE[l];
 ['en','hu','ro'].forEach(x=>{var b=document.getElementById('tglang-'+x);if(b)b.className='tglang'+(x===l?' active':'')});}
function setToolsLang(l){try{localStorage.setItem('ms_lang',l)}catch(e){}renderToolsInfo(l)}
function openToolsInfo(){var l='en';try{l=localStorage.getItem('ms_lang')||'en'}catch(e){}renderToolsInfo(l);var d=document.getElementById('toolsinfo');if(d.showModal)d.showModal()}
function esc(s){return (s||'').replace(/'/g,"")}
async function load(){
 const d=await api('GET','/api/default');DEF=d.fields;
 const cc=await api('GET','/api/commands');CMDS=cc.commands||[];
 document.getElementById('cmdlist').innerHTML=CMDS.map(c=>`<option value="${c.name}">${c.desc.slice(0,64)}</option>`).join('');
 const t=await api('GET','/api/telemetry');
 const r=await api('GET','/api/projects');
 document.getElementById('list').innerHTML = (r.projects.length?'':'<div class="card"><b>No working directories yet.</b><div class="hint">Add the folder where you run Claude Code.</div></div>')+
  r.projects.map(p=>{const pe=esc(p.path);return `<div class="card"><div class="row"><div><b>${p.label}</b> <span class="badge ${p.mode}">${p.mode==='enforce'?'Enforcing':'Observing'}</span><div class="path">${p.path}</div></div>
   <div><button onclick="toggleMode('${pe}','${p.mode}')">${p.mode==='enforce'?'Observe':'Enforce'}</button>
   <button onclick="editProject('${pe}','${esc(p.label)}','${p.mode}')">Edit</button>
   <button onclick="showReport('${pe}')">Activity</button>
   <button class="danger ghost" onclick="del('${pe}')">Remove</button></div></div></div>`}).join('');
 document.getElementById('consent').innerHTML=`<label style="display:flex;gap:9px;align-items:center;cursor:pointer;color:var(--fg)"><input type="checkbox" ${t.consent?'checked':''} onchange="setConsent(this.checked)"> Share anonymous usage stats <span class="hint">— off by default; never any code, paths, or personal data</span></label>`;
 renderTools();
 await renderLicense();
}
function renderTools(){
 document.getElementById('tools').innerHTML=`<h3 style="margin:2px 0 8px">Tools <a href="#" class="cmdinfo-link" onclick="event.preventDefault();openToolsInfo()">&#9432; How do these work?</a></h3>
  <label>Authenticity check — is an AI-written program real, or "slop"?</label>
  <input type="text" id="vf" placeholder="C:/path/to/app.py">
  <div style="margin-top:8px"><button onclick="doVerify()">Check authenticity</button>
   <span id="vfres" class="hint"></span></div>
  <div class="hint" style="margin-top:4px">Runs the file under a safe recording membrane (writes → throwaway sandbox, network/subprocess blocked) and reports whether its real effects match what it claims.</div>
  <label style="margin-top:16px">Run a program under the app membrane (deny-by-default effects)</label>
  <input type="text" id="rnf" placeholder="C:/path/to/app.py">
  <input type="text" id="rnp" placeholder="folder with its rules — must be added above" style="margin-top:6px">
  <div style="margin-top:8px"><button onclick="doRun()">Run confined</button>
   <span id="rnres" class="hint"></span></div>`;
}
async function doVerify(){
 const f=document.getElementById('vf').value.trim();const el=document.getElementById('vfres');
 if(!f){el.textContent='enter a .py path';return}el.textContent='running…';
 const r=await api('POST','/api/verify',{file:f});
 el.innerHTML = r.error&&!r.verdict ? '⚠ '+r.error :
   `<b style="color:${r.verdict==='HOLLOW'||r.verdict==='HIDDEN-EFFECT'?'var(--danger)':'var(--ok)'}">${r.verdict}</b> — ${r.headline} `+(r.observed&&r.observed.length?'(observed: '+r.observed.join(', ')+')':'');
}
async function doRun(){
 const f=document.getElementById('rnf').value.trim();const p=document.getElementById('rnp').value.trim();
 const el=document.getElementById('rnres');if(!f){el.textContent='enter a .py path';return}el.textContent='running…';
 const r=await api('POST','/api/run',{file:f,path:p});
 if(r.error&&r.allowed===undefined){el.innerHTML='⚠ '+r.error;return}
 el.innerHTML=`allowed: <b>${r.allowed}</b> · blocked: <b style="color:var(--danger)">${r.blocked}</b>`+
  (r.denied&&r.denied.length?'<br><span class="hint">blocked: '+r.denied.map(d=>d.kind+'/'+d.mode+' '+(d.target||'')).join(' · ')+'</span>':'')+
  (r.error?'<br><span class="hint">'+r.error+'</span>':'');
}
async function renderLicense(){
 const L=await api('GET','/api/license');const el=document.getElementById('license');
 if(!L.available){el.innerHTML=`<div class="row"><div><b>Licence</b> <span class="badge">FREE</span><div class="hint">Every feature is free right now. Paid tiers need the crypto extra: <code>pip install metaspace-membrane[pro]</code></div></div></div>`;return}
 if(L.tier==='pro'){el.innerHTML=`<div class="row"><div><b>Licence</b> <span class="badge enforce">PRO</span><div class="hint">${L.email||''}${L.expires?' · expires '+L.expires:''}</div></div><button class="danger ghost" onclick="removeLicense()">Remove</button></div>`;return}
 el.innerHTML=`<div><b>Licence</b> <span class="badge">FREE</span> <span class="hint">— every feature is free right now; a key just records your tier</span></div>
  <label>Have a licence key?</label><input type="text" id="lkey" placeholder="paste your key">
  <div style="margin-top:8px"><button class="primary" onclick="activateLicense()">Activate</button> <span id="lres" class="hint"></span></div>`;
}
async function activateLicense(){
 const k=document.getElementById('lkey').value.trim();const el=document.getElementById('lres');
 if(!k){el.textContent='paste a key';return}
 const r=await api('POST','/api/license',{key:k});
 if(r.ok){el.textContent='activated';renderLicense();}else{el.textContent='⚠ '+(r.error||'invalid');}
}
async function removeLicense(){if(confirm('Remove the licence and return to free?')){await api('POST','/api/license',{remove:true});renderLicense();}}
async function setConsent(on){await api('POST','/api/telemetry',{consent:on})}
async function toggleMode(path,cur){await api('POST','/api/mode',{path,mode:cur==='enforce'?'dryrun':'enforce'});load()}
async function del(path){if(confirm('Remove the membrane config for this folder?')){await api('DELETE','/api/project',{path});load()}}
async function showReport(path){
 const r=await api('GET','/api/report?path='+encodeURIComponent(path));
 alert('Activity for this folder:\n\nAllowed: '+r.allow+'\nBlocked: '+r.blocked+'\nWould-block (observe): '+r.would_block+(r.examples.length?'\n\nRecent:\n'+r.examples.map(e=>' • ['+e.type+'] '+(e.kind||'')+' '+(e.target||'')).join('\n'):'\n\n(no activity yet — run a Claude Code session in this folder)'));
}
async function editProject(path,label,mode){
 const r=await api('GET','/api/project?path='+encodeURIComponent(path));
 showForm({path,label,mode,fields:r.fields});
}
function showForm(ex){
 ex=ex||{};const editing=!!ex.path;const F=ex.fields||DEF;
 const f=document.getElementById('form');f.classList.remove('hidden');
 f.innerHTML=`<h3 style="margin:2px 0 2px">${editing?'Edit':'New'} working directory</h3>
  <label>Folder path <span class="hint">— where you run Claude Code</span></label>
  <input type="text" id="path" placeholder="C:/Users/you/my-project" value="${esc(ex.path||'')}" ${editing?'readonly':''}>
  <label>Name (optional)</label><input type="text" id="label" placeholder="my-project" value="${esc(ex.label||'')}">
  <label>Mode</label>
   <div class="modes"><label><input type="radio" name="mode" value="dryrun" ${ex.mode==='enforce'?'':'checked'}> Observe (warn only, never blocks — good for the first session)</label></div>
   <div class="modes"><label><input type="radio" name="mode" value="enforce" ${ex.mode==='enforce'?'checked':''}> Enforce (block anything outside the rules)</label></div>
  <label>Where can the agent write?</label>
  <div class="modes"><label><input type="checkbox" id="wproj" checked> This project folder only (recommended)</label></div>
  <label>Which sites may it reach?</label>${mkChipField('net',F.network||[])}
  <label>Allowed commands</label>${mkCmdField('allow',F.shell_allow||[])}
  <label>Always-blocked command patterns</label>${mkChipField('deny',F.shell_deny||[])}
  <div style="margin-top:16px"><button class="primary" onclick="save()">Save</button>
   <button class="ghost" onclick="document.getElementById('form').classList.add('hidden')">Cancel</button></div>`;
}
async function save(){
 const path=document.getElementById('path').value.trim();if(!path){alert('Please enter the folder path');return}
 const fields={write:document.getElementById('wproj').checked?['{{PROJECT_ROOT}}/**']:['{{PROJECT_ROOT}}/**'],
  read:['**'],network:window.arr_net||[],shell_allow:window.arr_allow||[],shell_deny:window.arr_deny||[]};
 const mode=document.querySelector('input[name=mode]:checked').value;
 await api('POST','/api/project',{path,label:document.getElementById('label').value.trim(),mode,fields});
 document.getElementById('form').classList.add('hidden');load();
}
load();
</script></body></html>"""
