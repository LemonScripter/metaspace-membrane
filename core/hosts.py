#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Host profiles — what varies between agents, as DATA rather than code (C-38).

Three hosts have now been surveyed by measurement (docs/AGENT_SURVEY.md), and the finding that
shapes this module is that they differ in *spelling*, never in *meaning*:

    host          pre-tool event    shell tool           write tool       verdict channel
    Claude Code   PreToolUse        Bash                 Write / Edit     exit code 2
    Cursor        preToolUse        Bash (Claude-compat) Write            {"permission": "deny"}
    Gemini CLI    BeforeTool        run_shell_command    write_file       {"decision": "deny"}

Not one of those differences reaches the decision core. `core.guard` still decides on a
normalized `(kind, mode, target)`; everything above is a lookup. So the per-host work is a table,
not an adapter — which is what makes "one membrane, many agents" honest rather than aspirational.

TWO DESIGN RULES, both learned by getting them wrong first:

  * **Host vocabulary never enters the `.bio`.** A constitution that named host internals would
    stop being portable, and every vendor update would change the policy fingerprint and flip
    RATIFIED to TAMPERED (O-3). The `.bio` describes effects; this table describes hosts.

  * **The verdict is emitted as a superset, not as a guess.** Rather than detect which host
    invoked us and answer in its dialect, the hook emits every key at once: `permission` for
    Cursor, `decision` + `reason` for Gemini, and exit code 2 for Claude Code. Each host reads
    its own field and ignores the rest. Guessing wrong would mean a verdict silently going
    unheard — which is exactly the failure that made the membrane inert under Cursor.

Detection is best-effort and never authoritative: presence of a config directory says a host is
probably installed, not that the membrane works there. Only a run says that.

Zero third-party dependencies — this sits on the enforcement hot path.
"""

import os

# ---------------------------------------------------------------------------
# Tool aliases: every host's tool name -> the canonical (Claude Code) name the
# hook's effect mapping already understands. Names do not collide across hosts.
# ---------------------------------------------------------------------------
TOOL_ALIASES = {
    # Gemini CLI 0.50.0 — from its own EVENT/TOOL_NAME_MAPPING in hooks/migrate.ts
    "run_shell_command": "Bash",
    "write_file": "Write",
    "replace": "Edit",
    "read_file": "Read",
    "glob": "Glob",
    "grep": "Grep",
    "ls": "LS",
    # Cursor — its Claude-compat layer already maps onto Claude's names, so only its
    # native event payloads need translating (handled by HOST_EVENTS below).
}

# Host-native pre/post tool events -> (canonical tool, payload field holding the target).
HOST_EVENTS = {
    # Cursor native (hooks.json)
    "beforeShellExecution": ("Bash", "command"),
    "afterShellExecution":  ("Bash", "command"),
    "beforeReadFile":       ("Read", "file_path"),
    "beforeTabFileRead":    ("Read", "file_path"),
    "afterFileEdit":        ("Write", "file_path"),
    "afterTabFileEdit":     ("Write", "file_path"),
}

# Events that only a *pre* hook can stop. Recorded for honesty: a post event may be observed
# and audited, but a verdict returned from one is advisory (O-11, measured on Cursor).
BLOCKING_EVENTS = {
    "PreToolUse", "preToolUse", "BeforeTool",
    "beforeShellExecution", "beforeMCPExecution", "beforeReadFile", "beforeTabFileRead",
}

HOST_PROFILES = {
    "claude-code": {
        "label": "Claude Code",
        "detect": ["~/.claude"],
        "config": "~/.claude/settings.json",
        "config_kind": "claude-settings",       # hooks.PreToolUse[].hooks[].command
        "pre_tool_event": "PreToolUse",
        "verdict": "exit-code",
        "propagates_env": True,
        "notes": "",
    },
    "cursor": {
        "label": "Cursor",
        "detect": ["~/.cursor"],
        # Cursor reads Claude's settings file; it also has its own ~/.cursor/hooks.json.
        "config": "~/.claude/settings.json",
        "config_kind": "claude-settings",
        "shares_config_with": "claude-code",
        "pre_tool_event": "preToolUse",
        "verdict": "json-permission",           # {"permission": "allow"|"deny"|"ask"}
        "propagates_env": False,                # measured: O-13
        "notes": "Does not propagate settings.json env (O-13). Post-edit hooks cannot veto (O-11).",
    },
    "gemini-cli": {
        "label": "Gemini CLI",
        "detect": ["~/.gemini"],
        "config": "~/.gemini/settings.json",
        "config_kind": "gemini-settings",       # hooks.BeforeTool[]
        "pre_tool_event": "BeforeTool",
        "verdict": "json-decision",             # {"decision": "block"|"deny"|"ask", "reason": …}
        "propagates_env": None,                 # UNMEASURED — do not assume either way
        "notes": "Surveyed (C-56); no live run yet, so no tier may be claimed (C-57).",
    },
}


def _expand(p):
    return os.path.expanduser(p).replace("\\", "/")


def canonical_tool(name):
    """Map a host's tool name onto the canonical one, or return it unchanged."""
    return TOOL_ALIASES.get(name, name)


def detect():
    """-> list of {id, label, installed, config, config_exists, notes}. Best-effort only.

    A present config directory means the host is probably installed. It does NOT mean the
    membrane is active there, and it never implies a guarantee tier — that needs a run.
    """
    out = []
    for hid, p in HOST_PROFILES.items():
        installed = any(os.path.isdir(_expand(d)) for d in p["detect"])
        cfg = _expand(p["config"])
        out.append({
            "id": hid,
            "label": p["label"],
            "installed": installed,
            "config": cfg,
            "config_exists": os.path.exists(cfg),
            "pre_tool_event": p["pre_tool_event"],
            "verdict": p["verdict"],
            "propagates_env": p["propagates_env"],
            "notes": p["notes"],
        })
    return out


def verdict_payload(permission, reason=""):
    """The verdict as a SUPERSET, so every host finds the field it reads.

    Cursor reads `permission`; Gemini reads `decision` (+ `reason`); Claude Code reads the exit
    code and ignores stdout. Emitting all of them removes the need to identify the caller — and
    a wrong identification would mean the verdict going unheard, which is precisely how the
    membrane ended up inert under Cursor.
    """
    out = {"permission": permission}
    if permission == "deny":
        out["decision"] = "deny"
        out["reason"] = reason or "blocked by the constitution"
        out["user_message"] = f"[MEMBRANE BLOCK] {reason}" if reason else "[MEMBRANE BLOCK]"
        out["agent_message"] = (
            f"Blocked by the MetaSpace membrane: {reason}. "
            f"This effect is outside the constitution — do not retry it."
            if reason else "Blocked by the MetaSpace membrane.")
    else:
        out["decision"] = "approve"
    return out
