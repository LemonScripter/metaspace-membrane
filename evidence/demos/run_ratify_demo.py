#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — ratification demo (SYNTHESIZED -> RATIFIED -> TAMPERED)

Ratification is content-bound: the stamp carries a fingerprint of the enforced policy.
  1) A freshly synthesized constitution is SYNTHESIZED (not yet trusted).
  2) After a human ratifies it, it is RATIFIED (bound to its exact policy).
  3) If the policy is edited afterwards (a capability quietly added), it becomes TAMPERED.

You cannot ratify a policy and then broaden it without detection.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO_ROOT)
from core.capability_analyzer import analyze_path, synthesize_bio  # noqa: E402
from core.provenance import verify, ratify, badge, policy_fingerprint  # noqa: E402

APP = os.path.join(HERE, "synth_demo", "sample_app.py")


def main():
    # 1) synthesize -> SYNTHESIZED
    bio = synthesize_bio("sample_app", analyze_path(APP))
    s1 = verify(bio)

    # 2) ratify -> RATIFIED (bound to the policy fingerprint)
    ratified = ratify(bio, when="2026-07-03")
    s2 = verify(ratified)

    # 3) tamper: quietly add an undeclared capability after ratification -> TAMPERED
    tampered = ratified.replace("CAPABILITIES {", "CAPABILITIES {\n    SUBPROCESS exec ;", 1)
    s3 = verify(tampered)

    print("=" * 70)
    print("  RATIFICATION DEMO  (content-bound provenance)")
    print("=" * 70)
    print("  1) freshly synthesized      ->", badge(s1), " policy:", policy_fingerprint(bio))
    print("  2) after human ratifies      ->", badge(s2), " policy:", policy_fingerprint(ratified))
    print("     stamp line:", ratified.splitlines()[0])
    print("  3) SUBPROCESS added afterward ->", badge(s3),
          " (stamp no longer matches the widened policy)")
    print("-" * 70)

    ok = (s1 == "SYNTHESIZED" and s2 == "RATIFIED" and s3 == "TAMPERED")
    print("=" * 70)
    if ok:
        print("  RESULT: PASS - ratification is bound to the policy; a post-ratification")
        print("          widening is detected as TAMPERED, not silently trusted.")
        return 0
    print(f"  RESULT: FAIL (got {s1} / {s2} / {s3})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
