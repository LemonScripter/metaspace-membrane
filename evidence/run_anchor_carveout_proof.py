#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-CARVEOUT — the anchor deny protects a host's control surface, not the user's data (C-66 / O-22).

THE PROBLEM. `core/agent_anchors.py` denies each host's whole config tree (`~/.claude/**` and
friends), and `FILESYSTEM deny` unconditionally overrides write. That is what makes C-33/C-59
hold — but the tree is not only control surface. Claude Code keeps **per-project memory** under
`~/.claude/projects/<slug>/memory/`, which is user content. Measured 2026-07-28: a write there was
DENIED even though the constitution granted it explicitly, so switching a real installation to
`enforce` silently ended cross-session memory. A constitution cannot except itself from a
code-injected deny — by design, since that escape hatch is what C-33 removes — so the fix had to
be in code.

THE SHAPE OF THE FIX, AND WHY THIS SHAPE. The obvious repair is to deny a precise list of config
files instead of the tree. That inverts the risk the wrong way: whatever the list forgets becomes
writable, so a config file added by a future release of a host would be a silent hole. Instead the
tree stays denied in full and a **small, code-defined carve-out** is exempted. Forgetting to
carve something out over-blocks — loud and correctable. Forgetting to *deny* something is
impossible, because denial is the default.

TWO LOCKS, ONE REMOVED. The carve-out only lifts the code-level veto. The constitution must still
grant the path for a write to succeed, so an installation that never grants it is unchanged. The
carve-out list is not readable from a `.bio` and cannot be extended by one — leg 4 pins that,
because a constitution able to declare its own exemptions would reopen C-33 completely.

WHAT IS PROVEN (every leg drives the REAL hook):

  1  the memory directory is writable again when the constitution grants it
  2  the control surface is untouched: settings.json, the membrane's own state, subagent and
     command definitions, the global instruction file, and MCP wiring all stay denied
  3  an unknown, never-listed path inside the anchor is still denied — the default did not flip
  4  a constitution CANNOT create its own carve-out: one that grants `~/.claude/settings.json`,
     and one that writes its own exemption in `.bio` syntax, are both still refused
  5  the carve-out is precise: a sibling of the memory directory is not exempt

FALSIFIABLE: empty `DATA_CARVEOUTS` and leg 1 fails; widen it to `~/.claude/projects/**` and leg 5
fails; let the guard read exemptions from the constitution and leg 4 fails.

Run: python evidence/run_anchor_carveout_proof.py     (exit 0 = PASS)
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


SLUG = "C--Users-someone-Documents-demo"


def bio_for(project, home, extra_grants=""):
    """A constitution that grants the project AND the memory directory, like a real install."""
    return (
        "CELL Demo {\n"
        "  CAPABILITIES {\n"
        f'    FILESYSTEM write "{project}/**";\n'
        f'    FILESYSTEM write "{home}/.claude/projects/{SLUG}/memory/**";\n'
        '    FILESYSTEM read  "**";\n'
        f"{extra_grants}"
        "  }\n"
        "}\n"
    )


def run_hook(home, project, bio_path, target):
    env = dict(os.environ)
    for k in ("METASPACE_SESSION_BIO", "CLAUDE_PROJECT_DIR"):
        env.pop(k, None)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["METASPACE_MODE"] = "enforce"
    env["METASPACE_SESSION_BIO"] = bio_path
    env["METASPACE_PROJECT_ROOT"] = project
    env["METASPACE_SESSION_AUDIT"] = os.path.join(project, "audit.jsonl")
    event = json.dumps({"tool_name": "Write", "tool_input": {"file_path": target}})
    p = subprocess.run([sys.executable, HOOK], input=event, capture_output=True,
                       text=True, env=env)
    return p.returncode


