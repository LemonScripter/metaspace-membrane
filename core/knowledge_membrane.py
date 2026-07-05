#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — Epistemic (KNOWLEDGE) membrane

The third membrane. It does not bound EFFECTS (that is the capability membrane) but
FACTS and knowledge-based actuation. Goal: contain hallucination harm.

HARD tier (here — deterministic, decidable -> verifiable, constant-time in nature):
  1) REFERENTIAL INTEGRITY  — closed-world: you cannot assert a non-existent entity.
  2) SCHEMA / DOMAIN        — enum membership, numeric range, type.
  3) PROVENANCE-LOCKED ACT. — a side-effect is allowed only from a granted source (not
                              from the model's "imagination"); this is the core of the
                              anti-hallucination guarantee.
  4) CITATION OBLIGATION    — every factual assertion requires a known source id (SOURCE).

SOFT tier (NOT decided here, NOT deterministic — the honest boundary):
  semantic faithfulness / entailment (does the text actually follow from the source) ->
  an NLI model. `soft_entailment()` does NOT block it, only flags it as UNVERIFIED.
  We do not pretend it is hard.

Every hard check is set membership / dict lookup / enum / numeric range = deterministic
and decidable -> the membrane's decision is verifiable.
"""

import os
import re
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))


class KnowledgeViolation(Exception):
    """An epistemic violation — a deterministic block (hard tier)."""


# ---------------------------------------------------------------------------
# KNOWLEDGE block parser (in the tolerant style of guard.py)
# ---------------------------------------------------------------------------
def parse_knowledge(bio_text: str):
    spec = {
        "entities": {},     # type -> FROM path
        "fields": {},       # type -> [(field, kind, arg)]
        "actuate": {},      # action -> set(provenance)
        "citation_required": False,
        "sources": set(),
    }
    in_block = False
    for line in bio_text.splitlines():
        s = line.split("#", 1)[0].strip()   # strip comment
        if not in_block:
            if re.search(r"\bKNOWLEDGE\b\s*\{", s):
                in_block = True
            continue
        if s == "}" or s.startswith("}"):
            break
        if not s:
            continue

        m = re.match(r'ENTITY\s+(\w+)\s+FROM\s+"([^"]+)"', s)
        if m:
            spec["entities"][m.group(1)] = m.group(2)
            continue
        m = re.match(r'FIELD\s+(\w+)\.(\w+)\s+IN\s+(.+)', s)
        if m:
            vals = [v.strip() for v in m.group(3).split(",") if v.strip()]
            spec["fields"].setdefault(m.group(1), []).append((m.group(2), "enum", vals))
            continue
        m = re.match(r'FIELD\s+(\w+)\.(\w+)\s+RANGE\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)', s)
        if m:
            lo, hi = float(m.group(3)), float(m.group(4))
            spec["fields"].setdefault(m.group(1), []).append((m.group(2), "range", (lo, hi)))
            continue
        m = re.match(r'FIELD\s+(\w+)\.(\w+)\s+REF\s+(\w+)', s)
        if m:
            spec["fields"].setdefault(m.group(1), []).append((m.group(2), "ref", m.group(3)))
            continue
        m = re.match(r'ACTUATE\s+(\w+)\s+PROVENANCE\s+(.+)', s)
        if m:
            srcs = {v.strip() for v in m.group(2).split(",") if v.strip()}
            spec["actuate"][m.group(1)] = srcs
            continue
        if re.match(r'CITATION\s+REQUIRED', s):
            spec["citation_required"] = True
            continue
        m = re.match(r'SOURCE\s+(\w+)', s)
        if m:
            spec["sources"].add(m.group(1))
            continue
    return spec


# ---------------------------------------------------------------------------
# Epistemic membrane
# ---------------------------------------------------------------------------
class KnowledgeMembrane:
    def __init__(self, bio_path: str, base_dir: str = None, audit_path: str = None,
                 provenance: str = "SYNTHESIZED"):
        self.base_dir = os.path.abspath(base_dir or os.path.dirname(bio_path))
        self.provenance = provenance
        self.audit_path = audit_path or os.path.join(HERE, "knowledge_audit.jsonl")
        with open(bio_path, encoding="utf-8") as fh:
            self.spec = parse_knowledge(fh.read())
        # load the closed-world sets (the basis of referential integrity)
        self.world = {}      # type -> set(ids)
        for etype, rel in self.spec["entities"].items():
            path = rel if os.path.isabs(rel) else os.path.join(self.base_dir, rel)
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.world[etype] = set(data.keys())
        self.decisions = []

    # --- audit ---
    def _log(self, op, target, allow, reason, tier="HARD"):
        rec = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "op": op, "target": target, "tier": tier,
            "decision": "ALLOW" if allow else "DENY",
            "reason": reason, "provenance": self.provenance,
        }
        self.decisions.append(rec)
        with open(self.audit_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _deny(self, op, target, reason):
        self._log(op, target, False, reason)
        raise KnowledgeViolation(f"[EPISTEMIC BLOCK] {op} '{target}' :: {reason}")

    # --- (1)+(2)+(4): factual assertion ---
    def assert_fact(self, etype: str, record: dict, citation: str = None):
        """The app asserts a FACT about an entity. Hard checks."""
        eid = record.get("id")
        # (4) citation obligation
        if self.spec["citation_required"]:
            if not citation:
                self._deny("ASSERT", eid, "citation obligation: missing source (citation)")
            if citation not in self.spec["sources"]:
                self._deny("ASSERT", eid,
                           f"unknown source '{citation}' (allowed: {sorted(self.spec['sources'])})")
        # (1) referential integrity: does the entity exist in the closed world
        world = self.world.get(etype)
        if world is None:
            self._deny("ASSERT", eid, f"unknown entity type '{etype}'")
        if eid not in world:
            self._deny("ASSERT", eid,
                       f"referential integrity: '{eid}' not in the closed-world {etype} set")
        # (2) schema / domain
        for field, kind, arg in self.spec["fields"].get(etype, []):
            if field not in record:
                continue
            val = record[field]
            if kind == "enum" and str(val) not in arg:
                self._deny("ASSERT", eid, f"schema/domain: {etype}.{field}='{val}' not in enum {arg}")
            if kind == "range":
                lo, hi = arg
                if not isinstance(val, (int, float)) or not (lo <= val <= hi):
                    self._deny("ASSERT", eid, f"schema/domain: {etype}.{field}={val} outside range [{lo},{hi}]")
            if kind == "ref":
                refworld = self.world.get(arg, set())
                if val not in refworld:
                    self._deny("ASSERT", eid, f"referential integrity: {etype}.{field}='{val}' is not an existing {arg}")
        self._log("ASSERT", eid, True, "grounded: closed-world + schema + citation OK")
        return True

    # --- (3): provenance-locked actuation ---
    def actuate(self, action: str, args: dict, provenance: str = None):
        """A side-effect (e.g. refund) — allowed ONLY from a granted provenance source."""
        allowed = self.spec["actuate"].get(action)
        if allowed is None:
            self._deny("ACTUATE", action, "unknown actuation (deny-by-default)")
        if provenance not in allowed:
            self._deny("ACTUATE", action,
                       f"provenance-locked: source '{provenance}' not allowed (allowed: {sorted(allowed)})")
        # if args reference entities, those must also be closed-world
        for k, v in (args or {}).items():
            if k in self.world and v not in self.world[k]:
                self._deny("ACTUATE", action, f"referential integrity: {k}='{v}' does not exist")
        self._log("ACTUATE", action, True, f"provenance OK ({provenance})")
        return True

    # --- SOFT tier: NOT deterministic, does NOT block ---
    def soft_entailment(self, claim: str, sources, backend: str = "heuristic"):
        """Semantic faithfulness (entailment). NOT decidable deterministically -> not enforced,
        only flagged. Backends: 'heuristic' (dependency-free) or 'claude' (LLM judge). See
        core/entailment.py. This method NEVER blocks; the hard tier is what enforces."""
        import sys as _sys
        _root = os.path.dirname(HERE)
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from core.entailment import check_entailment
        v = check_entailment(claim, sources, backend=backend)
        self._log("ENTAIL", claim[:40], True,
                  f"ADVISORY FLAG (not enforced) [{v.backend}] {v.verdict}: {v.note}", tier="SOFT")
        return {"verdict": v.verdict, "score": v.score, "backend": v.backend,
                "hard": False, "note": v.note}
