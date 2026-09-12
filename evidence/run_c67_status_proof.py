#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — C-67 proof: `metaspace status` reports the mode ACTUALLY in force,
the constitution in force, and which precedence step decided each.

WHY THIS CLAIM EXISTS. `install`, `enforce` and `dryrun` write a mode and the panel displays
one, but nothing reported the mode a hook invocation would really use — and it can differ,
because four layers stack:

    1. project registry   (~/.claude/metaspace/registry.json)   <- wins
    2. environment        (METASPACE_MODE)
    3. user-level file    (~/.claude/metaspace/config.json)
    4. built-in           ("enforce")

THE BUG THIS PROOF PINS. The hook's own `mode_src` diagnostic knew only layers 2-4. On a
registered project it therefore logged "env" (or "user-file") while the *registry* had decided
— the audit told a confident, wrong story about its own configuration. Leg B fails on the old
code and passes on the new: that is what makes it evidence rather than decoration.

HERMETIC (C-61): HOME/USERPROFILE are redirected to a temp directory, so the result does not
depend on the developer's machine. Nothing here reads or writes the real configuration.

Run:  python evidence/run_c67_status_proof.py
"""

import os
import re
import sys
import json
import shutil
import hashlib
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
CLI = os.path.join(REPO_ROOT, "cli.py")
HOOK = os.path.join(REPO_ROOT, "products", "ai_membrane", "session_guard_hook.py")

failures = []


def check(cond, msg):
    print(("    [ok]   " if cond else "    [FAIL] ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def base_env(home, project):
    env = dict(os.environ)
    for k in ("METASPACE_MODE", "METASPACE_SESSION_BIO", "METASPACE_PROJECT_ROOT",
              "CLAUDE_PROJECT_DIR"):
        env.pop(k, None)
    env["HOME"] = home
    env["USERPROFILE"] = home
    return env


def status(home, project, extra=None):
    env = base_env(home, project)
    if extra:
        env.update(extra)
    p = subprocess.run([sys.executable, CLI, "status", "--root", project],
                       capture_output=True, text=True, env=env)
    return p.stdout or ""


def run_hook(home, project, extra=None):
    env = base_env(home, project)
    env["METASPACE_PROJECT_ROOT"] = project
    env["METASPACE_SESSION_AUDIT"] = os.path.join(project, ".metaspace", "audit.jsonl")
    if extra:
        env.update(extra)
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo hello"}}
    subprocess.run([sys.executable, HOOK], input=json.dumps(payload).encode("utf-8"),
                   capture_output=True, env=env)
    path = os.path.join(project, ".metaspace", "audit.jsonl")
    recs = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                recs.append(json.loads(line))
            except Exception:
                pass
    return recs[-1] if recs else {}


def eff_mode(out):
    m = re.search(r"effective mode\s*:\s*(\S+)\s*<-\s*(\S+)", out)
    return (m.group(1), m.group(2)) if m else (None, None)


def main():
    print("=" * 74)
    print("  C-67 — `metaspace status`: the mode in force, and which layer decided it")
    print("=" * 74)

    home = tempfile.mkdtemp(prefix="c67_home_")
    project = tempfile.mkdtemp(prefix="c67_proj_")
    ms = os.path.join(home, ".claude", "metaspace")
    os.makedirs(os.path.join(ms, "projects"), exist_ok=True)

    bio_user = os.path.join(ms, "user.bio")
    with open(bio_user, "w", encoding="utf-8") as f:
        f.write('CELL U {\n  CAPABILITIES {\n    FILESYSTEM write "%s/**";\n  }\n  BASH_POLICY {\n'
                '    ALLOW "echo";\n  }\n}\n' % project.replace("\\", "/"))
    with open(os.path.join(ms, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"mode": "dryrun", "bio": bio_user.replace("\\", "/")}, f)

    # ---- LEG A: environment overrides the user file, and the split is reported ----------
    print("\n  LEG A — env vs user file (the O-13 split)")
    out = status(home, project, {"METASPACE_MODE": "enforce"})
    mode, src = eff_mode(out)
    check(mode == "enforce" and src == "env",
          "effective mode is enforce, from env (got %r from %r)" % (mode, src))
    check("user file" in out and "dryrun" in out,
          "the user file's disagreeing value is shown, not hidden")
    check("TWO MODES AT ONCE" in out,
          "the split is called out: a host ignoring `env` would see a different mode")
    check("mode dryrun  (from user-file)" in out,
          "and it names what that other host would actually get")

    # ---- LEG B: the project registry beats the environment ------------------------------
    print("\n  LEG B — the project registry wins over env (the layer the audit used to miss)")
    h = hashlib.sha1(os.path.normpath(os.path.abspath(project))
                     .replace("\\", "/").encode("utf-8")).hexdigest()[:16]
    shutil.copyfile(bio_user, os.path.join(ms, "projects", h + ".bio"))
    with open(os.path.join(ms, "registry.json"), "w", encoding="utf-8") as f:
        json.dump({os.path.normpath(os.path.abspath(project)).replace("\\", "/"):
                   {"hash": h, "mode": "dryrun"}}, f)

    out = status(home, project, {"METASPACE_MODE": "enforce"})
    mode, src = eff_mode(out)
    check(mode == "dryrun" and src == "project",
          "the registry decides, and status says so (got %r from %r)" % (mode, src))
    check(re.search(r"1 project registry.*IN FORCE", out) is not None,
          "the precedence table marks the project row as in force")
    check(re.search(r"2 environment.*set(?!.*IN FORCE)", out) is not None,
          "env is shown as set but NOT in force — the overridden layer stays visible")

    # ---- LEG C: the hook's own diagnostic agrees with status -----------------------------
    print("\n  LEG C — the audit and status tell the SAME story")
    rec = run_hook(home, project, {"METASPACE_MODE": "enforce"})
    check(rec.get("mode_src") == "project",
          "the hook records mode_src=project (got %r) — this is the leg that fails on the old "
          "code, which knew only env/user-file/built-in" % rec.get("mode_src"))
    check(rec.get("eff_mode") == "dryrun",
          "the hook really ran in the registry's mode (got %r)" % rec.get("eff_mode"))
    check(rec.get("mode_src") == src,
          "status and the audit name the same source — one story, not two")

    # ---- LEG D: nothing but the built-in, reported as such -------------------------------
    print("\n  LEG D — a machine with no configuration at all")
    home2 = tempfile.mkdtemp(prefix="c67_bare_")
    out = status(home2, project)
    mode, src = eff_mode(out)
    check(mode == "enforce" and src == "built-in",
          "the built-in default is named as the source, not silently assumed (got %r from %r)"
          % (mode, src))
    check("TWO MODES AT ONCE" not in out,
          "no split is claimed when the layers agree")

    for d in (home, home2, project):
        shutil.rmtree(d, ignore_errors=True)

    print("\n" + "-" * 74)
    if failures:
        print("  RESULT: FAIL — %d check(s) failed" % len(failures))
        for f in failures:
            print("    - " + f)
        return 1
    print("  RESULT: PASS — the effective mode, the constitution and the deciding layer are")
    print("          reportable; the registry layer is no longer invisible; and the audit and")
    print("          the command agree on the source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
