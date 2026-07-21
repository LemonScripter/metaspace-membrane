#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-ENVLESS — the user's configuration survives a host that does not propagate `env` (O-13).

MEASURED PROBLEM: `metaspace install` records the mode and the constitution path in the `env`
block of ~/.claude/settings.json. Claude Code injects those into the hook process. **Cursor
invokes the very same hook and injects nothing** — verified in a real run: `mode_from_env=false`,
`bio_from_env=false`. The hook therefore fell back to its built-in defaults, with two
consequences that are worse than they look:

  * a configured `dryrun` ran as `enforce`. Safe-by-default, but it defeats the observe-first
    rollout (C-35): the user gets hard blocking with no warning session on that host.
  * `METASPACE_SESSION_BIO` never arrived either, so the SHIPPED constitution was used instead
    of the user's — every per-project rule set in `metaspace ui` silently did nothing there.

FIX: mirror the settings to ~/.claude/metaspace/config.json, which every host can read.
Precedence, most specific first: per-project registry -> env (when the host provides it) ->
this user-level file -> built-in default. Claude Code is unaffected because env still wins.

FALSIFIABLE: delete the mirror-write from `metaspace install`, or the file fallback from the
hook, and the env-less legs below fail — the hook reverts to enforcing with the shipped rules.

Run: python evidence/run_envless_config_proof.py     (exit 0 = PASS)
"""

import os
import re
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOOK = os.path.join(REPO, "products", "ai_membrane", "session_guard_hook.py")
sys.path.insert(0, REPO)

failures = []


def check(cond, msg):
    print(("    [ok]   " if cond else "    [FAIL] ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def run_hook(home, project, payload, with_env=None):
    """Drive the real hook. `with_env=None` simulates a host that propagates no configuration."""
    env = dict(os.environ)
    for k in ("METASPACE_MODE", "METASPACE_SESSION_BIO", "METASPACE_PROJECT_ROOT",
              "CLAUDE_PROJECT_DIR"):
        env.pop(k, None)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["METASPACE_PROJECT_ROOT"] = project
    env["METASPACE_SESSION_AUDIT"] = os.path.join(project, ".metaspace", "audit.jsonl")
    if with_env:
        env.update(with_env)
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def last_audit(project):
    path = os.path.join(project, ".metaspace", "audit.jsonl")
    recs = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                recs.append(json.loads(line))
            except Exception:
                pass
    return recs[-1] if recs else {}


def main():
    print("=" * 70)
    print("  P-ENVLESS — configuration survives a host that ignores `env` (O-13)")
    print("=" * 70)

    home = tempfile.mkdtemp(prefix="ms_home_")
    project = tempfile.mkdtemp(prefix="ms_proj_")
    ms_dir = os.path.join(home, ".claude", "metaspace")
    os.makedirs(ms_dir, exist_ok=True)

    # a user constitution that differs visibly from the shipped one: it grants a marker path
    user_bio = os.path.join(ms_dir, "session.constitution.bio")
    marker = os.path.join(project, "user_scope_marker.txt").replace("\\", "/")
    with open(user_bio, "w", encoding="utf-8") as fh:
        fh.write("CELL UserConstitution {\n  CAPABILITIES {\n"
                 f'    FILESYSTEM write "{marker}";\n'
                 '  }\n}\n')

    outside = os.path.join(tempfile.gettempdir(), "ms_envless_outside.txt").replace("\\", "/")
    write_out = {"tool_name": "Write", "tool_input": {"file_path": outside}}
    write_marker = {"tool_name": "Write", "tool_input": {"file_path": marker}}

    # ---------------------------------------------------------- 1. reproduce the O-13 downgrade
    print("\n  1. with no config file and no env, the hook uses its built-in defaults")
    rc, _, _ = run_hook(home, project, write_out)
    a = last_audit(project)
    check(rc == 2, f"out-of-scope write blocked (got exit {rc})")
    check(a.get("mode_src") == "built-in",
          f"mode came from the built-in default (got {a.get('mode_src')!r})")
    check(a.get("eff_mode") == "enforce",
          f"…which is enforce — the O-13 downgrade, reproduced (got {a.get('eff_mode')!r})")

    # ------------------------------------------------------- 2. the mirror restores the config
    print("\n  2. with the user-level mirror on disk, an env-less host honours it")
    from core import project_config
    real_home_ms = project_config.home_ms
    project_config.home_ms = lambda: ms_dir            # point the helper at the temp home
    try:
        project_config.save_defaults(mode="dryrun", bio=user_bio)
    finally:
        project_config.home_ms = real_home_ms
    check(os.path.exists(os.path.join(ms_dir, "config.json")), "config.json written")

    rc2, _, err2 = run_hook(home, project, write_out)
    a2 = last_audit(project)
    check(a2.get("mode_src") == "user-file",
          f"mode now comes from the user file (got {a2.get('mode_src')!r})")
    check(a2.get("eff_mode") == "dryrun",
          f"…and it is the configured dryrun (got {a2.get('eff_mode')!r})")
    check(rc2 == 0 and a2.get("would_block") is True,
          "observe-mode: recorded as would-block, not blocked — C-35 holds on this host too")
    check("DRY-RUN" in err2, "the user is warned loudly instead of being silently blocked")

    # -------------------------------------------- 3. the USER's constitution is the one applied
    print("\n  3. the user's constitution is used, not the shipped one")
    project_config.home_ms = lambda: ms_dir
    try:
        project_config.save_defaults(mode="enforce", bio=user_bio)
    finally:
        project_config.home_ms = real_home_ms
    rc3, _, _ = run_hook(home, project, write_marker)
    a3 = last_audit(project)
    check(rc3 == 0 and a3.get("decision") == "ALLOW",
          "a path granted ONLY by the user's constitution is allowed (shipped rules would deny)")
    rc4, _, _ = run_hook(home, project, write_out)
    check(rc4 == 2, "…while an out-of-scope write is still blocked (no over-permission)")

    # ---------------------------------------------------- 4. env still wins where it is provided
    print("\n  4. a host that DOES propagate env is unaffected (Claude Code)")
    rc5, _, _ = run_hook(home, project, write_out,
                         with_env={"METASPACE_MODE": "dryrun", "METASPACE_SESSION_BIO": user_bio})
    a5 = last_audit(project)
    check(a5.get("mode_src") == "env", f"env takes precedence (got {a5.get('mode_src')!r})")
    check(rc5 == 0 and a5.get("would_block") is True, "env-provided dryrun still observed")

    shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(project, ignore_errors=True)

    print("\n" + "-" * 70)
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} check(s) failed")
        for f in failures:
            print("    -", f)
        return 1
    print("  RESULT: PASS — the user's mode and constitution reach every host, env or not")
    print("-" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
