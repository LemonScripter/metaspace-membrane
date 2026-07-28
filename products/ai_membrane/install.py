#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — Agent membrane one-click installer (Product B)

Installs the PreToolUse session membrane into a target project's Claude Code config:
  * writes/merges <project>/.claude/settings.json with the PreToolUse hook,
  * copies an editable session.constitution.bio into <project>/.claude/metaspace/,
  * points the hook at this repo's session_guard_hook.py and sets the project root.

Usage:
    python install.py [<project_dir>]     (default: current directory)

After installing, RESTART the Claude Code session (project hooks load at start), then run
/hooks to confirm the membrane is active. Removing the hook block from settings.json fully
reverts it.
"""

import os
import sys
import json
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "session_guard_hook.py")
BIO_TEMPLATE = os.path.join(HERE, "session.constitution.bio")


def main():
    project = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
    project_fw = project.replace("\\", "/")
    claude_dir = os.path.join(project, ".claude")
    ms_dir = os.path.join(claude_dir, "metaspace")
    os.makedirs(ms_dir, exist_ok=True)

    # 1) editable constitution copy
    bio_dest = os.path.join(ms_dir, "session.constitution.bio")
    shutil.copyfile(BIO_TEMPLATE, bio_dest)

    # 2) merge settings.json
    settings_path = os.path.join(claude_dir, "settings.json")
    settings = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, encoding="utf-8") as fh:
                settings = json.load(fh)
        except Exception:
            print("! existing settings.json is not valid JSON; aborting to avoid clobbering it")
            return 1

    settings.setdefault("env", {})
    settings["env"]["METASPACE_PROJECT_ROOT"] = project_fw
    settings["env"]["METASPACE_SESSION_BIO"] = bio_dest.replace("\\", "/")

    hook_entry = {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit|Read|Bash|PowerShell|WebFetch",
        "hooks": [{
            "type": "command",
            "command": "python",
            "args": [HOOK.replace("\\", "/")],
            "timeout": 30,
        }],
    }
    hooks = settings.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    # replace any prior MetaSpace hook (idempotent install)
    pre = [h for h in pre if HOOK.replace("\\", "/") not in json.dumps(h)]
    pre.append(hook_entry)
    hooks["PreToolUse"] = pre

    with open(settings_path, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2)

    print("MetaSpace agent membrane installed.")
    print("  project      :", project_fw)
    print("  settings.json:", settings_path)
    print("  constitution :", bio_dest, "(edit to adjust scope / allowlist)")
    print()
    print("  NEXT: restart the Claude Code session, then run /hooks to confirm it is active.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
