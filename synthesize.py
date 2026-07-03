#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — code -> constitution synthesizer (CLI)

Statically analyzes a Python file or directory, detects its real effects (filesystem,
network, env, subprocess, hardware bus, import-path), and synthesizes a draft `.bio`
constitution with the CAPABILITIES it needs. The output is SYNTHESIZED (not ratified):
a human should review and ratify it. The runtime membrane then enforces deny-by-default.

    python synthesize.py <path> [--out FILE] [--cell NAME]

Honest limit: this is a static, name-based heuristic (it can under-declare on heavy
dynamism). The guarantee is the runtime membrane, not this synthesis.
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.capability_analyzer import analyze_path, synthesize_bio  # noqa: E402


def main():
    ap = argparse.ArgumentParser(
        description="Synthesize a .bio constitution from Python code.")
    ap.add_argument("path", help="a .py file or a directory to analyze")
    ap.add_argument("--out", help="write the constitution to this file (default: stdout only)")
    ap.add_argument("--cell", help="constitution CELL name (default: derived from the path)")
    args = ap.parse_args()

    if not os.path.exists(args.path):
        sys.stderr.write(f"path not found: {args.path}\n")
        return 2

    findings = analyze_path(args.path)
    base = os.path.basename(os.path.abspath(args.path.rstrip("/\\")))
    cell = args.cell or os.path.splitext(base)[0].replace("-", "_")
    bio = synthesize_bio(cell, findings)

    print(bio)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(bio + "\n")
        sys.stderr.write(f"\n[OK] constitution written: {args.out}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
