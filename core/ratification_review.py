#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — ratification review (the cognitive brake)

The dry-run learning mode fixes false positives, but it opens a new risk: a capability the
dry-run learned could be a disguised, malicious one that a fatigued human rubber-stamps. This
module makes that abuse structurally hard.

  * Every capability carries an ORIGIN: `static` (name-based analysis) or `dry-run` (observed at
    runtime). Dry-run-added capabilities are PROVISIONAL.
  * A provisional capability is ratifiable only if it has an explicit JUSTIFICATION — a
    human-readable reason (author- or AI-authored). Ratification is REFUSED (fail-closed) while
    any provisional capability lacks one. This is the read-gate: you cannot bulk-approve a
    learned capability without a justification present.

Honest limit: the code enforces the PRESENCE of a justification and a per-item review — it
defeats click-fatigue. It cannot verify the justification is TRUE; an adversarial AI can write a
convincing-but-false reason, so the human judgement on the reason still matters.
"""

import re


class UnjustifiedProvisional(Exception):
    """Ratification refused: a provisional (dry-run) capability has no justification."""


def _capabilities_block(bio_text: str):
    lines, inside = [], False
    for line in bio_text.splitlines():
        if not inside:
            if re.search(r"\bCAPABILITIES\b\s*\{", line):
                inside = True
            continue
        if "}" in line:
            break
        lines.append(line)
    return lines


def parse_capabilities_with_origin(bio_text: str):
    caps = []
    for line in _capabilities_block(bio_text):
        m = re.match(r"\s*([A-Z_]+)\s+([a-z0-9_]+)", line)
        if not m:
            continue
        kind, mode = m.group(1), m.group(2)
        scopes = re.findall(r'"([^"]*)"', line)
        om = re.search(r"#.*\borigin:([\w-]+)", line)
        origin = om.group(1) if om else "static"
        for s in (scopes or [None]):
            caps.append({"kind": kind, "mode": mode, "scope": s, "origin": origin})
    return caps


def parse_justifications(bio_text: str):
    return {t: j for t, j in re.findall(r'JUSTIFY\s+"([^"]*)"\s+"([^"]*)"', bio_text)}


def review(bio_text: str):
    caps = parse_capabilities_with_origin(bio_text)
    just = parse_justifications(bio_text)
    for c in caps:
        c["provisional"] = (c["origin"] == "dry-run")
        c["justification"] = just.get(c["scope"]) if c["provisional"] else None
        c["justified"] = (not c["provisional"]) or (c["justification"] is not None)
    provisional = [c for c in caps if c["provisional"]]
    unjustified = [c for c in provisional if not c["justified"]]
    return {"capabilities": caps, "provisional": provisional, "unjustified": unjustified}


def assert_ratifiable(bio_text: str):
    """Raise UnjustifiedProvisional if any provisional capability lacks a justification."""
    r = review(bio_text)
    if r["unjustified"]:
        names = ", ".join(f"{c['kind']}/{c['mode']} {c['scope']!r}" for c in r["unjustified"])
        raise UnjustifiedProvisional(
            "cannot ratify: provisional (dry-run) capabilities need a JUSTIFY reason: " + names)
    return r
