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
import re
import shlex

# Characters that, on their own or in any run, separate one command from the next. Membership is
# tested per-CHARACTER rather than against a list of spellings, because shlex groups a run of
# punctuation into ONE token: `|&` and `;&` are real shell operators that were not in the old list
# and therefore did not separate anything, so `curl … |& bash` collapsed into a single sub-command
# whose program was `curl` — the `bash` was never checked and the interpreter hardening never ran.
# A list of spellings is the wrong shape here for the same reason an allowlist of file names was
# wrong in O-22: whatever it forgets, fails open.
_SEP_CHARS = set(";|&")
# grouping tokens, which also end a command
_GROUP = {"(", ")"}
_SEP = {";", "&&", "||", "|", "&", "\n", "(", ")"}   # kept for callers that import it
# redirection operators: drop the operator AND its target token (a file, not a command)
_REDIR = {">", ">>", "<", "<<", "<<<", "2>", "2>>", "&>", ">&", "1>", "1>>"}
# shell interpreters: allowlisting one voids the allowlist (they run ANY program), so an
# interpreter is only allowed if what it will execute is itself allowlisted (see check()).
_SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash", "ksh", "ash"}
_ASSIGN = None  # compiled lazily


def _is_separator(tok: str) -> bool:
    """True for any token made only of separator punctuation (`;`, `|`, `&`) or a grouping paren."""
    return tok in _GROUP or (bool(tok) and all(c in _SEP_CHARS for c in tok))


def _prog_name(tok: str) -> str:
    """The program a token names, compared the way the OS resolves it (O-26).

    Windows is case-insensitive and its executables carry `.exe`, so a plain string match got two
    things wrong at once: `RM -RF /` ran under a denylist that forbade `rm -rf`, and a venv
    interpreter given by path was refused although `python` was allowlisted. Only `.exe` is
    stripped — a `foo.bat` or `foo.cmd` is a script, not the same artefact as bare `foo`, and
    treating them as equal would let a script inherit an allowlist entry meant for a binary.
    """
    name = os.path.basename(tok)
    if os.name == "nt":
        name = name.lower()
        if name.endswith(".exe"):
            name = name[:-4]
    return name


def _fold(tok: str) -> str:
    """Case-fold a non-program token where the OS would. Errs towards matching more."""
    return tok.lower() if os.name == "nt" else tok


def _is_assignment(tok: str) -> bool:
    # VAR=value environment prefix (e.g. `FOO=1 git status`)
    import re
    global _ASSIGN
    if _ASSIGN is None:
        _ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
    return bool(_ASSIGN.match(tok))


# heredoc opener: `<<DELIM`, `<<'DELIM'`, `<<"DELIM"`, `<<-DELIM`. The `(?!<)` keeps `<<<`
# (a here-string, which has no body) out of this — that is stdin, not a body.
_HEREDOC_START = re.compile(r"<<(?!<)-?[ \t]*(?:'([^']*)'|\"([^\"]*)\"|([A-Za-z_][A-Za-z0-9_]*))")


def _strip_heredocs(cmd: str) -> str:
    """Remove heredoc BODIES, keeping the command lines themselves (O-24).

    A heredoc body is an argument, not a list of commands, but the tokenizer cannot know that:
    shlex swallows the newlines, so `python - <<'PY' … PY` reached this policy as one sub-command
    per body line and was refused for invoking "programs" like `p,`. Stripping the bodies before
    tokenizing is what makes a body data again.

    The `<<DELIM` operator is deliberately LEFT in place. It is what tells check() that this
    sub-command feeds a script on stdin — harmless for `python`, and something that must stay
    refused for a shell. Stripping the operator too would silently turn `bash <<'EOF'` into a
    bare `bash`, which is allowed.

    An unterminated heredoc raises ValueError, i.e. deny: a command whose extent cannot be
    determined must not be allowed.
    """
    if "<<" not in cmd:
        return cmd
    lines = cmd.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for m in _HEREDOC_START.finditer(line):
            delim = m.group(1) or m.group(2) or m.group(3)
            closed = False
            while i < len(lines):
                probe = lines[i].strip()
                i += 1
                if probe == delim:          # the terminator, alone on its line
                    closed = True
                    break
            if not closed:
                raise ValueError(f"unterminated heredoc <<{delim}")
    return "\n".join(out)


