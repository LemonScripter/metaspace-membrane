#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — the BASH_POLICY parser (one copy, not three).

WHY THIS MODULE EXISTS. The allow/deny statements of `BASH_POLICY` used to be read with
`ALLOW\\s+([^;]*);` in three separate places (the hook, the panel's field translation, the
ratification fingerprint). That capture stops at the first semicolon *anywhere* — including
one inside a comment:

    ALLOW   # runtimes (dev necessity; node too)
      "python", "node", "git", "ls";

…parses to ZERO programs. An empty allowlist is not a strict policy but the ABSENCE of one:
`core.shell_policy.check` engages the allowlist branch only `if allow`, so an empty list skips
the allowlist and the interpreter hardening together, leaving a porous denylist behind. The
constitution still looks deny-by-default to whoever wrote it, and nothing is logged (O-20).

Two structural answers, because fixing only the regex would leave the class open:

  1. comments are removed BEFORE matching, and the removal is quote-aware — a `#` inside a
     quoted string is data (`DENY "curl http://x/#frag"`), not the start of a comment;
  2. `declares_allow()` lets a caller tell "no allowlist configured" apart from "an allowlist
     was configured and could not be read". The second must fail closed. Any future parse bug
     in this file therefore becomes a loud denial rather than a silent downgrade.

Stdlib-only: the Warden hook imports this on every tool call (see DECISIONS I-49).
"""

import re

__all__ = ["strip_comments", "bash_policy_block", "parse_bash_allowlist",
           "parse_bash_denylist", "declares_allow"]

_ALLOW_STMT = re.compile(r"\bALLOW\b\s*([^;]*);", re.S)
# Both quoting styles. `DENY 'git push'` used to be dropped silently: the author wrote a denial,
# the membrane did not enforce it, and nothing said so — the O-20 family again, in a second file.
_QUOTED = re.compile(r'"([^"]*)"' r"|'([^']*)'")
_DENY_STMT = re.compile(r'\bDENY\b\s+(?:"([^"]*)"' r"|'([^']*)')")
_ALLOW_KW = re.compile(r"\bALLOW\b")
_BASH_BLOCK = re.compile(r"\bBASH_POLICY\b\s*\{")


def strip_comments(text):
    """Remove `#` comments, treating a `#` inside a double-quoted string as data.

    A naive `re.sub(r'#.*$', '')` would corrupt scopes and denied invocations that legitimately
    contain a fragment marker, so the scan tracks quoting. An unterminated quote is left alone
    rather than guessed at: the downstream parsers are the ones that must fail closed on it.
    """
    out = []
    for line in (text or "").splitlines():
        buf = []
        quote = None           # None, '"' or "'" — which character opened the string
        for ch in line:
            if quote:
                buf.append(ch)
                if ch == quote:
                    quote = None
            elif ch in ('"', "'"):
                quote = ch     # tracking WHICH quote matters: an apostrophe inside a
                buf.append(ch) # double-quoted scope must not open a string
            elif ch == "#":
                break          # rest of the line is a comment
            else:
                buf.append(ch)
        out.append("".join(buf))
                               # a string does not span lines in .bio, so state resets per line
    return "\n".join(out)


def _quoted_values(text):
    """Every quoted string in `text`, either quoting style, in order.

    The patterns use alternation, so `findall` yields a tuple per match with one group filled.
    Collapsing that here keeps both callers from having to know it.
    """
    return [a or b for a, b in _QUOTED.findall(text or "")]


def bash_policy_block(bio_text):
    """-> the contents of `BASH_POLICY { … }`, comments removed. '' when there is no such block.

    Scoping matters, and not only for tidiness: `ALLOW` is also the keyword of the DEPENDENCIES
    block (`ALLOW fastapi;`). A block-agnostic search would report "this constitution declares a
    shell allowlist" for a constitution that declares no such thing, and the fail-closed rule
    built on that answer would then deny every shell call in it. Correct in direction, wrong in
    fact — so the question is asked of the right block.
    """
    clean = strip_comments(bio_text)
    m = _BASH_BLOCK.search(clean)
    if not m:
        return ""
    depth, in_str, start = 1, False, m.end()
    i = start
    while i < len(clean):
        ch = clean[i]
        if ch == '"':
            in_str = not in_str
        elif not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return clean[start:i]
        i += 1
    return clean[start:]          # unterminated block: the parsers below still fail closed


def declares_allow(bio_text):
    """True if the constitution states a BASH_POLICY ALLOW (comments do not count).

    The caller uses this to distinguish "this constitution runs no allowlist" from "this
    constitution has an allowlist that produced nothing", which must be treated as fail-closed.
    """
    return bool(_ALLOW_KW.search(bash_policy_block(bio_text)))


def parse_bash_allowlist(bio_text):
    """-> allowlisted program names, in the order the constitution lists them, deduplicated.

    Order is kept because the panel renders this list back to the operator; membership is all
    the policy needs (`core.shell_policy.check` sets it), so both callers are served by one
    function rather than by two that could drift apart again.
    """
    out, seen = [], set()
    for stmt in _ALLOW_STMT.findall(bash_policy_block(bio_text)):
        for name in _quoted_values(stmt):
            if name and name not in seen:
                seen.add(name)
                out.append(name)
    return out


def parse_bash_denylist(bio_text):
    """-> list of denied invocations (token prefixes, e.g. "git push").

    Deliberately NOT scoped to BASH_POLICY, unlike the allowlist. The two errors are not
    symmetric: an out-of-block ALLOW would grant something the author never meant to grant,
    while an out-of-block DENY only refuses more. Reading every `DENY "…"` in the file errs
    towards refusing, and it also keeps the ratification fingerprint stable for any constitution
    that placed one elsewhere — scoping it could flip such a file RATIFIED -> TAMPERED (O-3).
    """
    return [a or b for a, b in _DENY_STMT.findall(strip_comments(bio_text))]
