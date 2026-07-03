#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — Epistemic membrane DEMO

Runs an AI customer-service app's factual assertions and actuations through the membrane.
Claim proven: the HARD tier deterministically blocks hallucination — a non-existent
entity, an out-of-domain value, an uncited assertion, and an ungrounded (LLM-invented)
actuation. The grounded cases pass.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))   # .../metaspace-membrane
sys.path.insert(0, REPO_ROOT)
from core.knowledge_membrane import KnowledgeMembrane, KnowledgeViolation  # noqa: E402

BIO = os.path.join(HERE, "app.knowledge.bio")


def main():
    audit = os.path.join(HERE, "knowledge_audit.jsonl")
    if os.path.exists(audit):
        os.remove(audit)

    m = KnowledgeMembrane(BIO, base_dir=HERE, audit_path=audit)

    # (description, callable, expected_decision, mechanism)
    cases = [
        # --- grounded (ALLOW) ---
        ("real order assertion + citation",
         lambda: m.assert_fact("order", {"id": "O-1001", "status": "shipped", "total": 250, "ref": "P-1"},
                               citation="verified_db"),
         "ALLOW", "grounded"),
        ("refund from the verified DB source",
         lambda: m.actuate("refund", {"order": "O-1001", "amount": 250}, provenance="verified_db"),
         "ALLOW", "provenance OK"),

        # --- hallucination (DENY) ---
        ("invented order (non-existent id)",
         lambda: m.assert_fact("order", {"id": "O-9999", "status": "shipped", "total": 10}, citation="verified_db"),
         "DENY", "1) referential integrity"),
        ("out-of-domain / bad enum value",
         lambda: m.assert_fact("order", {"id": "O-1002", "status": "levitating", "total": 999}, citation="verified_db"),
         "DENY", "2) schema/domain (enum)"),
        ("ref to a non-existent product",
         lambda: m.assert_fact("order", {"id": "O-1003", "status": "pending", "total": 4200, "ref": "P-404"}, citation="verified_db"),
         "DENY", "1) ref integrity (second level)"),
        ("uncited factual assertion",
         lambda: m.assert_fact("order", {"id": "O-1001", "status": "shipped", "total": 250}, citation=None),
         "DENY", "4) citation obligation"),
        ("LLM-invented refund (no provenance)",
         lambda: m.actuate("refund", {"order": "O-1001", "amount": 999999}, provenance="llm_generated"),
         "DENY", "3) provenance-locked actuation"),
    ]

    print("=" * 72)
    print("  EPISTEMIC (KNOWLEDGE) MEMBRANE DEMO  — hard tier")
    print("=" * 72)
    print("  Constitution:", os.path.basename(BIO), " closed-world:", {k: len(v) for k, v in m.world.items()})
    print("-" * 72)

    ok = True
    allow = deny = 0
    for desc, fn, expected, mech in cases:
        try:
            fn()
            got = "ALLOW"
        except KnowledgeViolation:
            got = "DENY"
        match = (got == expected)
        ok = ok and match
        allow += (got == "ALLOW")
        deny += (got == "DENY")
        flag = "OK " if match else "!! "
        print("  [%s%s] %-42s <%s>" % (flag, got.ljust(5), desc, mech))
    print("-" * 72)
    print("  total: %d  (ALLOW=%d, DENY=%d)  — want: ALLOW=2, DENY=5" % (len(cases), allow, deny))

    # soft tier: honest flag, does NOT block
    soft = m.soft_entailment("The order arrived differently", "source text...")
    print("-" * 72)
    print("  SOFT tier (NLI):", soft["verdict"], "-", soft["note"])

    print("=" * 72)
    if ok and allow == 2 and deny == 5:
        print("  RESULT: PASS — the hard tier deterministically enforces all 4 mechanisms;")
        print("          the hallucination cases are blocked.")
        print("  audit:", os.path.relpath(audit, HERE))
        return 0
    print("  RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
