#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — ratify a constitution (SYNTHESIZED -> RATIFIED)

Shows a constitution, then (on confirmation) stamps it RATIFIED with a fingerprint bound to
its enforced policy. Editing the policy afterwards makes it TAMPERED.

    python ratify.py app.constitution.bio            # interactive
    python ratify.py app.constitution.bio --yes       # non-interactive (CI)
    python ratify.py app.constitution.bio --out ratified.bio
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.provenance import verify, ratify, badge, policy_fingerprint  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Ratify a .bio constitution.")
    ap.add_argument("bio", help="the .bio constitution to ratify")
    ap.add_argument("--yes", action="store_true", help="ratify without an interactive prompt")
    ap.add_argument("--out", help="write the ratified constitution here (default: in place)")
    args = ap.parse_args()

    if not os.path.exists(args.bio):
        sys.stderr.write(f"file not found: {args.bio}\n")
        return 2

    with open(args.bio, encoding="utf-8") as fh:
        text = fh.read()

    status = verify(text)
    print(text)
    print("-" * 60)
    print("current status:", badge(status), " policy:", policy_fingerprint(text))

    if status == "RATIFIED":
        print("Already ratified and unchanged. Nothing to do.")
        return 0
    if status == "TAMPERED":
        print("WARNING: an existing ratification stamp does NOT match the current policy.")

    if not args.yes:
        try:
            resp = input("Ratify this constitution? [y/N] ").strip().lower()
        except EOFError:
            resp = "n"
        if resp not in ("y", "yes"):
            print("Aborted.")
            return 1

    ratified = ratify(text)
    out = args.out or args.bio
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(ratified)
    print(badge("RATIFIED"), "->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
