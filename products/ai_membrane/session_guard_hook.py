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
                            and used as the base_dir for scope matching. Falls back to
                            CLAUDE_PROJECT_DIR (set by Claude Code when run as a plugin),
                            then the current working directory.
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

PROJECT_ROOT = (os.environ.get("METASPACE_PROJECT_ROOT")
                or os.environ.get("CLAUDE_PROJECT_DIR")   # set by Claude Code (plugin/hook)
                or os.getcwd()).replace("\\", "/")
# the Claude config dir — substituted into the constitution so it can deny writes to its own
# config (self-protection), independent of where the project root happens to be.
CLAUDE_HOME = os.path.expanduser("~/.claude").replace("\\", "/")
BIO_PATH = os.environ.get("METASPACE_SESSION_BIO",
                          os.path.join(HERE, "session.constitution.bio"))
AUDIT = os.environ.get("METASPACE_SESSION_AUDIT",
                       os.path.join(PROJECT_ROOT, ".metaspace", "session_audit.jsonl"))

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read"}
NET_TOOLS = {"WebFetch"}


def audit(rec):
    rec["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        d = os.path.dirname(AUDIT)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(AUDIT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def allow(reason, **extra):
    rec = {"decision": "ALLOW", "reason": reason}
    rec.update(extra)
    audit(rec)
    sys.exit(0)


def deny(reason, **extra):
    rec = {"decision": "DENY", "reason": reason}
    rec.update(extra)
    audit(rec)
    sys.stderr.write(f"[MEMBRANE BLOCK] {reason}\n")
    sys.exit(2)


def parse_bash_denylist(bio_text):
    return re.findall(r'DENY\s+"([^"]*)"', bio_text)


def parse_bash_allowlist(bio_text):
    allow = []
    for stmt in re.findall(r'ALLOW\s+([^;]*);', bio_text, re.S):
        allow += re.findall(r'"([^"]*)"', stmt)
    return set(allow)


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
            bio = fh.read().replace("{{PROJECT_ROOT}}", PROJECT_ROOT).replace("{{CLAUDE_HOME}}", CLAUDE_HOME)
        from core.guard import Guard
        # the hook is the single audit authority (it logs with tool + kind + target); the guard
        # must not double-log to the same file -> audit_path=False (in-memory decisions only).
        guard = Guard(bio, base_dir=PROJECT_ROOT, audit_path=False, provenance="RATIFIED")
    except Exception as e:
        # cannot load the constitution -> the membrane is non-functional -> FAIL-CLOSED
        audit({"decision": "DENY", "reason": f"constitution load error ({e})", "fail": "closed"})
        sys.stderr.write(f"[MEMBRANE BLOCK] session-hook: constitution load error ({e}) "
                         f"-> deny-by-default (fail-closed)\n")
        sys.exit(2)

    # --- map the Claude Code tool event onto a normalized effect (kind, mode, target) ---
    if tool in WRITE_TOOLS:
        kind, mode, target = "FILESYSTEM", "write", (tin.get("file_path") or tin.get("notebook_path") or "")
    elif tool in READ_TOOLS:
        kind, mode, target = "FILESYSTEM", "read", (tin.get("file_path") or "")
    elif tool in NET_TOOLS:
        kind, mode, target = "NETWORK", "out", host_of(tin.get("url", ""))
    elif tool == "Bash":
        kind, mode, target = "SHELL", "exec", (tin.get("command", "") or "")
    else:
        sys.exit(0)   # any other tool: not our scope -> let the normal permission flow proceed

    # --- one shared, harness-independent decision (same core the MCP broker uses) ---
    from core.agent_adapter import decide
    allowset = parse_bash_allowlist(bio) if kind == "SHELL" else None
    denylist = parse_bash_denylist(bio) if kind == "SHELL" else None
    ok, reason = decide(kind, mode, target, guard, allowset, denylist)

    tgt = target[:80] if kind == "SHELL" else target
    if ok:
        allow(f"{tool} {kind}/{mode}: {str(target)[:60]}", tool=tool, kind=kind, mode=mode, target=tgt)
    else:
        deny(f"{tool} blocked ({kind}/{mode}): {reason}", tool=tool, kind=kind, mode=mode, target=tgt)


if __name__ == "__main__":
    main()
