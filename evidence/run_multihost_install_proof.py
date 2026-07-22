#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-INSTALL-HOSTS — installing into a second host is safe, merged, and reversible.

Writing into somebody's editor configuration is the most destructive thing this tool does, so
the properties below matter more than the feature itself. Everything here runs against a
throwaway HOME; no real configuration is touched.

  * NON-CLOBBERING — unrelated settings and third-party hooks survive untouched. A membrane that
    eats a user's config to protect them has not helped.
  * BACKED UP — a `.metaspace.bak` is written before the first modification, so a bad merge is
    recoverable without git.
  * IDEMPOTENT — installing twice leaves one entry, not two.
  * REFUSES rather than guesses — a host whose config location is unknown (Antigravity: a Go
    binary whose string table cannot be read statically) is declined with a reason. Writing a
    file nothing reads would look like success and protect nothing.
  * FAILS SAFE on damage — malformed JSON is reported, never overwritten.

FALSIFIABLE: drop the merge and leg 1 fails; drop the backup and leg 2 fails; drop the
`installable()` guard and Antigravity is silently "installed" into a path no host reads.

Run: python evidence/run_multihost_install_proof.py     (exit 0 = PASS)
"""

import os
import sys
import json
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

failures = []


def check(cond, msg):
    print(("    [ok]   " if cond else "    [FAIL] ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def main():
    print("=" * 72)
    print("  P-INSTALL-HOSTS — second-host install is safe, merged and reversible")
    print("=" * 72)

    import cli
    from core import hosts

    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    real_expand = os.path.expanduser
    os.path.expanduser = lambda p: p.replace("~", home, 1) if p.startswith("~") else real_expand(p)
    try:
        cfg = os.path.join(home, ".gemini", "settings.json")
        os.makedirs(os.path.dirname(cfg), exist_ok=True)

        # a realistic pre-existing config: unrelated settings AND somebody else's hook
        original = {
            "theme": "dark",
            "gcp": {"project": "someones-project"},
            "hooks": {
                "BeforeTool": [
                    {"matcher": "run_shell_command",
                     "hooks": [{"type": "command", "command": "python other_tool.py"}]}
                ],
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo hi"}]}
                ],
            },
        }
        with open(cfg, "w", encoding="utf-8") as fh:
            json.dump(original, fh, indent=2)

        hookpath = os.path.join(REPO, "products", "ai_membrane", "session_guard_hook.py")

        # ------------------------------------------------------------- 0. dry-run touches nothing
        print("\n  0. --dry-run reports without writing")
        before = open(cfg, encoding="utf-8").read()
        ok, msg = cli._install_host("gemini-cli", hookpath, "bio.bio", dry_run=True)
        check(ok and "WOULD write" in msg, "dry-run reports the intended change")
        check(open(cfg, encoding="utf-8").read() == before, "the file is byte-identical after a dry-run")
        check(not os.path.exists(cfg + ".metaspace.bak"), "no backup is created by a dry-run")

        # ------------------------------------- 0b. --dry-run covers the WHOLE command, not just --host
        print("\n  0b. a dry run leaves the PRIMARY host untouched too")
        # Regression guard for a real defect: --dry-run used to gate only the --host section, so
        # `install --host X --dry-run` still performed a real Claude Code install. Because a fresh
        # install resets the mode to dryrun, that could silently downgrade someone who was
        # enforcing. A dry run that writes anything is not a dry run.
        import argparse as _ap
        claude_settings = os.path.join(home, ".claude", "settings.json")
        os.makedirs(os.path.dirname(claude_settings), exist_ok=True)
        pre_existing = {"env": {"METASPACE_MODE": "enforce"}, "hooks": {}}
        with open(claude_settings, "w", encoding="utf-8") as fh:
            json.dump(pre_existing, fh, indent=2)
        ms_marker = os.path.join(home, ".claude", "metaspace")

        args = _ap.Namespace(project=None, force=False, enforce=False,
                             host="gemini-cli", dry_run=True)
        rc = cli.cmd_install(args)
        check(rc == 0, f"dry-run install exits cleanly (got {rc})")
        after = json.load(open(claude_settings, encoding="utf-8"))
        check(after == pre_existing,
              "the primary host's settings.json is byte-identical — mode NOT reset to dryrun")
        check(not os.path.isdir(ms_marker),
              "no ~/.claude/metaspace directory was created by a dry run")

        # --------------------------------------------------------------------- 1. merge, not clobber
        print("\n  1. the install merges and preserves everything else")
        ok, msg = cli._install_host("gemini-cli", hookpath, "bio.bio")
        check(ok, f"install reported success ({msg[:60]}…)")
        got = json.load(open(cfg, encoding="utf-8"))
        check(got.get("theme") == "dark", "an unrelated top-level setting survived")
        check(got.get("gcp", {}).get("project") == "someones-project", "a nested setting survived")
        check(len(got["hooks"]["SessionStart"]) == 1, "an unrelated hook EVENT survived")
        others = [h for h in got["hooks"]["BeforeTool"] if "other_tool.py" in json.dumps(h)]
        check(len(others) == 1, "a third-party hook on the SAME event survived")
        ours = [h for h in got["hooks"]["BeforeTool"] if "session_guard_hook" in json.dumps(h)]
        check(len(ours) == 1, "our hook was added exactly once")

        # ---------------------------------------------------------------- 2. the host's own shape
        print("\n  2. the entry is in Gemini's own dialect, not Claude's")
        entry = ours[0]
        check("BeforeTool" in got["hooks"], "the event is BeforeTool (not PreToolUse)")
        check("run_shell_command" in entry["matcher"] and "write_file" in entry["matcher"],
              f"the matcher uses Gemini's tool names ({entry['matcher']})")
        check("Bash" not in entry["matcher"] and "Write|" not in entry["matcher"],
              "no Claude tool names leaked into the matcher")
        check(entry["hooks"][0]["type"] == "command", "hook type is `command`")

        # -------------------------------------------------------------------------- 3. backup
        print("\n  3. the previous config is recoverable")
        bak = cfg + ".metaspace.bak"
        check(os.path.exists(bak), "a .metaspace.bak was written before the change")
        check(json.load(open(bak, encoding="utf-8")) == original,
              "the backup is the ORIGINAL config, byte-for-byte in content")

        # ----------------------------------------------------------------------- 4. idempotent
        print("\n  4. installing twice does not stack duplicates")
        cli._install_host("gemini-cli", hookpath, "bio.bio")
        got2 = json.load(open(cfg, encoding="utf-8"))
        ours2 = [h for h in got2["hooks"]["BeforeTool"] if "session_guard_hook" in json.dumps(h)]
        check(len(ours2) == 1, f"still exactly one MetaSpace entry ({len(ours2)})")
        check(len([h for h in got2["hooks"]["BeforeTool"] if "other_tool.py" in json.dumps(h)]) == 1,
              "and the third-party hook is still there")

        # ---------------------------------------- 5. a non-merge host is refused by the generic path
        print("\n  5. a host that needs a dedicated install is refused by the generic merger")
        ok3, msg3 = cli._install_host("antigravity", hookpath, "bio.bio")
        check(not ok3, "Antigravity install is refused by the generic config-merger")
        check("dedicated install path" in msg3, f"…with the reason stated ({msg3[:50]}…)")
        check("antigravity" not in hosts.installable(), "it is excluded from `all` installs")
        check(hosts.HOST_PROFILES["antigravity"].get("install") == "special",
              "its profile marks it as a special (non-merge) install, not a guessed config path")
        check(hosts.HOST_PROFILES["antigravity"]["config"] is None,
              "and exposes no generic-merge config path")

        # ------------------------------------------------------ 6. damaged config is not eaten
        print("\n  6. a malformed config is reported, never overwritten")
        with open(cfg, "w", encoding="utf-8") as fh:
            fh.write("{ this is not json")
        ok4, msg4 = cli._install_host("gemini-cli", hookpath, "bio.bio")
        check(not ok4 and "not valid JSON" in msg4, "install refuses and says why")
        check(open(cfg, encoding="utf-8").read() == "{ this is not json",
              "the damaged file is left exactly as it was")

        # --------------------------------- 7. the special (Antigravity) per-workspace install path
        print("\n  7. Antigravity's dedicated install writes a per-workspace hook, non-clobbering")
        agy_proj = os.path.join(home, "agy_ws")
        os.makedirs(os.path.join(agy_proj, ".agents"))
        json.dump({"user-hook": {"enabled": True}},
                  open(os.path.join(agy_proj, ".agents", "hooks.json"), "w"))
        ok5, _msg5 = cli._install_antigravity(agy_proj)
        check(ok5, "the special install succeeds")
        hj = json.load(open(os.path.join(agy_proj, ".agents", "hooks.json"), encoding="utf-8"))
        check("metaspace-warden" in hj and "user-hook" in hj,
              "our hook is added AND the user's other named hook is preserved (non-clobbering)")
        w = hj.get("metaspace-warden", {})
        check(w.get("PreToolUse", [{}])[0].get("matcher") == "*",
              "it is a PreToolUse matcher group in agy's jsonhook schema")
        check("run_adapter.bat" in json.dumps(w), "and points at the PACKAGED adapter bat")
        check(os.path.exists(os.path.join(agy_proj, ".agents", "hooks.json.metaspace.bak")),
              "the previous hooks.json was backed up first")
    finally:
        os.path.expanduser = real_expand
        shutil.rmtree(home, ignore_errors=True)

    print("\n" + "-" * 72)
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} check(s) failed")
        for f in failures:
            print("    -", f)
        return 1
    print("  RESULT: PASS — merged, backed up, idempotent, and honest about what it cannot do")
    print("-" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
