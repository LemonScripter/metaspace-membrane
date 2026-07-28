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
# enforcement mode: "dryrun" (observe: record + warn what WOULD be blocked, but allow it) or
# "enforce" (block). Fresh installs start in dryrun so the membrane never over-blocks on the
# first session; the user reviews, then runs `metaspace enforce`. Default enforce if unset.
# These are DEFAULTS; a per-project constitution/mode (if configured via the UI) overrides them.
def _user_defaults():
    """Mode + constitution from ~/.claude/metaspace/config.json (O-13 fallback).

    Not every host propagates the `env` block of settings.json — Cursor invokes this hook but
    passes no environment, which silently downgraded the user's configuration to the built-in
    defaults. Precedence, most specific first:
        1. the per-project registry entry (resolved later, in main)
        2. an explicit environment variable, when the host provides one (Claude Code)
        3. this user-level file on disk, which every host can read
        4. the built-in defaults
    """
    try:
        sys.path.insert(0, REPO_ROOT)
        from core.project_config import load_defaults
        return load_defaults()
    except Exception:
        return {}


_DEFAULTS = _user_defaults()
DEFAULT_MODE = (os.environ.get("METASPACE_MODE")
                or _DEFAULTS.get("mode")
                or "enforce").strip().lower()
DEFAULT_BIO = (os.environ.get("METASPACE_SESSION_BIO")
               or _DEFAULTS.get("bio")
               or os.path.join(HERE, "session.constitution.bio"))
AUDIT = os.environ.get("METASPACE_SESSION_AUDIT",
                       os.path.join(PROJECT_ROOT, ".metaspace", "session_audit.jsonl"))

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read"}
NET_TOOLS = {"WebFetch"}
# Every tool that hands a command line to a shell. `Bash` was alone here while a `PowerShell`
# tool sat beside it with the same capability on the same machine — a live call left no audit
# entry at all, because the membrane only ever knew the one name (O-34). Every shell protection
# in this project was one tool name away from irrelevant.
#
# HONEST LIMIT: `core/shell_policy.py` tokenises POSIX-style, and PowerShell is not POSIX — its
# backtick is an escape character, not command substitution, for instance. The mismatch runs
# towards over-blocking (a wrong split refuses), which is the safe direction, but this is
# mediation, not comprehension. The boundary on this host stays the FILESYSTEM write-scope and
# the NETWORK out-scope, as C-63 says for interpreters generally.
#
# And adding a name is a stopgap, not the fix: the membrane still decides only over the tools it
# is told about. The structural answer is O-33 — see the ledger before extending this set again.
SHELL_TOOLS = {"Bash", "PowerShell", "Shell", "Terminal", "run_shell_command", "shell_exec"}


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


def _emit(permission, reason=""):
    """Also answer in the JSON-on-stdout dialect.

    Claude Code takes the verdict from the EXIT CODE (2 = block). Cursor reads a JSON object on
    stdout with a `permission` field and ignores the exit code — verified empirically: this hook
    exited 2 for every Cursor tool call and the operations proceeded anyway.

    Emitting both is additive: Claude Code still sees exit 2, Cursor now sees the deny it was
    waiting for. Anything that understands neither is unaffected.
    """
    try:
        try:
            from core.hosts import verdict_payload
            out = verdict_payload(permission, reason)
        except Exception:
            out = {"permission": permission}
        sys.stdout.write(json.dumps(out))
        sys.stdout.flush()
    except Exception:
        pass          # the verdict must never depend on being able to write stdout


def allow(reason, **extra):
    rec = {"decision": "ALLOW", "reason": reason}
    rec.update(extra)
    audit(rec)
    _emit("allow")
    sys.exit(0)


def deny(reason, **extra):
    rec = {"decision": "DENY", "reason": reason}
    rec.update(extra)
    audit(rec)
    sys.stderr.write(f"[MEMBRANE BLOCK] {reason}\n")
    _emit("deny", reason)
    sys.exit(2)


# The BASH_POLICY parse used to be duplicated here, in core/bio_fields.py and in
# core/provenance.py. Three copies of `ALLOW\s+([^;]*);` meant three chances to get it wrong,
# and one of them was: a semicolon inside a comment emptied the allowlist, which silently
# disabled the allowlist AND the interpreter hardening (O-20). One parser now, imported.
from core.bio_policy import (                            # noqa: E402
    parse_bash_allowlist, parse_bash_denylist, declares_allow)


def host_of(url):
    m = re.match(r"[a-zA-Z]+://([^/:]+)", url or "")
    return m.group(1) if m else (url or "")


