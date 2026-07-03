#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — Agent (session) Guard Hook (PreToolUse)

Mediates the Claude Code agent's own tool calls against session.constitution.bio BEFORE
they run. The membrane sits in the harness (OUTSIDE the agent) — that is what makes the
"write only inside the project" rule hard: not self-discipline, the hook blocks.

Uses the same core.guard.Guard.check() decision engine as the app membrane (one source,
two places).

Input (stdin): PreToolUse JSON  {tool_name, tool_input, ...}
Block: exit code 2 + reason on stderr (returned to the model).
Allow: exit 0.

Configuration (environment):
  METASPACE_PROJECT_ROOT  — the project root; substituted for {{PROJECT_ROOT}} in the .bio
                            and used as the base_dir for scope matching (default: cwd).
  METASPACE_SESSION_BIO   — path to the constitution (default: sibling session.constitution.bio).

HONEST LIMITS:
  - Only affects TOOL effects (Write/Edit/Bash/WebFetch), NOT the model's prose/reasoning.
  - Bash command analysis is HEURISTIC (string patterns), not complete.

ERROR HANDLING (fail-closed):
  - Unreadable stdin OR unloadable constitution -> the membrane cannot SEE the request ->
    FAIL-CLOSED (exit 2, deny). A membrane that cannot see must not allow. If this stalls
    the session it is a LOUD signal (not a silent bypass), reversible by removing the hook.
"""

import os
import re
import sys
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))   # .../metaspace-membrane
sys.path.insert(0, REPO_ROOT)

PROJECT_ROOT = os.environ.get("METASPACE_PROJECT_ROOT", os.getcwd()).replace("\\", "/")
BIO_PATH = os.environ.get("METASPACE_SESSION_BIO",
                          os.path.join(HERE, "session.constitution.bio"))
AUDIT = os.environ.get("METASPACE_SESSION_AUDIT",
                       os.path.join(HERE, "session_audit.jsonl"))

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read"}
NET_TOOLS = {"WebFetch"}


def audit(rec):
    rec["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        with open(AUDIT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def allow(reason):
    audit({"decision": "ALLOW", "reason": reason})
    sys.exit(0)


def deny(reason):
    audit({"decision": "DENY", "reason": reason})
    sys.stderr.write(f"[MEMBRANE BLOCK] {reason}\n")
    sys.exit(2)


def parse_bash_denylist(bio_text):
    return re.findall(r'DENY\s+"([^"]*)"', bio_text)


def host_of(url):
    m = re.match(r"[a-zA-Z]+://([^/:]+)", url or "")
    return m.group(1) if m else (url or "")


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError("empty stdin")
        event = json.loads(raw)
    except Exception as e:
        # the membrane cannot SEE the request -> FAIL-CLOSED (deny)
        audit({"decision": "DENY", "reason": f"unreadable input ({e})", "fail": "closed"})
        sys.stderr.write(f"[MEMBRANE BLOCK] session-hook: unreadable input ({e}) "
                         f"-> deny-by-default (fail-closed)\n")
        sys.exit(2)

    tool = event.get("tool_name", "")
    tin = event.get("tool_input", {}) or {}

    try:
        with open(BIO_PATH, encoding="utf-8") as fh:
            bio = fh.read().replace("{{PROJECT_ROOT}}", PROJECT_ROOT)
        from core.guard import Guard, ConstitutionViolation
        guard = Guard(bio, base_dir=PROJECT_ROOT, audit_path=AUDIT, provenance="RATIFIED")
    except Exception as e:
        # cannot load the constitution -> the membrane is non-functional -> FAIL-CLOSED
        audit({"decision": "DENY", "reason": f"constitution load error ({e})", "fail": "closed"})
        sys.stderr.write(f"[MEMBRANE BLOCK] session-hook: constitution load error ({e}) "
                         f"-> deny-by-default (fail-closed)\n")
        sys.exit(2)

    # --- FILESYSTEM write (hard project boundary) ---
    if tool in WRITE_TOOLS:
        path = tin.get("file_path") or tin.get("notebook_path") or ""
        audit({"tool": tool, "kind": "FILESYSTEM", "mode": "write", "target": path})
        try:
            guard.check("FILESYSTEM", "write", path)
        except ConstitutionViolation as e:
            deny(str(e))
        allow(f"{tool} -> writable scope: {path}")

    # --- FILESYSTEM read ---
    if tool in READ_TOOLS:
        path = tin.get("file_path") or ""
        try:
            guard.check("FILESYSTEM", "read", path)
        except ConstitutionViolation as e:
            deny(str(e))
        allow(f"{tool} read: {path}")

    # --- NETWORK out (WebFetch) ---
    if tool in NET_TOOLS:
        host = host_of(tin.get("url", ""))
        audit({"tool": tool, "kind": "NETWORK", "mode": "out", "target": host})
        try:
            guard.check("NETWORK", "out", host)
        except ConstitutionViolation:
            deny(f"NETWORK/out host not allowed: {host}")
        allow(f"WebFetch host: {host}")

    # --- Bash (heuristic) ---
    if tool == "Bash":
        cmd = tin.get("command", "") or ""
        for pattern in parse_bash_denylist(bio):
            if pattern.lower() in cmd.lower():
                deny(f"Bash forbidden pattern: \"{pattern}\"  (command: {cmd[:80]})")
        audit({"tool": "Bash", "decision_pre": "no-deny-pattern", "cmd": cmd[:120]})
        allow(f"Bash (no forbidden pattern): {cmd[:60]}")

    # --- any other tool: not our scope -> let the normal permission flow proceed ---
    sys.exit(0)


if __name__ == "__main__":
    main()
