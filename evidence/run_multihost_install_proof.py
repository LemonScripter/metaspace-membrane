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

        # ------------------------------------------------- 5. refuse to guess an unknown host
        print("\n  5. a host with an unknown config location is refused, not guessed at")
        ok3, msg3 = cli._install_host("antigravity", hookpath, "bio.bio")
        check(not ok3, "Antigravity install is refused")
        check("no known config path" in msg3, f"…with the reason stated ({msg3[:50]}…)")
        check("antigravity" not in hosts.installable(), "it is excluded from `all` installs")
        check(hosts.HOST_PROFILES["antigravity"]["config"] is None,
              "its profile records the path as unknown rather than a guess")

        # ------------------------------------------------------ 6. damaged config is not eaten
        print("\n  6. a malformed config is reported, never overwritten")
        with open(cfg, "w", encoding="utf-8") as fh:
            fh.write("{ this is not json")
        ok4, msg4 = cli._install_host("gemini-cli", hookpath, "bio.bio")
        check(not ok4 and "not valid JSON" in msg4, "install refuses and says why")
        check(open(cfg, encoding="utf-8").read() == "{ this is not json",
              "the damaged file is left exactly as it was")
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