def main():
    try:
        # Read BYTES, not text, and strip a UTF-8 BOM if present. Cursor prefixes its hook
        # payload with EF BB BF; plain json.loads() rejects that, which made this hook
        # fail-closed on EVERY Cursor tool call (verified against a captured payload — see
        # evidence/fixtures/cursor_beforeShellExecution.json). A membrane that cannot parse its
        # host denies everything, which is safe but useless.
        data = sys.stdin.buffer.read()
        raw = data.decode("utf-8-sig") if isinstance(data, (bytes, bytearray)) else str(data)
        if not raw.strip():
            raise ValueError("empty stdin")
        event = json.loads(raw)
    except Exception as e:
        # the membrane cannot SEE the request -> FAIL-CLOSED (deny)
        audit({"decision": "DENY", "reason": f"unreadable input ({e})", "fail": "closed"})
        sys.stderr.write(f"[MEMBRANE BLOCK] session-hook: unreadable input ({e}) "
                         f"-> deny-by-default (fail-closed)\n")
        _emit("deny", f"unreadable input ({e})")
        sys.exit(2)

    # --- which host dialect is this? -------------------------------------------------------
    # Claude Code sends {tool_name, tool_input}. Cursor sends {hook_event_name, command|file_path}
    # even when the hook was registered through ~/.claude/settings.json, so the payload shape is
    # NOT implied by the config file it came from. Normalise both onto Claude's shape here; the
    # decision core below is unchanged. (Cursor's vocabulary was read out of its own shipped
    # hooks/types.js — see docs/AGENT_SURVEY.md.)
    # The per-host tables are DATA in core.hosts, not code here: three surveyed hosts differ only
    # in spelling (PreToolUse / preToolUse / BeforeTool; Bash / run_shell_command; Write /
    # write_file), never in meaning, so adding a host is a table entry.
    try:
        from core.hosts import HOST_EVENTS as CURSOR_EVENTS, canonical_tool
    except Exception:
        CURSOR_EVENTS, canonical_tool = {}, (lambda n: n)
    # Measured dialects (Cursor 3.12.17, 2026-07-21) — do not guess, these were observed:
    #   claude   : {tool_name, tool_input}                     — Claude Code
    #   native   : {hook_event_name: beforeShellExecution, …}  — Cursor's own hooks.json
    #   hybrid   : BOTH — Cursor's Claude-compat path sends hook_event_name "preToolUse"
    #              alongside Claude's tool_name/tool_input, plus cursor_version. It works
    #              through the Claude fields; the Cursor metadata is extra, not a substitute.
    #   unknown  : a host event we have no mapping for AND no Claude fields -> nothing to decide.
    host_event = event.get("hook_event_name", "")
    has_claude_fields = bool(event.get("tool_name"))
    if not host_event:
        dialect = "claude"
    elif has_claude_fields:
        dialect = "hybrid"
    elif host_event in CURSOR_EVENTS:
        dialect = "native"
        mapped_tool, field = CURSOR_EVENTS[host_event]
        value = event.get(field, "") or ""
        event = dict(event)
        event["tool_name"] = mapped_tool
        event["tool_input"] = ({"command": value} if mapped_tool == "Bash"
                               else {"file_path": value})
    else:
        dialect = "unknown"

    # Gemini sends Claude-shaped {tool_name, tool_input} but with ITS OWN tool names
    # (run_shell_command, write_file, replace, read_file). Alias them onto the canonical set so
    # the effect mapping below stays one table, not one per host.
    tool = canonical_tool(event.get("tool_name", ""))
    tin = event.get("tool_input", {}) or {}

    # resolve THIS project's constitution + mode (per-working-directory config, stored user-level
    # under ~/.claude); fall back to the install defaults. Never fatal.
    try:
        from core import project_config
        bio_path, enforce_mode = project_config.resolve(PROJECT_ROOT, DEFAULT_BIO, DEFAULT_MODE)
        bio_path = bio_path or DEFAULT_BIO
    except Exception:
        bio_path, enforce_mode = DEFAULT_BIO, DEFAULT_MODE

    try:
        with open(bio_path, encoding="utf-8") as fh:
            bio = fh.read().replace("{{PROJECT_ROOT}}", PROJECT_ROOT).replace("{{CLAUDE_HOME}}", CLAUDE_HOME)
        from core.guard import Guard
        # the hook is the single audit authority (it logs with tool + kind + target); the guard
        # must not double-log to the same file -> audit_path=False (in-memory decisions only).
        guard = Guard(bio, base_dir=PROJECT_ROOT, audit_path=False, provenance="RATIFIED")
        # Self-protection is enforced from CODE, not from the constitution's text (O-14).
        # The `.bio` still carries its own deny line for visibility, but the guarantee must not
        # depend on it: a constitution written before a host existed cannot name that host's
        # anchor, and a hand-edited one may have had the line deleted. Injecting the anchors here
        # protects old and edited constitutions alike. This only ever ADDS to the deny side, so a
        # wrong entry can over-block (loud) but never open a hole (silent).
        try:
            from core.agent_anchors import deny_scopes
            guard.allowed.setdefault(("FILESYSTEM", "deny"), []).extend(deny_scopes())
        except Exception:
            pass
    except Exception as e:
        # cannot load the constitution -> the membrane is non-functional -> FAIL-CLOSED
        audit({"decision": "DENY", "reason": f"constitution load error ({e})", "fail": "closed"})
        sys.stderr.write(f"[MEMBRANE BLOCK] session-hook: constitution load error ({e}) "
                         f"-> deny-by-default (fail-closed)\n")
        _emit("deny", f"constitution load error ({e})")
        sys.exit(2)

    # --- map the Claude Code tool event onto a normalized effect (kind, mode, target) ---
    if tool in WRITE_TOOLS:
        kind, mode, target = "FILESYSTEM", "write", (tin.get("file_path") or tin.get("notebook_path") or "")
    elif tool in READ_TOOLS:
        kind, mode, target = "FILESYSTEM", "read", (tin.get("file_path") or "")
    elif tool in NET_TOOLS:
        kind, mode, target = "NETWORK", "out", host_of(tin.get("url", ""))
    elif tool in SHELL_TOOLS:
        kind, mode, target = "SHELL", "exec", (tin.get("command", "") or "")
    else:
        # Not a mediated effect -> let the normal permission flow proceed. But RECORD it:
        # an event the membrane did not recognise is exactly the blind spot that hides a host
        # dialect we have not mapped yet (Cursor's payload shape was found this way). Passing
        # something through silently is indistinguishable, in the audit, from never being called.
        audit({"decision": "PASSTHROUGH", "reason": "event not in the mediated set",
               "tool": tool or None,
               "host_event": event.get("hook_event_name") or None,
               "event_keys": sorted(event.keys())[:20]})
        _emit("allow")
        sys.exit(0)

    # --- one shared, harness-independent decision (same core the MCP broker uses) ---
    from core.agent_adapter import decide
    allowset = parse_bash_allowlist(bio) if kind == "SHELL" else None
    denylist = parse_bash_denylist(bio) if kind == "SHELL" else None
    # whether an allowlist was STATED is a separate fact from what could be read out of it:
    # stated-but-empty is a broken parse and must deny, not fall through to denylist-only (O-20)
    stated = declares_allow(bio) if kind == "SHELL" else False
    ok, reason = decide(kind, mode, target, guard, allowset, denylist, allow_declared=stated)

    # Diagnostics recorded on EVERY decision, not just passthroughs. Two facts turned out to be
    # invisible in the audit and had to be inferred: which dialect the host actually sent (a
    # Cursor-shaped payload normalised to tool "Write" is indistinguishable from a Claude-shaped
    # one), and which mode was really in force (Cursor does not propagate settings.json `env`,
    # so a configured dryrun silently ran as the built-in enforce default). Inference is what we
    # keep having to retract; record it instead.
    diag = {
        "dialect": dialect,
        "host_event": host_event or None,
        "host_version": event.get("cursor_version") or None,
        "eff_mode": enforce_mode,
        "mode_from_env": "METASPACE_MODE" in os.environ,
        "bio_from_env": "METASPACE_SESSION_BIO" in os.environ,
        # where the default actually came from, so an O-13-style silent downgrade is visible
        "mode_src": ("env" if "METASPACE_MODE" in os.environ
                     else "user-file" if _DEFAULTS.get("mode") else "built-in"),
    }

    tgt = target[:80] if kind == "SHELL" else target
    if ok:
        allow(f"{tool} {kind}/{mode}: {str(target)[:60]}", tool=tool, kind=kind, mode=mode,
              target=tgt, **diag)
    else:
        if enforce_mode == "dryrun":
            # observe-only: record what WOULD be blocked and warn loudly, but let it through so
            # the first session is never over-blocked. `metaspace enforce` turns on blocking.
            sys.stderr.write(f"[MEMBRANE DRY-RUN] would block ({kind}/{mode}): {reason}\n")
            allow(f"DRY-RUN would-block ({kind}/{mode}): {reason}",
                  tool=tool, kind=kind, mode=mode, target=tgt, would_block=True, **diag)
        deny(f"{tool} blocked ({kind}/{mode}): {reason}", tool=tool, kind=kind, mode=mode,
             target=tgt, **diag)


if __name__ == "__main__":
    main()
