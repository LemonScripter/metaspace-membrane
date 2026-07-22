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
import json

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
        # matcher uses Gemini's own tool names, exactly as its `hooks migrate` rewrites them
        "matcher": "run_shell_command|write_file|replace|read_file",
        "verdict": "json-decision",             # {"decision": "block"|"deny"|"ask", "reason": …}
        "propagates_env": None,                 # UNMEASURED — do not assume either way
        "notes": "Surveyed (C-56); no live run yet, so no tier may be claimed (C-57).",
    },
    "antigravity": {
        "label": "Antigravity CLI (agy)",
        "detect": ["~/.gemini/antigravity-cli", "~/AppData/Local/agy"],
        # Execution SOLVED by experiment (O-16 update, 2026-07-22): agy IS a hook agent. But it is
        # deliberately NOT a generic-merge host, so `config` stays None: unlike Claude/Cursor/Gemini
        # there is no single settings file to wire. Its executing hooks live in a PER-WORKSPACE
        # `.agents/hooks.json` (its `jsonhook.go` path), and that path is gated by a server-side
        # Unleash flag (`json-hooks-enabled`, constrained to ide=jetski) that must first be flipped
        # via a local mock. So the generic installer correctly REFUSES it — it needs the dedicated
        # agy path (mock + adapter + launcher), marked below.
        "config": None,
        "config_kind": None,
        "install": "special",                    # not a JSON-merge; see the dedicated agy path
        "exec_config": ".agents/hooks.json",     # per-workspace; schema: name -> event -> [{matcher, hooks[]}]
        "activation": "unleash-mock",            # json-hooks-enabled is ide=jetski-gated (O-16)
        "pre_tool_event": "PreToolUse",          # CONFIRMED live (2026-07-22), not merely inferred
        "matcher": None,                         # None keeps install_entry() returning (None, None)
        "verdict": "json-decision",              # {"decision": allow|deny|ask|force_ask, ...} — confirmed
        "propagates_env": False,                 # no settings.json env; UNLEASH_URL is set at launch
        "notes": "Hook execution SOLVED by experiment (O-16 update): agy's workspace "
                 "`.agents/hooks.json` fires PreToolUse once the `json-hooks-enabled` Unleash flag "
                 "is flipped (local mock, UNLEASH_URL redirect). NOT a JSON-merge install — needs "
                 "the dedicated agy path (mock + adapter + launcher), so the generic installer "
                 "refuses it. Reverse-engineered and experimental; no proof harness yet (O-16 OPEN).",
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
        # a host may be detected without its config location being known (Antigravity): report
        # that honestly rather than inventing a path
        cfg = _expand(p["config"]) if p.get("config") else None
        out.append({
            "id": hid,
            "label": p["label"],
            "installed": installed,
            "config": cfg,
            "config_exists": bool(cfg) and os.path.exists(cfg),
            "pre_tool_event": p["pre_tool_event"],
            "verdict": p["verdict"],
            "propagates_env": p["propagates_env"],
            "notes": p["notes"],
        })
    return out


# The local mock Unleash that flips agy's `json-hooks-enabled` flag listens here. Its being up is
# the strongest cheap machine-level signal that agy's (experimental) protection is live right now:
# without it the flag reverts and hooks stop firing. Not a guarantee — the launcher must also inject
# UNLEASH_URL — so this only ever refines the `experimental` tier, never promotes it to `protected`.
AGY_MOCK_HOST, AGY_MOCK_PORT = "127.0.0.1", 4242


def _port_open(host, port, timeout=0.25):
    """True if something accepts a TCP connection at host:port. Fast, best-effort, never raises."""
    import socket
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _hook_wired(config_path, event):
    """True if OUR PreToolUse hook is present in this host's config file for `event`.
    Best-effort and read-only — a check for the control panel's status view, not an authority."""
    if not config_path:
        return False
    p = _expand(config_path)
    if not os.path.exists(p):
        return False
    try:
        with open(p, encoding="utf-8-sig") as fh:      # some hosts write a BOM
            s = json.load(fh) or {}
    except Exception:
        return False
    hooks = (s.get("hooks") or {}).get(event, [])
    return any("session_guard_hook" in json.dumps(h) for h in hooks)


def protection():
    """Per-host protection status for the control panel: detection PLUS whether the membrane is
    actually wired. Read-only, best-effort — makes the multi-host reality visible so a user is
    never silently unprotected. A 'special' host (Antigravity) is opt-in and its per-workspace
    wiring is not a single-file check, so it is reported as `experimental`, never as 'protected'.

    status ∈ {protected, unprotected, experimental, absent}.
    """
    out = []
    for h in detect():
        prof = HOST_PROFILES.get(h["id"], {})
        detail = None
        if not h["installed"]:
            protected, status = False, "absent"
        elif prof.get("install") == "special":
            # NEVER promoted to 'protected' (conditional + reverse-engineered + no proof harness,
            # O-16). But reflect the observable live state so the panel is not stuck on a generic
            # label: `active` when the activation mock is up, `inactive` otherwise.
            protected, status = None, "experimental"
            detail = "active" if _port_open(AGY_MOCK_HOST, AGY_MOCK_PORT) else "inactive"
        else:
            # a host may read another's config (Cursor <- Claude Code, same settings.json under
            # Claude's PreToolUse key); inherit the owner's wiring so it is not falsely "unprotected".
            owner = HOST_PROFILES.get(prof.get("shares_config_with"), prof)
            protected = _hook_wired(owner.get("config"), owner.get("pre_tool_event"))
            status = "protected" if protected else "unprotected"
        out.append({"id": h["id"], "label": h["label"], "installed": h["installed"],
                    "protected": protected, "status": status, "detail": detail})
    return out


def install_entry(host_id, hook_command, timeout=30):
    """The hook entry to merge into a host's config, in that host's own shape.

    Gemini's config is structurally identical to Claude's — same
    `{matcher, hooks:[{type, command, timeout}]}` shape — only the event name and the tool names
    in the matcher differ. That is not a coincidence: Gemini ships `gemini hooks migrate`, which
    converts a Claude config by renaming exactly those two things. Returns
    (event_name, entry) or (None, None) when the host cannot be installed into.
    """
    p = HOST_PROFILES.get(host_id) or {}
    if not p.get("config") or not p.get("matcher"):
        return None, None
    return p["pre_tool_event"], {
        "matcher": p["matcher"],
        "hooks": [{"type": "command", "command": hook_command, "timeout": timeout}],
    }


def installable():
    """Hosts we can install into today — i.e. those whose config path is actually known."""
    return [h for h, p in HOST_PROFILES.items() if p.get("config") and p.get("matcher")]


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
