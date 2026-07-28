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

INTERPRETER PASSTHROUGH (hardened): a shell interpreter (sh/bash/…) can run ANY program, so
allowlisting one would silently void the whole allowlist (`bash evil.sh` sneaks `evil.sh` past
a program-name check). An interpreter invocation is therefore only allowed when what it will
run is itself allowlisted:
  - `bash script.sh`      -> the script's basename must be allowlisted;
  - `bash -c "CMD"`       -> CMD is re-checked recursively through this same policy;
  - `CMD | bash`          -> the interpreter executes unverifiable piped stdin -> DENY;
  - `bash` (bare)         -> nothing is specified to run -> allowed.
This closes the "Friendly Fire" class of attack (AI Now Institute, 2026), where a prompt-
injected agent is steered to run a malicious repo script via a shell wrapper.

Unparseable input (unbalanced quotes, etc.) -> DENY (fail-closed): a policy that cannot parse
the command must not allow it.
"""

import os
import shlex

# operators that separate one command from the next
_SEP = {";", "&&", "||", "|", "&", "\n", "(", ")"}
# redirection operators: drop the operator AND its target token (a file, not a command)
_REDIR = {">", ">>", "<", "<<", "<<<", "2>", "2>>", "&>", ">&", "1>", "1>>"}
# shell interpreters: allowlisting one voids the allowlist (they run ANY program), so an
# interpreter is only allowed if what it will execute is itself allowlisted (see check()).
_SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash", "ksh", "ash"}
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


def _sub_commands_ex(cmd: str):
    """Split a command line into (tokens, piped_in) pairs, where piped_in is True when the
    sub-command receives its stdin from a preceding `|`. Raises ValueError if the command
    cannot be tokenized."""
    tokens = _tokenize(cmd)
    groups, cur, cur_piped, i = [], [], False, 0
    while i < len(tokens):
        t = tokens[i]
        if t in _SEP:
            if cur:
                groups.append((cur, cur_piped))
                cur = []
            cur_piped = (t == "|")   # the next sub-command is piped-in iff this separator is |
        elif t in _REDIR:
            i += 1  # skip the redirect target token as well
        else:
            cur.append(t)
        i += 1
    if cur:
        groups.append((cur, cur_piped))
    return groups


def sub_commands(cmd: str):
    """Split a command line into sub-commands (each a list of tokens). Raises ValueError if
    the command cannot be tokenized."""
    return [toks for toks, _piped in _sub_commands_ex(cmd)]


def program_names(cmd: str):
    """The set of program names a command line would actually invoke (basenames), including
    those inside command substitutions."""
    names = set()
    for sub in sub_commands(cmd):
        toks = [t for t in sub if not _is_assignment(t)]
        if toks:
            names.add(os.path.basename(toks[0]))
    return names


def _check_interpreter(toks, piped, allow, deny):
    """An allowlisted shell interpreter (toks[0]) may only run allowlisted work. Returns
    (True, reason) if what it will execute is verifiably allowlisted, else (False, reason)."""
    prog = os.path.basename(toks[0])
    # 1) piped-in stdin: the interpreter runs content we cannot see -> fail-closed
    if piped:
        return False, f"shell interpreter '{prog}' runs unverifiable piped stdin -> fail-closed"
    args = toks[1:]
    # 2) -c / -lc / -xc "CMD": re-check the command string through this same policy
    for j, a in enumerate(args):
        if a.startswith("-") and not a.startswith("--") and "c" in a:
            if j + 1 < len(args):
                ok, reason = check(args[j + 1], allow=allow, deny=deny)
                return (ok, "shell -c payload allowlisted" if ok
                        else f"shell -c payload blocked: {reason}")
            return False, f"shell interpreter '{prog}' -c with no command string -> fail-closed"
    # 3) first non-flag argument is a script path -> its basename must be allowlisted too
    for a in args:
        if a.startswith("-"):
            continue
        script = os.path.basename(a)
        if script not in allow:
            return False, f"shell script '{script}' run by '{prog}' is not in the allowlist"
        return True, f"shell script '{script}' allowlisted"
    # 4) bare interpreter, no script, not piped -> nothing specified to run
    return True, f"bare shell interpreter '{prog}' (no program specified)"


def check(cmd: str, allow=None, deny=None, allow_declared: bool = False):
    """Structural decision. -> (True, reason) to allow, (False, reason) to deny (fail-closed).

    `allow_declared` says the constitution DID state an allowlist. An empty `allow` is then a
    parse failure, not a permissive policy, and must deny — otherwise the allowlist branch below
    is skipped and the interpreter hardening goes with it, silently downgrading deny-by-default
    to a porous denylist. That is how a semicolon inside a comment once emptied a real
    constitution without a word of warning (O-20).
    """
    allow = set(allow or [])
    deny = list(deny or [])
    if allow_declared and not allow:
        return False, ("the constitution declares a BASH_POLICY allowlist but no program could "
                       "be read from it -> fail-closed (an empty allowlist is not a policy)")
    try:
        subs = _sub_commands_ex(cmd)
    except ValueError as e:
        return False, f"unparseable shell command ({e}) -> fail-closed"

    # token-based denylist: a denied invocation is a prefix of a sub-command's tokens
    for toks_raw, _piped in subs:
        toks = [t for t in toks_raw if not _is_assignment(t)]
        for entry in deny:
            dt = entry.split()
            if dt and toks[:len(dt)] == dt:
                return False, f"denied invocation: {' '.join(dt)}"

    # allowlist: every invoked program must be explicitly allowed
    if allow:
        for toks_raw, piped in subs:
            toks = [t for t in toks_raw if not _is_assignment(t)]
            if not toks:
                continue
            name = os.path.basename(toks[0])
            if name not in allow:
                return False, f"program '{name}' not in the allowlist"
            # an allowlisted interpreter must not become an allowlist bypass (see module docstring)
            if name in _SHELL_INTERPRETERS:
                ok, reason = _check_interpreter(toks, piped, allow, deny)
                if not ok:
                    return False, reason
        return True, "all invoked programs are allowlisted"

    return True, "no denylist match (no allowlist configured)"
