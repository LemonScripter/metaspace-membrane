#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-VERSION — the version is consistent across the packaging manifest, the plugin manifest, and
the CLI. A release that bumped one and forgot another would ship an inconsistent version; this
proof fails if `pyproject.toml`, `.claude-plugin/plugin.json`, and `metaspace --version` disagree.

Run: python run_version_proof.py   (exit 0 iff all three agree)
"""

import os
import re
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CLI = os.path.join(REPO, "cli.py")


def pyproject_version():
    text = open(os.path.join(REPO, "pyproject.toml"), encoding="utf-8").read()
    m = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else None


def plugin_version():
    data = json.load(open(os.path.join(REPO, ".claude-plugin", "plugin.json"), encoding="utf-8"))
    return data.get("version")


def cli_version():
    p = subprocess.run([sys.executable, CLI, "--version"], capture_output=True, text=True)
    out = (p.stdout or "").strip() or (p.stderr or "").strip()   # argparse may use either
    m = re.search(r"(\d+\.\d+\.\d+\S*)", out)
    return m.group(1) if m else None


def main():
    py, pl, cl = pyproject_version(), plugin_version(), cli_version()
    print("=" * 60)
    print("  P-VERSION — version parity across manifests + CLI")
    print("=" * 60)
    print("  pyproject.toml      :", py)
    print("  plugin.json         :", pl)
    print("  metaspace --version :", cl)
    print("-" * 60)
    ok = py is not None and py == pl == cl
    print("  RESULT:", "PASS — all three agree" if ok else "FAIL — versions disagree")
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
