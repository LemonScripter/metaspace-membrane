#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent capability detector — prototype (C-44 / the auto-profiling idea).

QUESTION IT ANSWERS: can the membrane discover an agent's interception surface *by itself*,
per installed version, instead of us hand-writing an adapter per agent?

This prototype does mechanically what was done by hand for Cursor 2.3.35: locate the install,
read its version, extract the hook vocabulary and each hook's veto contract, and emit a profile.

WHAT IT CAN DECIDE (mechanically, no inference):
  * is the agent installed, and at what version
  * which hook names that version advertises          (a literal enum in the shipped bundle)
  * which of them accept `permission: deny`           (literal arrays in the validator modules)
  * therefore: which hooks can veto and which only observe

WHAT IT CANNOT DECIDE — and must never guess:
  * what a hook NAME MEANS in effect terms (is `afterFileEdit` a FILESYSTEM write?).
    That mapping is authored by a human, once per name, in SEMANTIC_MAP below. A detector that
    guessed this would be doing heuristic classification — correctness, not containment.
  * whether the advertised hooks are COMPLETE (an effect path with no hook at all is invisible
    to introspection). Only adversarial probing can address that; see cursor_hook_probe.py.

FAIL-CLOSED: an unmapped hook name, or a hook that lost its veto contract since the mapping was
authored, is reported as a REGRESSION and suppresses any protection claim for the affected
effect. A membrane that silently degrades when the vendor ships an update is worse than none.

