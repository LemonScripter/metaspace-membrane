#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-ROADMAP — the claim & roadmap ledger is machine-checked, not maintained by discipline.

`docs/CLAIMS.md` is the single source of truth for what the project claims, plans, and is
blocked by. Its rules ("claim = proof", append-only, a claim may never exceed its TIER) were
prose until now: nothing failed when they were broken. This proof turns them into mechanism.

It is the project's own principle applied reflexively: the membrane denies the agent any effect
it has not been granted; this proof denies the project any claim it has not proven.

INVARIANTS CHECKED (fail-closed — a malformed ledger fails, it does not pass quietly):

  I1  Every [PROVEN] row names at least one proof runner that actually exists in run_proofs.py.
      ([SCOPE-LIMIT] rows are STATED and point at documentation instead — they are exempt.)
  I2  No row is IN-PROGRESS while any of its DEPENDS is not yet PROVEN.
  I3  Every claim blocked by an OPEN obstacle is itself marked BLOCKED.
  I4  Every load-bearing public statement traces to a claim ID and does not exceed its TIER.
      *** ENFORCING *** since 2026-07-21. It shipped in observe mode first (mirroring the
      membrane's own dry-run-then-enforce default, C-35), which surfaced 22 untagged paragraphs
      and one stale, factually wrong proof count in README.md. With those fixed and every
      guarantee-bearing paragraph traced, the gate was flipped. Consequence: adding a guarantee
      sentence to README.md without a `<!-- claim: C-nn -->` tag now fails this proof — which is
      the point. Tag it, or add the claim to the ledger first.

  S1  Index table and detail blocks agree (same IDs, same TIER, same STATUS).
  S2  Claim IDs are unique (append-only: an ID is never reused).
  S3  Every HARD claim states a CONDITION — the anti-slop rule, mechanised.
  S4  Every referenced obstacle and dependency exists.

Run: python evidence/run_roadmap_proof.py     (exit 0 = PASS)
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CLAIMS_MD = os.path.join(REPO, "docs", "CLAIMS.md")
RUN_PROOFS = os.path.join(REPO, "run_proofs.py")
README = os.path.join(REPO, "README.md")

VALID_TIER = {"HARD", "COOPERATIVE", "ADVISORY", "N/A", "—"}
VALID_STATUS = {"PROVEN", "STATED", "IN-PROGRESS", "PLANNED", "BLOCKED", "REFUTED", "WONTDO"}
VALID_OBSTACLE_STATUS = {"OPEN", "RESOLVED", "ACCEPTED-LIMIT"}

# Words that mark a load-bearing guarantee statement in public copy (I4, observe mode).
GUARANTEE_WORDS = re.compile(
    r"\b(cannot|can't|unbypassable|impossible|never|guarantee[sd]?|prevents?|"
    r"blocked|unreachable|hard boundary|deny-by-default|proven)\b", re.I)

failures = []
warnings = []


def check(cond, msg):
    if cond:
        print(f"    [ok]   {msg}")
    else:
        print(f"    [FAIL] {msg}")
        failures.append(msg)
    return cond


def warn(msg):
    print(f"    [warn] {msg}")
    warnings.append(msg)


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------
def parse_runners():
    """Proof runner names actually registered in run_proofs.py (basename, no .py)."""
    text = open(RUN_PROOFS, encoding="utf-8").read()
    paths = re.findall(r'"([^"]*\.py)"', text)
    return {os.path.splitext(os.path.basename(p))[0] for p in paths}


def _field(block, name):
    m = re.search(r"\*\*" + name + r":\*\*\s*([^·\n]+)", block)
    return m.group(1).strip() if m else None


def _ids(value, prefix):
    return re.findall(prefix + r"-\d+", value or "")


def parse_claims(text):
    """-> {id: {...}} from the detail blocks."""
    claims = {}
    blocks = re.split(r"\n(?=### C-\d+)", text)
    for b in blocks:
        m = re.match(r"### (C-\d+)\s+—\s+(.*)", b)
        if not m:
            continue
        cid, title = m.group(1), m.group(2).strip()
        tmatch = re.search(r"`\[([A-Z-]+)\]`", b)
        claims[cid] = {
            "title": title,
            "type": tmatch.group(1) if tmatch else None,
            "tier": _field(b, "TIER"),
            "status": _field(b, "STATUS"),
            "proof_line": _field(b, "PROOF") or "",
            "depends": _ids(_field(b, "DEPENDS"), "C"),
            "blocked_by": _ids(_field(b, "BLOCKED-BY"), "O"),
            "has_condition": "**CONDITION" in b,
            "dup": cid in claims,
        }
    return claims


def parse_index(text):
    """-> {id: (tier, status)} from the index table."""
    idx = {}
    for line in text.splitlines():
        m = re.match(r"\|\s*(C-\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|", line)
        if m:
            idx[m.group(1)] = (m.group(3).strip(), m.group(4).strip())
    return idx


def parse_obstacles(text):
    """-> {id: {status, blocks}} from the obstacle register."""
    obs = {}
    for line in text.splitlines():
        m = re.match(r"\|\s*\*\*(O-\d+)\*\*\s*\|", line)
        if not m:
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 5:
            obs[m.group(1)] = {"status": cols[3], "blocks": _ids(cols[4], "C")}
    return obs


# ---------------------------------------------------------------------------
def main():
    print("=" * 68)
    print("  P-ROADMAP — claim & roadmap ledger integrity")
    print("=" * 68)

    for p in (CLAIMS_MD, RUN_PROOFS):
        if not os.path.exists(p):
            print(f"  [FAIL] missing required file: {p}")
            return 1

    text = open(CLAIMS_MD, encoding="utf-8").read()
    runners = parse_runners()
    claims = parse_claims(text)
    index = parse_index(text)
    obstacles = parse_obstacles(text)

    print(f"\n  parsed: {len(claims)} claims, {len(obstacles)} obstacles, "
          f"{len(runners)} registered proof runners\n")
    if not check(len(claims) > 0 and len(obstacles) > 0, "ledger is non-empty (fail-closed)"):
        return 1

    # --- S2: unique ids -----------------------------------------------------
    print("  S2 — claim IDs are unique (append-only, never reused)")
    check(not any(c["dup"] for c in claims.values()), "no duplicate claim ID")

    # --- S1: index vs detail ------------------------------------------------
    print("\n  S1 — index table agrees with the detail blocks")
    check(set(index) == set(claims),
          f"index and detail cover the same IDs (index {len(index)}, detail {len(claims)})")
    for cid in sorted(set(index) & set(claims)):
        it, ist = index[cid]
        d = claims[cid]
        if it != d["tier"] or ist != d["status"]:
            check(False, f"{cid}: index says {it}/{ist}, detail says {d['tier']}/{d['status']}")
    if set(index) == set(claims) and not any(
            index[c][0] != claims[c]["tier"] or index[c][1] != claims[c]["status"]
            for c in claims):
        check(True, "every row's TIER and STATUS match between index and detail")

    # --- vocabulary ---------------------------------------------------------
    print("\n  vocabulary — TIER and STATUS are enumerations, not prose")
    bad_tier = {c: d["tier"] for c, d in claims.items() if d["tier"] not in VALID_TIER}
    bad_status = {c: d["status"] for c, d in claims.items() if d["status"] not in VALID_STATUS}
    check(not bad_tier, f"every TIER is from the enumeration ({bad_tier or 'all valid'})")
    check(not bad_status, f"every STATUS is from the enumeration ({bad_status or 'all valid'})")
    bad_obs = {o: v["status"] for o, v in obstacles.items()
               if v["status"] not in VALID_OBSTACLE_STATUS}
    check(not bad_obs, f"every obstacle status is valid ({bad_obs or 'all valid'})")

    # --- I1: claim = proof --------------------------------------------------
    print("\n  I1 — every [PROVEN] row names a proof that exists in run_proofs.py")
    for cid in sorted(claims):
        d = claims[cid]
        if d["status"] != "PROVEN":
            continue
        named = set(re.findall(r"`([A-Za-z0-9_./]+)`", d["proof_line"]))
        named = {os.path.splitext(os.path.basename(n))[0] for n in named}
        if not (named & runners):
            check(False, f"{cid}: PROOF names no registered runner (found: {sorted(named)})")
    unbacked = [c for c in claims
                if claims[c]["status"] == "PROVEN"
                and not ({os.path.splitext(os.path.basename(n))[0]
                          for n in re.findall(r"`([A-Za-z0-9_./]+)`", claims[c]["proof_line"])}
                         & runners)]
    check(not unbacked, f"all PROVEN claims are backed by a registered runner "
                        f"({len([c for c in claims if claims[c]['status'] == 'PROVEN'])} checked)")

    # STATED rows must NOT pretend to be proven
    print("\n  I1b — [SCOPE-LIMIT] rows are STATED, not PROVEN")
    mislabelled = [c for c, d in claims.items()
                   if d["type"] == "SCOPE-LIMIT" and d["status"] == "PROVEN"]
    check(not mislabelled, f"no scope-limit is labelled PROVEN ({mislabelled or 'none'})")

    # --- S3: HARD requires a stated condition -------------------------------
    print("\n  S3 — every HARD claim states its CONDITION (anti-slop, mechanised)")
    hard = [c for c, d in claims.items() if d["tier"] == "HARD"]
    missing = [c for c in hard if not claims[c]["has_condition"]]
    check(not missing, f"all {len(hard)} HARD claims state a CONDITION ({missing or 'none missing'})")

    # --- S4: referential integrity ------------------------------------------
    print("\n  S4 — every referenced dependency and obstacle exists")
    dangling = []
    for cid, d in claims.items():
        dangling += [f"{cid}->{x}" for x in d["depends"] if x not in claims]
        dangling += [f"{cid}->{x}" for x in d["blocked_by"] if x not in obstacles]
    for oid, o in obstacles.items():
        dangling += [f"{oid}->{x}" for x in o["blocks"] if x not in claims]
    check(not dangling, f"no dangling references ({dangling or 'none'})")

    # --- I2: dependency order -----------------------------------------------
    print("\n  I2 — nothing is IN-PROGRESS on an unproven dependency")
    violations = []
    for cid, d in claims.items():
        if d["status"] == "IN-PROGRESS":
            violations += [f"{cid} depends on {x} ({claims[x]['status']})"
                           for x in d["depends"]
                           if x in claims and claims[x]["status"] != "PROVEN"]
    check(not violations, f"no in-progress claim rests on an unproven one ({violations or 'none'})")

    # --- I3: open obstacles force BLOCKED -----------------------------------
    print("\n  I3 — an OPEN obstacle forces its claims to BLOCKED")
    leaks = []
    for oid, o in obstacles.items():
        if o["status"] != "OPEN":
            continue
        for cid in o["blocks"]:
            if cid in claims and claims[cid]["status"] not in ("BLOCKED", "REFUTED", "WONTDO"):
                leaks.append(f"{cid} is {claims[cid]['status']} but {oid} is OPEN")
    # the reverse direction: a claim citing an open blocker must be BLOCKED
    for cid, d in claims.items():
        for oid in d["blocked_by"]:
            if oid in obstacles and obstacles[oid]["status"] == "OPEN" \
                    and d["status"] not in ("BLOCKED", "REFUTED", "WONTDO"):
                leaks.append(f"{cid} is {d['status']} but cites OPEN {oid}")
    check(not leaks, f"every claim under an open obstacle is BLOCKED ({sorted(set(leaks)) or 'none'})")

    # --- I4: public surface traceability (OBSERVE MODE) ---------------------
    print("\n  I4 — public statements trace to a claim ID  *** ENFORCING ***")
    if os.path.exists(README):
        rtext = open(README, encoding="utf-8").read()
        tagged = set(re.findall(r"<!--\s*claim:\s*(C-\d+)\s*-->", rtext))
        unknown = sorted(tagged - set(claims))
        body = re.sub(r"```.*?```", "", rtext, flags=re.S)      # skip code blocks
        # Attribute at PARAGRAPH granularity: a tag sits at the end of a sentence, which often
        # wraps onto the next line, so a line-level check would report tagged text as untagged.
        paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
        candidates = []
        for p in paragraphs:
            if not GUARANTEE_WORDS.search(p):
                continue
            if re.search(r"<!--\s*claim:\s*C-\d+\s*-->", p):
                continue
            stripped = "\n".join(ln for ln in p.splitlines()
                                 if not re.match(r"\s*!\[", ln))   # images carry no guarantee
            if stripped.strip() and GUARANTEE_WORDS.search(stripped):
                candidates.append(" ".join(stripped.split()))
        print(f"    README: {len(tagged)} tagged reference(s) covering "
              f"{len(set(tagged))} distinct claim(s); "
              f"{len(candidates)} untagged guarantee-bearing paragraph(s)")
        check(not unknown, f"every README claim tag names a real claim ({unknown or 'all valid'})")
        if candidates:
            for ln in candidates[:8]:
                print(f"           · {ln[:110]}")
            if len(candidates) > 8:
                print(f"           · … and {len(candidates) - 8} more")
        check(not candidates,
              f"every guarantee-bearing README paragraph traces to a claim "
              f"({len(candidates)} untagged)")
    else:
        check(False, "README.md exists (I4 cannot be evaluated without it — fail-closed)")

    # --- summary ------------------------------------------------------------
    print("\n" + "-" * 68)
    proven = sum(1 for d in claims.values() if d["status"] == "PROVEN")
    blocked = sum(1 for d in claims.values() if d["status"] == "BLOCKED")
    planned = sum(1 for d in claims.values() if d["status"] == "PLANNED")
    open_obs = sum(1 for o in obstacles.values() if o["status"] == "OPEN")
    print(f"  ledger: {proven} proven · {blocked} blocked · {planned} planned · "
          f"{len(claims)} total   |   obstacles: {open_obs} open of {len(obstacles)}")
    print(f"  warnings (observe-mode, non-fatal): {len(warnings)}")
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} invariant(s) violated")
        for f in failures:
            print(f"    - {f}")
        print("-" * 68)
        return 1
    print("  RESULT: PASS — the ledger is internally consistent and every claim is backed")
    print("-" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
