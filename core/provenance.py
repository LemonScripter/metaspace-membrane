#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — provenance & ratification

A synthesized constitution is SYNTHESIZED (🟡) until a human reviews and ratifies it (🟢).
Ratification is CONTENT-BOUND: the stamp carries a fingerprint of the actual enforced policy
(capabilities + knowledge + bash denylist). If the constitution is edited after ratification
— e.g. a scope is widened or a capability is added — the fingerprint no longer matches and the
status becomes TAMPERED (🔴). You cannot ratify a policy and then quietly broaden it.
"""

import os
import re
import sys
import json
import hashlib
import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from core.guard import parse_capabilities              # noqa: E402
from core.knowledge_membrane import parse_knowledge     # noqa: E402

RATIFIED_RE = re.compile(r'#\s*PROVENANCE:\s*RATIFIED\s+(\S+)\s+policy:([0-9a-f]+)', re.I)

_BADGES = {"RATIFIED": "[GREEN] RATIFIED", "SYNTHESIZED": "[YELLOW] SYNTHESIZED",
           "TAMPERED": "[RED] TAMPERED"}


def badge(status: str) -> str:
    return _BADGES.get(status, status)


def _canon_knowledge(k: dict) -> dict:
    return {
        "entities": dict(sorted(k["entities"].items())),
        "fields": {t: sorted(json.dumps(list(x), default=str) for x in v)
                   for t, v in sorted(k["fields"].items())},
        "actuate": {a: sorted(s) for a, s in sorted(k["actuate"].items())},
        "citation_required": k["citation_required"],
        "sources": sorted(k["sources"]),
    }


def policy_fingerprint(bio_text: str) -> str:
    """A stable 16-hex fingerprint of the ENFORCED policy (not the raw text/comments).

    The bash denylist is read through the shared BASH_POLICY parser, so the fingerprint covers
    what is actually enforced. Before that, a `DENY "…"` written inside a COMMENT counted
    towards the fingerprint even though no membrane ever enforced it — the docstring's promise
    ("not the raw text/comments") was not kept. Constitutions that keep their DENY statements in
    code, which is all of them, fingerprint identically before and after (pinned by P-BASHPARSE).
    """
    caps = sorted([k, m, sorted(s)] for k, m, s in parse_capabilities(bio_text))
    know = _canon_knowledge(parse_knowledge(bio_text))
    from core.bio_policy import parse_bash_denylist
    bash = sorted(parse_bash_denylist(bio_text))
    payload = json.dumps({"cap": caps, "know": know, "bash": bash}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def verify(bio_text: str) -> str:
    """-> 'RATIFIED' (stamp valid), 'TAMPERED' (stamp present, content changed), 'SYNTHESIZED'."""
    m = RATIFIED_RE.search(bio_text)
    if not m:
        return "SYNTHESIZED"
    return "RATIFIED" if m.group(2) == policy_fingerprint(bio_text) else "TAMPERED"


def ratify(bio_text: str, when: str = None) -> str:
    """Return the constitution stamped RATIFIED, bound to its current policy fingerprint."""
    when = when or datetime.date.today().isoformat()
    stamp = f"# PROVENANCE: RATIFIED {when} policy:{policy_fingerprint(bio_text)}"
    kept = [ln for ln in bio_text.splitlines()
            if not re.match(r'\s*#\s*PROVENANCE:', ln, re.I)
            and "provenance: SYNTHESIZED" not in ln]
    return stamp + "\n" + "\n".join(kept).lstrip("\n") + "\n"
