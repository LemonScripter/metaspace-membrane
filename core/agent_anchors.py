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


# --------------------------------------------------------------------------------------------
# Data carve-outs (O-22)
# --------------------------------------------------------------------------------------------
# An anchor tree is not only control surface. Claude Code keeps per-project MEMORY under
# `~/.claude/projects/<slug>/memory/` — user content the agent is meant to write, and the only
# thing that survives between sessions. Denying the whole tree made `enforce` silently end that.
#
# The repair deliberately keeps the tree denied and exempts a short list, rather than switching to
# a list of denied config files. The asymmetry is the entire point:
#
#   * forget to carve something out  -> it over-blocks. Loud, and someone reports it.
#   * forget to deny a config file   -> a silent hole, and the hole is C-33 itself.
#
# Denial stays the default, so only the first kind of mistake is reachable.
#
# TWO LOCKS, ONE REMOVED. Being exempt here does not grant anything: it only lifts the code-level
# veto, after which the constitution must still grant the path like any other. An installation
# that never grants it is unchanged.
#
# NOT READABLE FROM A `.bio`, AND THAT IS LOAD-BEARING. If a constitution could declare its own
# exemptions, a deceived agent would only need to write one — which is exactly the escape hatch
# C-33 exists to remove. Entries are added here, in code, by a human, or not at all.
#
# HONEST COST (see C-05): memory is read back into the model's context in later sessions, so a
# writable memory directory is a place where a deceived agent could leave text for its future
# self. The membrane contains effects; it has never claimed to make the model injection-proof.
# What it does guarantee is that this path cannot be used to switch the membrane off.
DATA_CARVEOUTS = (
    ".claude/projects/*/memory/**",   # Claude Code per-project memory (user content)
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


def exempt_scopes():
    """Absolute globs the anchor deny does NOT cover (see DATA_CARVEOUTS)."""
    home = os.path.expanduser("~")
    return [_norm(os.path.join(home, c)) for c in DATA_CARVEOUTS]


def is_exempt(path):
    """True if `path` is user data inside an anchor rather than part of its control surface.

    Exemption is not permission — the caller still applies the constitution's own scopes.
    """
    import fnmatch
    if not path:
        return False
    t = _norm(str(path))
    return any(fnmatch.fnmatch(t, s) for s in exempt_scopes())
