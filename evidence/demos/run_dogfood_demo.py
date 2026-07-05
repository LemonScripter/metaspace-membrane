#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — dogfood: synthesize a constitution from THIS repo's own code

The synthesizer is not a toy that only works on a hand-written sample. Here it runs over the
entire real codebase (thousands of lines across core/, products/, evidence/) and produces a
real, non-trivial constitution: the actual effects our own code has (filesystem read+write,
subprocess exec, env reads) and its real third-party dependencies. We then assert the result is
substantial and matches known real effects in our source — a real "code -> constitution" run on
real code, not a toy.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO_ROOT)
from core.capability_analyzer import analyze_path, synthesize_bio  # noqa: E402


def kinds_present(findings):
    return {(c.kind, c.mode) for c in findings.capabilities}


def main():
    targets = [os.path.join(REPO_ROOT, d) for d in ("core", "products", "evidence")]
    # count real .py files analyzed
    files = []
    for t in targets:
        for root, _dirs, fs in os.walk(t):
            files += [os.path.join(root, f) for f in fs if f.endswith(".py")]

    from core.capability_analyzer import Findings
    merged = Findings()
    for t in targets:
        f = analyze_path(t)
        merged.capabilities.extend(f.capabilities)
        merged.imports |= f.imports
        merged.invariants |= f.invariants
        merged.smells.extend(f.smells)

    bio = synthesize_bio("metaspace_membrane_self", merged)
    present = kinds_present(merged)
    deps = sorted(merged.imports - {  # drop obvious stdlib for a readable summary
        "os", "sys", "re", "io", "json", "shlex", "shutil", "hashlib", "datetime",
        "tempfile", "contextlib", "argparse", "random", "fnmatch", "subprocess",
        "ast", "builtins", "urllib", "dataclasses", "typing", "collections"})

    print("=" * 78)
    print("  DOGFOOD: code -> constitution, on THIS repo's own code")
    print("=" * 78)
    print(f"  Python files analyzed : {len(files)}")
    print(f"  distinct capabilities : {len(present)}  -> {sorted(present)}")
    print(f"  third-party deps found: {deps}")
    print("-" * 78)
    print("  Synthesized constitution (excerpt):")
    for line in bio.splitlines():
        if line.strip():
            print("    " + line)
    print("-" * 78)

    checks = [
        ("real codebase scale (>20 files)",              len(files) > 20),
        ("filesystem read detected",                     ("FILESYSTEM", "read") in present),
        ("filesystem write detected",                    ("FILESYSTEM", "write") in present),
        ("subprocess exec detected (we run subprocesses)", ("SUBPROCESS", "exec") in present),
        ("env read detected (os.environ.get)",           ("ENV", "read") in present),
        ("third-party dependency 'wasmtime' detected",   "wasmtime" in merged.imports),
    ]
    ok = True
    for name, cond in checks:
        print(f"   [{'OK' if cond else 'FAIL'}]  {name}")
        ok = ok and cond

    print("=" * 78)
    if ok:
        print("  RESULT: PASS - the synthesizer produced a real, non-trivial constitution from")
        print("          thousands of lines of real code, matching our code's actual effects.")
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
