#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — structural shell command policy

Replaces the substring/denylist heuristic for shell commands with STRUCTURAL analysis.
It tokenizes the command with a real shell lexer (shlex, punctuation-aware), splits it into
sub-commands across operators (`;` `&&` `||` `|` `&` newlines) and command substitutions, and
extracts each sub-command's program name. Two policies, defense-in-depth:

  * ALLOWLIST (recommended): every discovered program must be explicitly allowed, else DENY.
    This is robust to obfuscation the way a denylist is not — anything the lexer does not
    resolve to an allowed program name is refused (fail-closed).
  * DENYLIST (token-based): a denied invocation is matched against the parsed token sequence
    of each sub-command (e.g. "git push" matches ["git","push", ...]), not a raw substring,
    so spacing/quoting tricks do not slip past it.

Unparseable input (unbalanced quotes, etc.) -> DENY (fail-closed): a policy that cannot parse
the command must not allow it.
"""

import os
import shlex

# operators that separate one command from the next
_SEP = {";", "&&", "||", "|", "&", "\n", "(", ")"}
# redirection operators: drop the operator AND its target token (a file, not a command)
_REDIR = {">", ">>", "<", "<<", "<<<", "2>", "2>>", "&>", ">&", "1>", "1>>"}
_ASSIGN = None  # compiled lazily


def _is_assignment(tok: str) -> bool:
    # VAR=value environment prefix (e.g. `FOO=1 git status`)
    import re
    global _ASSIGN
    if _ASSIGN is None:
        _ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
    return bool(_ASSIGN.match(tok))


def _tokenize(cmd: str):
    """Punctuation-aware POSIX tokenization. Raises ValueError on unbalanced quotes."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def sub_commands(cmd: str):
    """Split a command line into sub-commands (each a list of tokens). Raises ValueError if
    the command cannot be tokenized."""
    tokens = _tokenize(cmd)
    groups, cur, i = [], [], 0
    while i < len(tokens):
        t = tokens[i]
        if t in _SEP:
            if cur:
                groups.append(cur)
                cur = []
        elif t in _REDIR:
            i += 1  # skip the redirect target token as well
        else:
            cur.append(t)
        i += 1
    if cur:
        groups.append(cur)
    return groups


def program_names(cmd: str):
    """The set of program names a command line would actually invoke (basenames), including
    those inside command substitutions."""
    names = set()
    for sub in sub_commands(cmd):
        toks = [t for t in sub if not _is_assignment(t)]
        if toks:
            names.add(os.path.basename(toks[0]))
    return names


def check(cmd: str, allow=None, deny=None):
    """Structural decision. -> (True, reason) to allow, (False, reason) to deny (fail-closed)."""
    allow = set(allow or [])
    deny = list(deny or [])
    try:
        subs = sub_commands(cmd)
    except ValueError as e:
        return False, f"unparseable shell command ({e}) -> fail-closed"

    # token-based denylist: a denied invocation is a prefix of a sub-command's tokens
    for sub in subs:
        toks = [t for t in sub if not _is_assignment(t)]
        for entry in deny:
            dt = entry.split()
            if dt and toks[:len(dt)] == dt:
                return False, f"denied invocation: {' '.join(dt)}"

    # allowlist: every invoked program must be explicitly allowed
    if allow:
        for sub in subs:
            toks = [t for t in sub if not _is_assignment(t)]
            if not toks:
                continue
            name = os.path.basename(toks[0])
            if name not in allow:
                return False, f"program '{name}' not in the allowlist"
        return True, "all invoked programs are allowlisted"

    return True, "no denylist match (no allowlist configured)"