def _newlines_to_separators(cmd: str) -> str:
    """Turn newlines OUTSIDE quotes into explicit `;` separators (O-25).

    `shlex` with `whitespace_split=True` treats a newline as ordinary whitespace and never emits
    it as a token, so the `"\\n"` entry in `_SEP` was dead code and every line after the first
    merged into the first sub-command. Only the first line's program was checked, and the
    denylist — which matches a token prefix — never saw the rest. `git status` followed by a
    newline and `rm -rf /` was ALLOWED, with `rm -rf` explicitly denied.

    Three cases must survive the substitution:
      * a newline inside a quoted string is data (`python -c "print('a\\nb')"`) -> left alone;
      * a trailing backslash is a line continuation -> the pair is dropped, joining the lines,
        because splitting there would refuse a command the user never wrote;
      * a backslash-escaped quote inside a string must not flip the quoting state.
    Heredoc bodies are removed before this runs (see `_strip_heredocs`), so their lines cannot
    become commands.
    """
    if "\n" not in cmd and "`" not in cmd:
        return cmd
    out = []
    quote = None          # None, "'" or '"'
    reopen = False        # a substitution was opened from inside a double-quoted string
    i, n = 0, len(cmd)
    while i < n:
        ch = cmd[i]
        if quote == "'":
            # inside single quotes nothing is special, not even a backslash
            out.append(ch)
            if ch == "'":
                quote = None
        elif quote == '"':
            if ch == "\\" and i + 1 < n:
                out.append(ch)
                out.append(cmd[i + 1])
                i += 2
                continue
            if ch == "`":
                # A backtick substitutes INSIDE double quotes too. Close the quote around the
                # separator so the substituted command comes out into the open, where it is
                # checked like any other; `reopen` puts the string back together at the closing
                # backtick, or shlex would see an unbalanced quote and deny a legitimate command.
                out.append('" ; ')
                quote, reopen = None, True
                i += 1
                continue
            out.append(ch)
            if ch == '"':
                quote = None
        else:
            if ch in ("'", '"'):
                quote = ch
                out.append(ch)
            elif ch == "\\" and i + 1 < n and cmd[i + 1] == "\n":
                i += 2          # line continuation: drop the backslash AND the newline
                continue
            elif ch == "\\" and i + 2 < n and cmd[i + 1] == "\r" and cmd[i + 2] == "\n":
                i += 3          # ...the CRLF spelling of the same thing
                continue
            elif ch == "`":
                # Backtick substitution runs a command, exactly like `$( … )` — which already
                # split, but only by accident, because parentheses are separators. A backtick is
                # not punctuation to shlex, so `` echo `rm -rf /` `` arrived as one sub-command
                # named `echo`. Turning each backtick into a separator makes the substituted
                # command a sub-command of its own, which is what it is.
                if reopen:
                    out.append(' ; "')      # closing backtick of a substitution inside a string
                    quote, reopen = '"', False
                else:
                    out.append(";")
            elif ch == "\n":
                # Collapse consecutive separators. A blank line would emit `;;`, and shlex groups
                # a run of punctuation into ONE token — `;;` is not in _SEP, so it would be read
                # as an ordinary word and the commands around it would merge again. Same for a
                # line that already ends in `;`.
                j = len(out) - 1
                while j >= 0 and out[j] in (" ", "\t"):
                    j -= 1
                if j < 0 or out[j] != ";":
                    out.append(";")
            elif ch == "\r":
                pass            # drop a bare CR; the following \n does the work
            else:
                out.append(ch)
        i += 1
    return "".join(out)


