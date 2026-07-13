#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Friendly <-> .bio translation for the control panel.

The UI shows a vibecoder plain-language toggles (where can it write? which hosts? which
commands?) instead of raw .bio, and this module converts between those fields and a real
constitution. Rendering ALWAYS injects the self-protection deny (`FILESYSTEM deny
"{{CLAUDE_HOME}}/**"`), so no UI input can produce a constitution the agent could disable.

Stdlib-only; reuses core.guard.parse_capabilities so there is one parser, not two.
"""

import re


def _safe_cell(name):
    s = re.sub(r"[^A-Za-z0-9_]", "_", (name or "Project").strip()) or "Project"
    if s[0].isdigit():
        s = "P" + s
    return s


def fields_from_bio(text):
    """-> {write, read, network, shell_allow, shell_deny} (self-protection deny is implicit)."""
    from core.guard import parse_capabilities
    write, read, network = [], [], []
    for kind, mode, scopes in parse_capabilities(text or ""):
        if kind == "FILESYSTEM" and mode == "write":
            write += scopes
        elif kind == "FILESYSTEM" and mode == "read":
            read += scopes
        elif kind == "NETWORK" and mode == "out":
            network += scopes
        # FILESYSTEM deny is the self-protection rule — not a user-editable field
    allow = []
    for stmt in re.findall(r"ALLOW\s+([^;]*);", text or "", re.S):
        allow += re.findall(r'"([^"]*)"', stmt)
    deny = re.findall(r'DENY\s+"([^"]*)"', text or "")
    return {"write": write, "read": read, "network": network,
            "shell_allow": allow, "shell_deny": deny}


def bio_from_fields(fields, cell="Project"):
    """Render fields to a constitution. ALWAYS injects the self-protection deny."""
    fields = fields or {}
    write = fields.get("write") or ["{{PROJECT_ROOT}}/**"]
    read = fields.get("read") or ["**"]
    network = fields.get("network") or []
    allow = fields.get("shell_allow") or []
    deny = fields.get("shell_deny") or []

    out = ["CELL %s {" % _safe_cell(cell), "  CAPABILITIES {"]
    for s in write:
        out.append('    FILESYSTEM write "%s";' % s)
    for s in read:
        out.append('    FILESYSTEM read  "%s";' % s)
    # self-protection: non-negotiable, injected regardless of UI input
    out.append('    FILESYSTEM deny  "{{CLAUDE_HOME}}/**";')
    if network:
        out.append('    NETWORK    out   %s;' % ", ".join('"%s"' % h for h in network))
    out.append("  }")
    out.append("  BASH_POLICY {")
    if allow:
        out.append("    ALLOW %s;" % ", ".join('"%s"' % a for a in allow))
    for d in deny:
        out.append('    DENY "%s";' % d)
    out.append("  }")
    out.append("}")
    return "\n".join(out) + "\n"


# sensible starter for a new working directory (mirrors the shipped default)
SAFE_DEFAULTS = {
    "write": ["{{PROJECT_ROOT}}/**"],
    "read": ["**"],
    "network": ["docs.anthropic.com", "docs.claude.com"],
    "shell_allow": ["python", "python3", "pip", "pip3", "node", "npm", "npx", "pytest",
                    "git", "cargo", "rustc", "ls", "cat", "echo", "cd", "mkdir", "cp", "mv",
                    "touch", "grep", "find", "head", "tail", "wc", "sort", "test", "true", "false"],
    "shell_deny": ["git push", "git reset --hard", "rm -rf", "mkfs"],
}