def main():
    print("=" * 76)
    print("  P-CARVEOUT — the anchor deny guards the control surface, not user data (C-66)")
    print("=" * 76)

    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    project = tempfile.mkdtemp(prefix="ms_proj_").replace("\\", "/")
    for sub in (".claude", os.path.join(".claude", "projects", SLUG, "memory")):
        os.makedirs(os.path.join(home, sub), exist_ok=True)

    bio = os.path.join(project, "c.bio").replace("\\", "/")
    with open(bio, "w", encoding="utf-8") as fh:
        fh.write(bio_for(project, home))

    A = f"{home}/.claude"
    MEM = f"{A}/projects/{SLUG}/memory"

    try:
        # -------------------------------------------------- 1. the data is writable again
        print("\n  1. the granted memory directory is writable")
        for path, label in [(f"{MEM}/MEMORY.md", "the memory index"),
                            (f"{MEM}/some-fact.md", "a memory file"),
                            (f"{MEM}/nested/deep.md", "a nested memory file")]:
            rc = run_hook(home, project, bio, path)
            check(rc == 0, f"{label} is allowed (exit {rc})")

        # -------------------------------------------------- 2. the control surface holds
        print("\n  2. everything that can switch the membrane off is still denied")
        control = [
            (f"{A}/settings.json", "the host's settings"),
            (f"{A}/settings.local.json", "…and its local override"),
            (f"{A}/metaspace/session.constitution.bio", "the membrane's own constitution"),
            (f"{A}/metaspace/config.json", "the membrane's own mode file"),
            (f"{A}/CLAUDE.md", "the global instruction file"),
            (f"{A}/agents/evil.md", "a subagent definition"),
            (f"{A}/commands/evil.md", "a slash-command definition"),
            (f"{A}/plugins/x/plugin.json", "a plugin manifest"),
            (f"{home}/.gemini/settings.json", "another host's anchor"),
            (f"{home}/.cursor/hooks.json", "…and another"),
        ]
        for path, label in control:
            rc = run_hook(home, project, bio, path)
            check(rc == 2, f"{label} is denied (exit {rc})")

        # -------------------------------------------------- 3. the default did not flip
        print("\n  3. an unlisted path inside the anchor is still denied by default")
        for path, label in [(f"{A}/something-a-future-release-adds.json", "an unknown config file"),
                            (f"{A}/projects/{SLUG}/transcript.jsonl", "a transcript beside the memory"),
                            (f"{A}/newdir/newfile", "an unknown subtree")]:
            rc = run_hook(home, project, bio, path)
            check(rc == 2, f"{label} is denied (exit {rc})")

        # -------------------------------------------------- 4. a .bio cannot carve its own
        print("\n  4. a constitution cannot grant itself a carve-out (C-33 preserved)")
        greedy = os.path.join(project, "greedy.bio").replace("\\", "/")
        with open(greedy, "w", encoding="utf-8") as fh:
            fh.write(bio_for(project, home,
                             extra_grants=f'    FILESYSTEM write "{A}/**";\n'))
        rc = run_hook(home, project, greedy, f"{A}/settings.json")
        check(rc == 2, f"a constitution granting the whole anchor is still refused (exit {rc})")

        forged = os.path.join(project, "forged.bio").replace("\\", "/")
        with open(forged, "w", encoding="utf-8") as fh:
            fh.write(bio_for(project, home,
                             extra_grants=f'    FILESYSTEM exempt "{A}/**";\n'
                                          f'    FILESYSTEM carveout "{A}/**";\n'))
        rc = run_hook(home, project, forged, f"{A}/settings.json")
        check(rc == 2,
              f"…and inventing an `exempt`/`carveout` rule in the .bio changes nothing (exit {rc})")

        # -------------------------------------------------- 5. the carve-out is precise
        print("\n  5. the carve-out is narrow, not 'anything under projects/'")
        for path, label in [(f"{A}/projects/{SLUG}/memory-notes.md", "a sibling named like memory"),
                            (f"{A}/projects/{SLUG}/settings.json", "a per-project settings file")]:
            rc = run_hook(home, project, bio, path)
            check(rc == 2, f"{label} is denied (exit {rc})")
    finally:
        shutil.rmtree(home, ignore_errors=True)
        shutil.rmtree(project, ignore_errors=True)

    print("\n" + "-" * 76)
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} check(s) failed")
        for f in failures:
            print("    -", f)
        return 1
    print("  RESULT: PASS — user data writable, control surface sealed, default still deny")
    print("-" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
