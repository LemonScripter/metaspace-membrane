#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — MCP adapter-proof (M2): the same core on a second harness.

Proves that the generic MCP capability-broker and the Claude Code PreToolUse hook reach the
SAME allow/deny decision for the same effects — because both are thin adapters over one
harness-independent core (core.agent_adapter.decide -> core.guard). And it proves the broker
is a real chokepoint: a denied fs_write is refused AND the file is never created.

For each normalized effect we:
  - ask the HOOK (subprocess, PreToolUse JSON on stdin) -> exit 0 (ALLOW) / 2 (BLOCK)
  - ask the MCP BROKER (subprocess, JSON-RPC tools/call over stdio) -> result.isError
  - assert the two harnesses agree.

Nothing is mocked: both are the real programs, driven over their real interfaces.

Run:  python evidence/run_mcp_e2e.py     (exit 0 if the harnesses agree and the gate holds)
"""

import os
import sys
import json
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
HOOK = os.path.join(REPO_ROOT, "products", "ai_membrane", "session_guard_hook.py")
SERVER = os.path.join(REPO_ROOT, "products", "mcp_membrane", "server.py")

OUTSIDE_ABS = "C:/Windows/System32/evil.txt" if os.name == "nt" else "/etc/evil.txt"


def mcp_batch(env, calls):
    """Drive the MCP server over stdio with initialize + tools/list + N tools/call. Returns
    {id: response}. calls: list of (name, arguments)."""
    reqs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}]
    for i, (name, arguments) in enumerate(calls, start=2):
        reqs.append({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                     "params": {"name": name, "arguments": arguments}})
    stdin = "".join(json.dumps(r) + "\n" for r in reqs)
    p = subprocess.run([sys.executable, SERVER], input=stdin,
                       capture_output=True, text=True, env=env)
    out = {}
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except Exception:
            continue
        if "id" in m:
            out[m["id"]] = m
    return out, p


def hook_allows(env, event):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(event),
                       capture_output=True, text=True, env=env)
    return p.returncode == 0   # 0 ALLOW, 2 BLOCK


def main():
    proj = tempfile.mkdtemp(prefix="mcp_proj_").replace("\\", "/")
    os.makedirs(os.path.join(proj, "src"), exist_ok=True)
    with open(os.path.join(proj, "src", "main.py"), "w", encoding="utf-8") as f:
        f.write("print('hi')\n")

    hook_env = dict(os.environ)
    hook_env["CLAUDE_PROJECT_DIR"] = proj
    hook_env["METASPACE_SESSION_AUDIT"] = os.path.join(proj, ".metaspace", "hook_audit.jsonl")

    mcp_env = dict(os.environ)
    mcp_env["CLAUDE_PROJECT_DIR"] = proj
    mcp_audit = os.path.join(proj, ".metaspace", "mcp_audit.jsonl")
    mcp_env["METASPACE_SESSION_AUDIT"] = mcp_audit

    inside = proj + "/src/out.txt"
    main_py = proj + "/src/main.py"

    # (label, expect_allow, hook PreToolUse event, (mcp_tool, mcp_args))
    effects = [
        ("fs write inside the project", True,
         {"tool_name": "Write", "tool_input": {"file_path": inside}},
         ("fs_write", {"path": inside, "content": "hello"})),
        ("fs write OUTSIDE the project", False,
         {"tool_name": "Write", "tool_input": {"file_path": OUTSIDE_ABS}},
         ("fs_write", {"path": OUTSIDE_ABS, "content": "evil"})),
        ("fs read inside the project", True,
         {"tool_name": "Read", "tool_input": {"file_path": main_py}},
         ("fs_read", {"path": main_py})),
        ("net fetch allowed host", True,
         {"tool_name": "WebFetch", "tool_input": {"url": "https://docs.anthropic.com/x"}},
         ("net_fetch", {"url": "https://docs.anthropic.com/x"})),
        ("net fetch blocked host", False,
         {"tool_name": "WebFetch", "tool_input": {"url": "https://evil.example.com/s"}},
         ("net_fetch", {"url": "https://evil.example.com/s"})),
    ]

    # one MCP subprocess handles the whole batch (in order)
    mcp_calls = [mcp for (_, _, _, mcp) in effects]
    responses, sp = mcp_batch(mcp_env, mcp_calls)

    print("=" * 74)
    print("  MetaSpace MCP adapter-proof (M2) — same core, second harness")
    print("=" * 74)
    print("  project     :", proj)
    print("  broker      :", os.path.relpath(SERVER, REPO_ROOT))
    print("-" * 74)

    checks = []
    # protocol sanity
    init = responses.get(0, {}).get("result", {})
    checks.append(("MCP initialize returns serverInfo", init.get("serverInfo", {}).get("name") == "metaspace-membrane"))
    tools = responses.get(1, {}).get("result", {}).get("tools", [])
    tool_names = {t.get("name") for t in tools}
    checks.append(("tools/list advertises fs_write/fs_read/net_fetch",
                   {"fs_write", "fs_read", "net_fetch"} <= tool_names))

    print(f"  {'EFFECT':<34}{'WANT':>6}{'HOOK':>7}{'MCP':>6}  AGREE")
    print("-" * 74)
    agree_all = True
    for idx, (label, expect_allow, event, _mcp) in enumerate(effects):
        h_allow = hook_allows(hook_env, event)
        res = responses.get(idx + 2, {}).get("result", {})
        m_allow = (res.get("isError") is False)
        agree = (h_allow == m_allow == expect_allow)
        agree_all = agree_all and agree
        print(f"  {label:<34}{('ALLOW' if expect_allow else 'BLOCK'):>6}"
              f"{('ALLOW' if h_allow else 'BLOCK'):>7}{('ALLOW' if m_allow else 'BLOCK'):>6}"
              f"  {'OK' if agree else 'MISMATCH'}")
    checks.append(("hook and MCP broker agree on every effect", agree_all))

    print("-" * 74)
    # the gate is real: the allowed write happened, the denied write did NOT
    checks.append(("allowed fs_write was performed (file exists)", os.path.exists(inside)))
    checks.append(("denied fs_write was NOT performed (no file outside)", not os.path.exists(OUTSIDE_ABS)))
    # the broker logged a real audit
    checks.append(("broker wrote an MCP audit log", os.path.exists(mcp_audit)))

    for name, cond in checks:
        print("  [%s]  %s" % ("OK" if cond else "FAIL", name))
        agree_all = agree_all and bool(cond)

    print("=" * 74)
    if agree_all:
        print("  RESULT: PASS — one core, two harnesses (Claude Code hook + MCP broker) reach")
        print("          identical verdicts; the broker refuses and does not perform denied effects.")
        return 0
    print("  RESULT: FAIL")
    if sp.stderr:
        sys.stderr.write(sp.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
