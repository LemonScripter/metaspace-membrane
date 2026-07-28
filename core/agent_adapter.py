#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harness-independent membrane decision core.

Both the Claude Code PreToolUse hook (products/ai_membrane) and the generic MCP
capability-broker (products/mcp_membrane) map their own harness-specific tool events onto a
*normalized effect* — (kind, mode, target) — and call decide(). One decision engine, many
harnesses: the guarantee (core.guard for capabilities, core.shell_policy for shell) lives
here; each adapter is a thin mapping layer. This is what makes "the same core on a different
harness" literally true rather than a slogan (see DECISIONS I-23).
"""

from core.guard import ConstitutionViolation
from core.shell_policy import check as _shell_check


def decide(kind, mode, target, guard, allowset=None, denylist=None, allow_declared=False):
    """Decide a normalized effect. Returns (allow: bool, reason: str).

    - SHELL goes through the structural shell policy (allowlist + token denylist, fail-closed).
      `allow_declared` carries the fact that the constitution stated an allowlist, so an empty
      `allowset` is read as a broken parse (deny) rather than as "no allowlist" (allow) — O-20.
    - Everything else (FILESYSTEM / NETWORK / ENV / SUBPROCESS / …) goes through the capability
      Guard: deny-by-default, scope-enforced. A ConstitutionViolation becomes (False, reason).

    The decision is pure with respect to enforcement; the caller is responsible for auditing
    and for translating the verdict into its harness's response (exit code, JSON-RPC, …).
    """
    if kind == "SHELL":
        return _shell_check(target or "", allow=allowset or set(), deny=denylist or [],
                            allow_declared=allow_declared)
    try:
        guard.check(kind, mode, target)
        return True, "allowed by the constitution"
    except ConstitutionViolation as e:
        return False, str(e)
