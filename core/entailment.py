#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — Epistemic SOFT tier (semantic faithfulness / entailment)

This is the SOFT tier of the epistemic membrane. Per the honest hard/soft split, semantic
faithfulness is NOT deterministic and this tier does NOT block — it FLAGS whether a claim is
supported by its cited sources. The HARD tier (knowledge_membrane) enforces; this tier informs.

Pluggable backends:
  * "heuristic" — dependency-free, runnable anywhere. A WEAK signal: it checks whether the
                  claim's figures and key terms appear in the sources. Deterministic for the
                  number check (an invented figure is a reliable hallucination signal), weak
                  for general meaning. Good enough to demonstrate the tier without a model.
  * "claude"    — an LLM judge (Anthropic API) for real semantic entailment. The recommended
                  production backend. Non-deterministic. Needs ANTHROPIC_API_KEY + network and
                  the `anthropic` package; returns UNVERIFIED gracefully if unavailable.

Neither backend is authoritative enough to enforce actuation — that is the hard tier's job.
"""

import os
import re
from dataclasses import dataclass


@dataclass
class Verdict:
    verdict: str        # SUPPORTED / UNSUPPORTED / UNVERIFIED
    score: float        # 0..1 support estimate
    backend: str
    hard: bool = False  # always False — the soft tier never enforces
    note: str = ""


def _tokens(text: str):
    return set(re.findall(r"[a-zA-Z]{4,}", text.lower()))


def _numbers(text: str):
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def _as_text(sources) -> str:
    if isinstance(sources, (list, tuple)):
        return "\n".join(str(s) for s in sources)
    return str(sources)


def heuristic_entailment(claim: str, sources) -> Verdict:
    src = _as_text(sources)
    ctoks, stoks = _tokens(claim), _tokens(src)
    cnums, snums = _numbers(claim), _numbers(src)
    overlap = (len(ctoks & stoks) / len(ctoks)) if ctoks else 1.0
    invented = cnums - snums          # figures in the claim not present in the sources
    if invented:
        return Verdict("UNSUPPORTED", round(overlap, 2), "heuristic", False,
                       f"claim contains figures absent from the sources: {sorted(invented)}")
    if overlap >= 0.6:
        return Verdict("SUPPORTED", round(overlap, 2), "heuristic", False,
                       "key terms present in the sources (weak lexical signal)")
    return Verdict("UNVERIFIED", round(overlap, 2), "heuristic", False,
                   "insufficient lexical support; use the 'claude' backend for real entailment")


def claude_entailment(claim: str, sources, model: str = "claude-sonnet-5") -> Verdict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return Verdict("UNVERIFIED", 0.0, "claude", False,
                       "ANTHROPIC_API_KEY not set; the LLM judge cannot run")
    try:
        import anthropic
    except ImportError:
        return Verdict("UNVERIFIED", 0.0, "claude", False,
                       "the 'anthropic' package is not installed (pip install anthropic)")
    src = _as_text(sources)
    client = anthropic.Anthropic(api_key=key)
    prompt = (f"Sources:\n{src}\n\nClaim: {claim}\n\n"
              "Is the claim fully supported by the sources? Reply with exactly one word: "
              "SUPPORTED, UNSUPPORTED, or UNVERIFIED.")
    msg = client.messages.create(model=model, max_tokens=8,
                                 messages=[{"role": "user", "content": prompt}])
    verdict = (msg.content[0].text or "").strip().upper().split()[:1]
    verdict = verdict[0] if verdict else "UNVERIFIED"
    if verdict not in ("SUPPORTED", "UNSUPPORTED", "UNVERIFIED"):
        verdict = "UNVERIFIED"
    return Verdict(verdict, 1.0 if verdict == "SUPPORTED" else 0.0, "claude", False,
                   f"LLM judge ({model}, non-deterministic)")


BACKENDS = {"heuristic": heuristic_entailment, "claude": claude_entailment}


def check_entailment(claim: str, sources, backend: str = "heuristic") -> Verdict:
    """Flag whether `claim` is supported by `sources`. Never blocks (soft tier)."""
    fn = BACKENDS.get(backend, heuristic_entailment)
    return fn(claim, sources)
