#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — Epistemic SOFT tier demo (semantic faithfulness)

Shows the soft tier flagging whether a claim is supported by its sources — and NEVER blocking
(D-006: the soft tier informs, the hard tier enforces). Uses the dependency-free 'heuristic'
backend so it runs anywhere; the 'claude' backend (LLM judge) is the production path and is
reported as available.

A faithful claim is flagged SUPPORTED; a claim with an invented figure is flagged UNSUPPORTED.
Neither result stops anything — that is the point of the soft/hard split.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO_ROOT)
from core.entailment import check_entailment  # noqa: E402

SOURCES = [
    "Order O-1001 shipped on 2026-06-01 for a total of 250 dollars, product P-1.",
]

CASES = [
    ("faithful claim",     "Order O-1001 shipped, total 250.",            "SUPPORTED"),
    ("hallucinated figure", "Order O-1001 was refunded 9999 dollars.",     "UNSUPPORTED"),
]


def main():
    print("=" * 72)
    print("  EPISTEMIC SOFT TIER DEMO  (semantic faithfulness — informs, never blocks)")
    print("=" * 72)
    print("  Sources:")
    for s in SOURCES:
        print("    -", s)
    print("-" * 72)

    ok = True
    for label, claim, expected in CASES:
        v = check_entailment(claim, SOURCES, backend="heuristic")
        match = (v.verdict == expected)
        ok = ok and match
        flag = "OK " if match else "!! "
        print(f"  [{flag}{v.verdict:<11}] {label}")
        print(f"       claim: {claim}")
        print(f"       note : {v.note}")
        print(f"       (soft tier: hard={v.hard} -> does NOT block regardless of verdict)")
    print("-" * 72)

    # show the production backend is wired (LLM judge); reports gracefully without a key
    prod = check_entailment(CASES[0][1], SOURCES, backend="claude")
    print(f"  Production backend 'claude' (LLM judge): {prod.verdict} — {prod.note}")

    print("=" * 72)
    if ok:
        print("  RESULT: PASS - the soft tier flagged the faithful claim SUPPORTED and the")
        print("          invented figure UNSUPPORTED, without blocking either (D-006).")
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
