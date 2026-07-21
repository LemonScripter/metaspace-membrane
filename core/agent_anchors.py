#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent configuration anchors — the paths a membrane must never let an agent write.

An "anchor" is where a host keeps the configuration that switches the membrane on. C-33's
guarantee ("a deceived agent cannot disable the membrane") rests entirely on that location being
unwritable by the agent: the constitution denies it, so the agent cannot edit the hook out of
existence, and `metaspace off` is not shell-allowlisted.

WHY THIS MODULE EXISTS (O-14). The deny used to be a single hard-coded `{{CLAUDE_HOME}}/**` line
emitted into each generated constitution. That covered Claude Code, and — by luck rather than
design — Cursor too, because Cursor reads the *same* `~/.claude/settings.json`. Gemini CLI does
not: it has its own `~/.gemini/settings.json`. Supporting a host whose anchor is not defended
would hand a deceived agent a fresh way to turn the membrane off on that host, which is the
exact attack C-33 exists to stop. Every host added is otherwise another unlocked back door.

TWO PROPERTIES THAT MATTER, both learned the hard way:

  * The list lives in CODE, not in the `.bio`. A constitution written before a host existed
    cannot know about it, and a hand-edited one can have the line removed. Deriving the deny
    from here means old and edited constitutions are protected too — self-protection stops being
    a policy statement the user could accidentally delete and becomes a structural property.

  * Adding an anchor must never widen anything. These paths are only ever added to the DENY
    side, never to an allow scope, so the worst case of a wrong entry is an over-strict membrane
    (loud, correctable) rather than a silent hole.

Zero third-party dependencies — this sits on the enforcement hot path.
"""

import os

# Per-user anchors, relative to the home directory. Keep this list additive and boring.
USER_ANCHORS = (
    ".claude",     # Claude Code — and Cursor, which reads the same settings.json
    ".cursor",     # Cursor's own hooks.json / mcp.json
    ".gemini",     # Gemini CLI settings.json (hooks.BeforeTool)
    ".codex",      # OpenAI Codex CLI
    ".aider",      # Aider
    ".continue",   # Continue
)

# Machine-wide anchors. A non-admin agent usually cannot write these anyway; denying them is
# free insurance for the case where the agent runs elevated.
SYSTEM_ANCHORS = (
    r"C:\ProgramData\Cursor",
    "/etc/cursor",
    "/Library/Application Support/Cursor",
)


def _norm(p):
    return os.path.normpath(p).replace("\\", "/")


def anchor_dirs():
    """Absolute anchor directories (existing or not — a host may be installed later)."""
    home = os.path.expanduser("~")
    dirs = [_norm(os.path.join(home, a)) for a in USER_ANCHORS]
    dirs += [_norm(p) for p in SYSTEM_ANCHORS]
    return dirs


def deny_scopes():
    """Glob scopes for `FILESYSTEM deny`: the anchor directory itself and everything under it."""
    out = []
    for d in anchor_dirs():
        out.append(d)
        out.append(d + "/**")
    return out


def deny_lines():
    """The same scopes rendered as `.bio` lines, for constitutions that show their own rules."""
    return ['    FILESYSTEM deny  "%s/**";' % d for d in anchor_dirs()]
