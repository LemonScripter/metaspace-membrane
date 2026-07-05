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
    ("App membrane - REAL app (real work + containment)", "products/app_membrane/run_real_app_demo.py"),
    ("Synthesis closed loop (code->bio->enforce)", "evidence/demos/run_synth_demo.py"),
    ("Ratification (content-bound provenance)", "evidence/demos/run_ratify_demo.py"),
    ("Ratification gate (only RATIFIED runs)",  "evidence/demos/run_gate_demo.py"),
    ("Dry-run learning mode (false-positive fix)", "evidence/demos/run_dryrun_demo.py"),
    ("Ratification review (cognitive brake)",   "evidence/demos/run_ratification_review_demo.py"),
    ("Knowledge membrane (hard tier)",         "evidence/demos/run_knowledge_demo.py"),
    ("Epistemic soft tier (entailment flag)",  "evidence/demos/run_entailment_demo.py"),
    ("Agent membrane",                         "products/ai_membrane/test_hook.py"),
    ("Structural shell policy (allowlist)",    "products/ai_membrane/test_shell_policy.py"),
    ("Threat-model matrix (honest coverage)",  "evidence/demos/run_threat_matrix_demo.py"),
    ("Self-falsification (anti-slop audit)",   "evidence/run_falsification.py"),
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
