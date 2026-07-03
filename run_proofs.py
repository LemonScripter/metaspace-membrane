#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — reproducible proof runner.

Runs every membrane proof and reports PASS/FAIL. This is the evidence: no hosted CI
required — clone the repo and run one command.

    pip install wasmtime
    python run_proofs.py          # exit 0 if all proofs pass
"""

import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

PROOFS = [
    ("App membrane - WebAssembly hard proof",  "products/app_membrane/run_wasm_demo.py"),
    ("App membrane - unbypassability proof",   "products/app_membrane/bypass_proof.py"),
    ("App membrane - WASI real-program proof", "products/app_membrane/wasi/run_wasi_demo.py"),
    ("Knowledge membrane",                     "evidence/demos/run_knowledge_demo.py"),
    ("Agent membrane",                         "products/ai_membrane/test_hook.py"),
]


def main():
    try:
        import wasmtime  # noqa: F401
    except ImportError:
        print("Missing dependency 'wasmtime'. Install it first:  pip install wasmtime")
        return 2

    print("=" * 60)
    print("  MetaSpace Membrane — reproducible proofs")
    print("=" * 60)
    results = []
    for name, rel in PROOFS:
        p = subprocess.run([sys.executable, os.path.join(HERE, rel)],
                           capture_output=True, text=True)
        ok = (p.returncode == 0)
        results.append((name, ok))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            tail = (p.stdout or "")[-600:] + (p.stderr or "")[-600:]
            print("  ---- output ----")
            for line in tail.splitlines():
                print("  " + line)
            print("  ----------------")
    print("-" * 60)
    passed = sum(1 for _, ok in results if ok)
    all_ok = (passed == len(results))
    print(f"  {passed}/{len(results)} proofs passed")
    print("  RESULT:", "ALL PROOFS PASS" if all_ok else "SOME PROOFS FAILED")
    print("=" * 60)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
