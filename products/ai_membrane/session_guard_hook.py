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
            bio = fh.read().replace("{{PROJECT_ROOT}}", PROJECT_ROOT)
        from core.guard import Guard, ConstitutionViolation
        # the hook is the single audit authority (it logs with tool + kind + target); the guard
        # must not double-log to the same file -> audit_path=False (in-memory decisions only).
        guard = Guard(bio, base_dir=PROJECT_ROOT, audit_path=False, provenance="RATIFIED")
    except Exception as e:
        # cannot load the constitution -> the membrane is non-functional -> FAIL-CLOSED
        audit({"decision": "DENY", "reason": f"constitution load error ({e})", "fail": "closed"})
        sys.stderr.write(f"[MEMBRANE BLOCK] session-hook: constitution load error ({e}) "
                         f"-> deny-by-default (fail-closed)\n")
        sys.exit(2)

    # --- FILESYSTEM write (hard project boundary) ---
    if tool in WRITE_TOOLS:
        path = tin.get("file_path") or tin.get("notebook_path") or ""
        try:
            guard.check("FILESYSTEM", "write", path)
        except ConstitutionViolation as e:
            deny(str(e), tool=tool, kind="FILESYSTEM", mode="write", target=path)
        allow(f"{tool} -> writable scope: {path}",
              tool=tool, kind="FILESYSTEM", mode="write", target=path)

    # --- FILESYSTEM read ---
    if tool in READ_TOOLS:
        path = tin.get("file_path") or ""
        try:
            guard.check("FILESYSTEM", "read", path)
        except ConstitutionViolation as e:
            deny(str(e), tool=tool, kind="FILESYSTEM", mode="read", target=path)
        allow(f"{tool} read: {path}",
              tool=tool, kind="FILESYSTEM", mode="read", target=path)

    # --- NETWORK out (WebFetch) ---
    if tool in NET_TOOLS:
        host = host_of(tin.get("url", ""))
        try:
            guard.check("NETWORK", "out", host)
        except ConstitutionViolation:
            deny(f"NETWORK/out host not allowed: {host}",
                 tool=tool, kind="NETWORK", mode="out", target=host)
        allow(f"WebFetch host: {host}",
              tool=tool, kind="NETWORK", mode="out", target=host)

    # --- Bash (STRUCTURAL: allowlist + token-based denylist, obfuscation-resistant) ---
    if tool == "Bash":
        cmd = tin.get("command", "") or ""
        from core.shell_policy import check as shell_check
        allowset = parse_bash_allowlist(bio)
        denylist = parse_bash_denylist(bio)
        ok, reason = shell_check(cmd, allow=allowset, deny=denylist)
        if not ok:
            deny(f"Bash blocked: {reason}  (command: {cmd[:80]})",
                 tool="Bash", kind="SHELL", mode="exec", target=cmd[:80])
        allow(f"Bash structural OK: {cmd[:60]}",
              tool="Bash", kind="SHELL", mode="exec", target=cmd[:80])

    # --- any other tool: not our scope -> let the normal permission flow proceed ---
    sys.exit(0)


if __name__ == "__main__":
    main()
