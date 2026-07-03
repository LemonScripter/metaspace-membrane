#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — ratification gate

Closes the provenance chain: in production, only a RATIFIED constitution may run. A
SYNTHESIZED (not yet reviewed) or TAMPERED (edited after ratification) constitution is
refused — fail-closed. A policy becomes enforceable only after a human ratifies it, and it
cannot be broadened afterwards without detection.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from core.provenance import verify, badge  # noqa: E402


class UnratifiedConstitution(Exception):
    """Refused to run: the constitution is not RATIFIED (production gate)."""


def gate(bio_text: str, require_ratified: bool = True) -> str:
    """Return the provenance status. If require_ratified and the status is not RATIFIED,
    raise UnratifiedConstitution (fail-closed) — SYNTHESIZED / TAMPERED must not run."""
    status = verify(bio_text)
    if require_ratified and status != "RATIFIED":
        raise UnratifiedConstitution(
            f"refused: constitution is {badge(status)}, not RATIFIED (production gate)")
    return status


def load_gated(bio_path: str, require_ratified: bool = True):
    """Read a .bio file and apply the ratification gate. -> (bio_text, status)."""
    with open(bio_path, encoding="utf-8") as fh:
        text = fh.read()
    return text, gate(text, require_ratified=require_ratified)