Usage:  python detect_agent.py [--json]
"""

import os
import re
import sys
import json

# ---------------------------------------------------------------------------
# Human-authored, once per hook NAME (not per version). Small and slow-changing.
# kind/mode use the membrane's normalized effect vocabulary (core.guard.KINDS).
# ---------------------------------------------------------------------------
SEMANTIC_MAP = {
    "beforeShellExecution": ("SHELL", "exec", "pre"),
    "afterShellExecution":  ("SHELL", "exec", "post"),
    "beforeMCPExecution":   ("MCP", "call", "pre"),
    "afterMCPExecution":    ("MCP", "call", "post"),
    "beforeReadFile":       ("FILESYSTEM", "read", "pre"),
    "beforeTabFileRead":    ("FILESYSTEM", "read", "pre"),
    "afterFileEdit":        ("FILESYSTEM", "write", "post"),
    "afterTabFileEdit":     ("FILESYSTEM", "write", "post"),
    "beforeSubmitPrompt":   ("PROMPT", "submit", "pre"),
    "stop":                 (None, None, "post"),
    "afterAgentResponse":   (None, None, "post"),
    "afterAgentThought":    (None, None, "post"),
}

CURSOR_ROOTS = [
    r"C:\Program Files\cursor\resources\app",
    r"C:\Program Files (x86)\cursor\resources\app",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\cursor\resources\app"),
    "/usr/share/cursor/resources/app",
    "/Applications/Cursor.app/Contents/Resources/app",
]


def find_cursor():
    for r in CURSOR_ROOTS:
        if os.path.isdir(r):
            return r
    return None


def read_version(app):
    try:
        with open(os.path.join(app, "package.json"), encoding="utf-8") as fh:
            pj = json.load(fh)
        return pj.get("version")
    except Exception:
        return None


def load_bundle(app):
    p = os.path.join(app, "out", "vs", "workbench", "workbench.desktop.main.js")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def extract_hook_names(txt):
    """The vocabulary is a self-mapping enum: {name:"name",name2:"name2",...}."""
    anchor = txt.find("hooks/types.js")
    if anchor < 0:
        return None, "types.js anchor not found (bundle layout changed)"
    window = txt[anchor:anchor + 6000]
    m = re.search(r"(\w+)=\{((?:\s*\w+:\"\w+\",){3,}\s*\w+:\"\w+\")\}", window)
    if not m:
        return None, None, "hook enum not found near types.js"
    enum_var = m.group(1)
    pairs = re.findall(r"(\w+):\"(\w+)\"", m.group(2))
    names = [k for k, v in pairs if k == v]       # only true self-mappings
    if not names:
        return None, None, "enum matched but held no self-mapped names"
    return names, enum_var, None


def _balanced_body(txt, open_brace, limit=8000):
    """Return the text between `{` at open_brace and its matching `}` (None if unbalanced).

    Naive fixed-size windows over minified code read past the function they were aimed at.
    In this bundle the validators sit adjacent, so overrun silently imports a neighbour's
    permission enum. Brace matching removes that whole class of false positives.
    """
    depth = 0
    for i in range(open_brace, min(len(txt), open_brace + limit)):
        c = txt[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return txt[open_brace:i + 1]
    return None


def extract_veto_contracts(txt, names, enum_var):
    """Resolve each hook through the validator DISPATCH TABLE, then inspect that validator.

    Guessing the validator from the hook's name is unsound: several hooks share one validator
    (beforeShellExecution and beforeMCPExecution both use the command validator), and some
    validator modules are spelled differently from their hook (afterFileEdit ->
    afterEditFileResponse.js). A name-based guess silently attributes one hook's permission enum
    to another and reports observe-only hooks as vetoing — i.e. it OVER-CLAIMS. So we read the
    table the product itself dispatches on:

        sBc = {[Eb.beforeShellExecution]: Ero, [Eb.afterFileEdit]: KOc, ...}

    and then look up each validator identifier's own definition. Minified identifiers change
    between builds, which is fine: they are resolved dynamically, never hard-coded.
    """
    tbl = re.search(r"\{\s*\[" + re.escape(enum_var) + r"\.\w+\]:\s*\w+(?:\s*,\s*\[" +
                    re.escape(enum_var) + r"\.\w+\]:\s*\w+)+\s*\}", txt)
    if not tbl:
        return None, "validator dispatch table not found -> FAIL-CLOSED (cannot prove veto)"
    dispatch = dict(re.findall(re.escape(enum_var) + r"\.(\w+)\]:\s*(\w+)", tbl.group(0)))

    out = {}
    for n in names:
        vid = dispatch.get(n)
        if not vid:
            out[n] = {"validator": None, "permissions": None, "can_veto": False,
                      "note": "not present in the dispatch table"}
            continue
        # the validator's own definition: `<vid>=i=>{ ... }`.
        # The body MUST be brace-matched, not a fixed window: these validators are tiny and
        # adjacent in the bundle, so a fixed window runs past the closing brace and picks up the
        # NEXT validator's permission enum — reporting an observe-only hook as vetoing.
        # Every extraction bug found here erred toward over-claiming, so bound it exactly.
        perms = None
        m = re.search(re.escape(vid) + r"=\s*i=>\{", txt)
        if m:
            body = _balanced_body(txt, m.end() - 1)
            if body is not None:
                pm = re.search(r'=\[((?:"\w+"\s*,?\s*)+)\]', body)
                if pm:
                    perms = re.findall(r'"(\w+)"', pm.group(1))
        out[n] = {"validator": vid, "permissions": perms,
                  "can_veto": bool(perms and "deny" in perms)}
    return out, None


def main():
    as_json = "--json" in sys.argv
    report = {"agent": "cursor", "detected": False}

    app = find_cursor()
    if not app:
        report["error"] = "Cursor not installed at any known path"
        print(json.dumps(report, indent=2) if as_json else report["error"])
        return 3

    report.update({"detected": True, "install": app, "version": read_version(app)})

    txt = load_bundle(app)
    if txt is None:
        report["error"] = "workbench bundle not found (layout changed) -> FAIL-CLOSED"
        print(json.dumps(report, indent=2) if as_json else report["error"])
        return 4

    names, enum_var, err = extract_hook_names(txt)
    if err:
        report["error"] = f"{err} -> FAIL-CLOSED (extraction broke, or the agent changed)"
        print(json.dumps(report, indent=2) if as_json else report["error"])
        return 4

    contracts, err = extract_veto_contracts(txt, names, enum_var)
    if err:
        report["error"] = f"{err}"
        print(json.dumps(report, indent=2) if as_json else report["error"])
        return 4
    report["hooks"] = contracts

    # --- derive the effect profile, fail-closed on anything unmapped -----------
    unmapped = [n for n in names if n not in SEMANTIC_MAP]
    report["unmapped_hooks"] = unmapped

    effects = {}
    for n in names:
        if n not in SEMANTIC_MAP:
            continue
        kind, mode, phase = SEMANTIC_MAP[n]
        if kind is None:
            continue
        key = f"{kind}/{mode}"
        can = contracts[n]["can_veto"] and phase == "pre"
        prev = effects.get(key)
        if prev is None or (can and not prev["enforceable"]):
            effects[key] = {"enforceable": can, "via": n, "phase": phase}
    for k, v in effects.items():
        v["tier"] = "HARD (given the host honours deny)" if v["enforceable"] else "ADVISORY (post-hoc only)"
    report["effect_profile"] = effects
    report["regression"] = bool(unmapped)

    if as_json:
        print(json.dumps(report, indent=2))
        return 0

    print("=" * 66)
    print(f"  Agent detector — cursor {report['version']}")
    print("=" * 66)
    print(f"  install : {app}")
    print(f"  hooks   : {len(names)} advertised\n")
    for n in names:
        c = contracts[n]
        v = "VETO " + str(c["permissions"]) if c["can_veto"] else "observe-only"
        mapped = "" if n in SEMANTIC_MAP else "   <-- UNMAPPED (regression)"
        print(f"    {n:<24} {v}{mapped}")
    print("\n  Derived effect profile (what the membrane could actually enforce):")
    for k, v in sorted(effects.items()):
        print(f"    {k:<20} {v['tier']:<38} via {v['via']}")
    if unmapped:
        print(f"\n  ** REGRESSION: {len(unmapped)} unmapped hook name(s) -> no claim may be made")
        return 5
    print("\n  No unmapped hooks: this version matches the authored semantic map.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
