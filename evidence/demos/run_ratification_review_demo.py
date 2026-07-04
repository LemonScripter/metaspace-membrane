#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — ratification review demo (the cognitive brake)

Scenario: the dry-run learned two capabilities and added them as PROVISIONAL. One is a
legitimate, justified write; the other is a disguised network host smuggled in during the
learning phase. Without a justification for the smuggled capability, ratification is REFUSED —
so a fatigued human cannot bulk-approve it. Once a human supplies a justification (having read
it), ratification proceeds.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO_ROOT)
from core.ratification_review import review, assert_ratifiable, UnjustifiedProvisional  # noqa: E402
from core.provenance import ratify, verify  # noqa: E402

BASE = """CELL customer_app {
  CAPABILITIES {
    FILESYSTEM read  "config.json";       # origin:static
    FILESYSTEM write "out/report.log";     # origin:dry-run
    NETWORK    out   "metrics.internal";    # origin:dry-run
  }
  JUSTIFY "out/report.log" "Report filename is built from APP_ENV at runtime; observed writing report.log.";
%s}
"""

BIO_UNJUSTIFIED = BASE % ""    # the smuggled host has NO justification
BIO_JUSTIFIED = BASE % ('  JUSTIFY "metrics.internal" '
                        '"Telemetry endpoint; confirmed with ops, required for the metrics feature.";\n')


def try_ratify(bio):
    try:
        assert_ratifiable(bio)
    except UnjustifiedProvisional as e:
        return "REFUSED", str(e)
    return "RATIFIED (" + verify(ratify(bio)) + ")", None


def main():
    print("=" * 84)
    print("  RATIFICATION REVIEW DEMO  —  provisional (dry-run) capabilities need a justification")
    print("=" * 84)
    r = review(BIO_UNJUSTIFIED)
    print("  Diff view (what the dry-run added is PROVISIONAL and must be justified):")
    print("  %-11s %-7s %-20s %-11s %s" % ("kind", "mode", "scope", "origin", "status"))
    print("  " + "-" * 78)
    for c in r["capabilities"]:
        status = ("justified" if c["justified"] else "!! UNJUSTIFIED") if c["provisional"] else "(static)"
        print("  %-11s %-7s %-20s %-11s %s" %
              (c["kind"], c["mode"], str(c["scope"]), c["origin"], status))
    print("  " + "-" * 78)

    d1, why1 = try_ratify(BIO_UNJUSTIFIED)
    d2, why2 = try_ratify(BIO_JUSTIFIED)
    print("  smuggled host WITHOUT justification -> ratify:", d1)
    if why1:
        print("      reason:", why1)
    print("  after a human supplies a justification -> ratify:", d2)
    print("=" * 84)

    ok = d1.startswith("REFUSED") and d2.startswith("RATIFIED")
    if ok:
        print("  RESULT: PASS - a learned capability cannot be silently ratified; a justification")
        print("          (that a human must supply and read) is required. Click-fatigue is broken.")
        print("  Note: the code enforces the PRESENCE of a justification, not its truth -- an")
        print("        adversarial reason is still a human judgement (honest residual limit).")
        return 0
    print(f"  RESULT: FAIL (unjustified={d1}, justified={d2})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