def _tokenize(cmd: str):
    """Punctuation-aware POSIX tokenization. Raises ValueError on unbalanced quotes."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def _sub_commands_ex(cmd: str):
    """Split a command line into (tokens, piped_in, stdin_script) triples.

    `piped_in` is True when the sub-command receives stdin from a preceding `|`.
    `stdin_script` is True when it receives stdin from a heredoc or a here-string. The two differ
    in origin and are identical in consequence for a shell: input this policy has not inspected.
    Raises ValueError if the command cannot be tokenized or a heredoc is left unterminated.
    """
    # order matters: heredoc bodies go first, or their lines become commands at the next step
    tokens = _tokenize(_newlines_to_separators(_strip_heredocs(cmd)))
    groups, cur, cur_piped, cur_stdin, i = [], [], False, False, 0
    while i < len(tokens):
        t = tokens[i]
        if t in _REDIR:
            if t in ("<<", "<<-", "<<<"):
                cur_stdin = True     # a script arrives on stdin; only the shell case is refused
            i += 2                   # skip the redirect target token as well
            continue
        if _is_separator(t):
            if cur:
                groups.append((cur, cur_piped, cur_stdin))
                cur, cur_stdin = [], False
            # the next sub-command reads stdin from the previous one iff a pipe is involved
            cur_piped = ("|" in t)
        else:
            cur.append(t)
        i += 1
    if cur:
        groups.append((cur, cur_piped, cur_stdin))
    return groups


def sub_commands(cmd: str):
    """Split a command line into sub-commands (each a list of tokens). Raises ValueError if
    the command cannot be tokenized."""
    return [toks for toks, _piped, _stdin in _sub_commands_ex(cmd)]


def program_names(cmd: str):
    """The set of program names a command line would actually invoke (basenames), including
    those inside command substitutions."""
    names = set()
    for sub in sub_commands(cmd):
        toks = [t for t in sub if not _is_assignment(t)]
        if toks:
            names.add(_prog_name(toks[0]))
    return names


def _check_interpreter(toks, unverified_stdin, allow, deny):
    """An allowlisted shell interpreter (toks[0]) may only run allowlisted work. Returns
    (True, reason) if what it will execute is verifiably allowlisted, else (False, reason)."""
    prog = _prog_name(toks[0])
    # 1) stdin this policy cannot see — a pipe, a heredoc or a here-string. The shell executes it
    #    verbatim, so there is nothing to check against the allowlist -> fail-closed. The
    #    here-string case was a live hole: `<<<` is a redirection, so the operator and its target
    #    were dropped and `bash <<< "…"` collapsed to a bare `bash`, which this function allows.
    if unverified_stdin:
        return False, f"shell interpreter '{prog}' runs unverifiable stdin -> fail-closed"
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
        script = _prog_name(a)
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

    # Token-based denylist. The denied program must be this sub-command's program, and the
    # remaining words must appear IN ORDER among its arguments — not as an exact prefix, which
    # `git -C /tmp/repo push` walked straight past by putting an option in between.
    # Accepted over-block, stated rather than hidden: `git commit -m push` also matches, because
    # after quote removal the message IS the token `push`. Refusing too much is loud; refusing too
    # little is what O-25 was.
    for toks_raw, _piped, _stdin in subs:
        toks = [t for t in toks_raw if not _is_assignment(t)]
        if not toks:
            continue
        prog = _prog_name(toks[0])
        rest = [_fold(t) for t in toks[1:]]
        for entry in deny:
            dt = entry.split()
            if not dt or _prog_name(dt[0]) != prog:
                continue
            wanted, k = [_fold(x) for x in dt[1:]], 0
            for tok in rest:
                if k < len(wanted) and tok == wanted[k]:
                    k += 1
            if k == len(wanted):
                return False, f"denied invocation: {' '.join(dt)}"

    # allowlist: every invoked program must be explicitly allowed
    if allow:
        allow = {_prog_name(a) for a in allow}
        for toks_raw, piped, stdin_script in subs:
            toks = [t for t in toks_raw if not _is_assignment(t)]
            if not toks:
                continue
            name = _prog_name(toks[0])
            if name not in allow:
                return False, f"program '{name}' not in the allowlist"
            # an allowlisted interpreter must not become an allowlist bypass (see module docstring)
            if name in _SHELL_INTERPRETERS:
                ok, reason = _check_interpreter(toks, piped or stdin_script, allow, deny)
                if not ok:
                    return False, reason
        return True, "all invoked programs are allowlisted"

    return True, "no denylist match (no allowlist configured)"
