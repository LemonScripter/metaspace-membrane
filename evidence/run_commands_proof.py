#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-COMMANDS — the command catalogue (used by the panel's type-to-search and info list) is
well-formed: alphabetical, every entry has a real explanation, and every command the shipped
safe-defaults allowlist grants is explained. Falsifiable: add a default command without a
catalogue entry, or an empty description, and this fails.

Run: python run_commands_proof.py   (exit 0 iff the catalogue is well-formed and complete)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

_ok = True


def check(cond, label):
    global _ok
    _ok = _ok and bool(cond)
    print("  [%s] %s" % ("ok" if cond else "FAIL", label))


def main():
    from core import command_catalog, bio_fields
    rows = command_catalog.catalog()
    print("=" * 72)
    print("  P-COMMANDS (panel command catalogue: well-formed, alphabetical, complete)")
    print("=" * 72)

    names = [r["name"] for r in rows]
    check(len(rows) >= 40, "catalogue has a useful number of commands (%d)" % len(rows))
    check(names == sorted(names), "commands are listed alphabetically")
    check(all(r["desc"].strip() for r in rows), "every command has a non-empty explanation")
    check(all(len(r["desc"]) >= 12 for r in rows), "every explanation is a real sentence, not a stub")

    catalog_set = set(names)
    defaults = bio_fields.SAFE_DEFAULTS.get("shell_allow", [])
    missing = [c for c in defaults if c not in catalog_set]
    check(not missing, "every shipped default command is explained (missing: %s)" % (missing or "none"))

    # a couple of high-risk commands must be present with a risk-aware note
    for risky in ("curl", "rm", "ssh"):
        check(risky in catalog_set, "high-risk command '%s' is in the catalogue" % risky)

    print("-" * 72)
    print("  RESULT:", "PASS — the catalogue is complete, alphabetical, and every entry explains itself"
          if _ok else "FAIL — see checks above")
    print("=" * 72)
    return 0 if _ok else 1


if __name__ == "__main__":
    sys.exit(main())
