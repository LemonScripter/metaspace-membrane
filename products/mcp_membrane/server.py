#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — generic MCP capability-broker (Product B, second harness).

A minimal MCP-compatible server (JSON-RPC 2.0 over stdio, newline-delimited: `initialize`,
`tools/list`, `tools/call`) that exposes *mediated effect tools* — every effect an agent
performs goes THROUGH the broker, which decides it with the SAME harness-independent core the
Claude Code hook uses (core.agent_adapter.decide -> core.guard), deny-by-default, against a
`.bio` constitution. An out-of-constitution effect is refused and NOT performed.

WHY THIS IS THE HARD VARIANT (honest condition, see DECISIONS I-23 / README):
  An MCP `check`-style tool the agent *may* call is only advisory. This broker is a *chokepoint*
  instead: it is hard ONLY IF the agent is deployed with its ambient authority removed, so the
  broker's tools are the agent's ONLY way to touch the filesystem / network. Given that, the
  guarantee equals the Claude Code hook's (harness-hook tier). The broker does not, and cannot,
  constrain effects the agent reaches through some *other* unmediated tool.

SCOPE (MVP, stated plainly):
  - FILESYSTEM effects are gated AND performed (real, hermetic): fs_write / fs_read.
  - NETWORK is gated (verdict returned); actually emitting egress is deferred (a one-liner) so
    the proof stays hermetic and never beacons. The deny-by-default block is fully real for both.

Config (environment):
  METASPACE_PROJECT_ROOT / CLAUDE_PROJECT_DIR  — project root (boundary + base_dir).
  METASPACE_MCP_BIO   — constitution (default: the shipped ai_membrane session.constitution.bio).
  METASPACE_SESSION_AUDIT — audit log (default: <project>/.metaspace/mcp_audit.jsonl).
"""

import os
import re
import sys
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))   # .../metaspace-membrane
sys.path.insert(0, REPO_ROOT)

PROJECT_ROOT = (os.environ.get("METASPACE_PROJECT_ROOT")
                or os.environ.get("CLAUDE_PROJECT_DIR")
                or os.getcwd()).replace("\\", "/")
BIO_PATH = os.environ.get(
    "METASPACE_MCP_BIO",
    os.path.join(REPO_ROOT, "products", "ai_membrane", "session.constitution.bio"))
AUDIT = os.environ.get("METASPACE_SESSION_AUDIT",
                       os.path.join(PROJECT_ROOT, ".metaspace", "mcp_audit.jsonl"))

SERVER_INFO = {"name": "metaspace-membrane", "version": "0.1.0"}
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "fs_write",
        "description": "Write a file. Mediated by the membrane: denied unless the path is inside "
                       "the constitution's writable scope.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "fs_read",
        "description": "Read a file. Mediated by the membrane against the constitution's read scope.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "net_fetch",
        "description": "Fetch a URL. Mediated by the membrane against the network host allowlist "
                       "(verdict only in this MVP; egress deferred).",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]


def audit(rec):
    rec["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    rec["harness"] = "mcp"
    try:
        d = os.path.dirname(AUDIT)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(AUDIT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def host_of(url):
    m = re.match(r"[a-zA-Z]+://([^/:]+)", url or "")
    return m.group(1) if m else (url or "")


def _make_guard():
    from core.guard import Guard
    with open(BIO_PATH, encoding="utf-8") as fh:
        bio = fh.read().replace("{{PROJECT_ROOT}}", PROJECT_ROOT)
    # the broker is the single audit authority -> the guard does not double-log (audit_path=False)
    return Guard(bio, base_dir=PROJECT_ROOT, audit_path=False, provenance="RATIFIED")


def call_tool(name, args, guard):
    """Run a mediated effect tool. Returns (is_error, text). Denied effects are NOT performed."""
    from core.agent_adapter import decide

    if name == "fs_write":
        path = args.get("path", "") or ""
        content = args.get("content", "") or ""
        ok, reason = decide("FILESYSTEM", "write", path, guard)
        audit({"decision": "ALLOW" if ok else "DENY", "kind": "FILESYSTEM", "mode": "write",
               "target": path, "reason": reason, "tool": name})
        if not ok:
            return True, f"[MEMBRANE BLOCK] fs_write refused: {reason}"
        try:
            d = os.path.dirname(path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            return False, f"wrote {len(content)} byte(s) to {path}"
        except Exception as e:
            return True, f"fs_write error after ALLOW: {e}"

    if name == "fs_read":
        path = args.get("path", "") or ""
        ok, reason = decide("FILESYSTEM", "read", path, guard)
        audit({"decision": "ALLOW" if ok else "DENY", "kind": "FILESYSTEM", "mode": "read",
               "target": path, "reason": reason, "tool": name})
        if not ok:
            return True, f"[MEMBRANE BLOCK] fs_read refused: {reason}"
        try:
            with open(path, encoding="utf-8") as fh:
                return False, fh.read()
        except Exception as e:
            return True, f"fs_read error after ALLOW: {e}"

    if name == "net_fetch":
        url = args.get("url", "") or ""
        host = host_of(url)
        ok, reason = decide("NETWORK", "out", host, guard)
        audit({"decision": "ALLOW" if ok else "DENY", "kind": "NETWORK", "mode": "out",
               "target": host, "reason": reason, "tool": name})
        if not ok:
            return True, f"[MEMBRANE BLOCK] net_fetch refused: {host} not in the allowlist"
        # MVP: egress deferred (verdict only) so proofs stay hermetic and never beacon.
        return False, f"ALLOWED: {host} is in the constitution's network allowlist (egress deferred)"

    return True, f"unknown tool: {name}"


def reply(mid, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
    sys.stdout.flush()


def reply_error(mid, code, message):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid,
                                 "error": {"code": code, "message": message}}) + "\n")
    sys.stdout.flush()


def main():
    guard = None
    try:
        guard = _make_guard()
    except Exception as e:
        # fail-closed: with no loadable constitution the broker cannot see requests -> deny all.
        sys.stderr.write(f"[MCP MEMBRANE] constitution load error ({e}) -> deny-all (fail-closed)\n")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        method = msg.get("method")
        mid = msg.get("id")

        if method == "initialize":
            reply(mid, {"protocolVersion": PROTOCOL_VERSION,
                        "serverInfo": SERVER_INFO,
                        "capabilities": {"tools": {}}})
        elif method == "tools/list":
            reply(mid, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params", {}) or {}
            name = params.get("name", "")
            args = params.get("arguments", {}) or {}
            if guard is None:
                audit({"decision": "DENY", "kind": "?", "target": name,
                       "reason": "no constitution (fail-closed)", "tool": name})
                reply(mid, {"content": [{"type": "text", "text":
                            "[MEMBRANE BLOCK] no constitution loaded -> deny-all (fail-closed)"}],
                            "isError": True})
            else:
                is_error, text = call_tool(name, args, guard)
                reply(mid, {"content": [{"type": "text", "text": text}], "isError": is_error})
        elif mid is not None:
            reply_error(mid, -32601, f"method not found: {method}")
        # notifications (no id) are ignored


if __name__ == "__main__":
    main()
