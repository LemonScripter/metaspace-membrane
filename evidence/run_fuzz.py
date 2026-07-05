#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — property-based fuzz proof (adversarial coverage)

Hand-picked demos show the membrane blocks the attacks WE thought of. This proof goes wider:
it generates thousands of RANDOM constitutions and RANDOM effect attempts and checks two
properties on every one:

  SECURITY (no oracle needed): a (kind,mode) that the constitution does NOT grant must NEVER be
                               ALLOWed by the guard (deny-by-default is sound).
  CONSISTENCY (vs an independent oracle): the guard's decision must match a separately implemented
                               scope oracle (catches scope/normalisation/glob divergences,
                               path traversal, absolute paths, host and name globs).

A fixed seed keeps it reproducible. Any mismatch fails the proof and prints the counterexample.
"""

import os
import sys
import random
import fnmatch
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, REPO_ROOT)
from core.guard import Guard, ConstitutionViolation  # noqa: E402

BASE = "/proj"   # a fixed virtual base dir so normalisation is comparable
KM = [("FILESYSTEM", "read"), ("FILESYSTEM", "write"), ("NETWORK", "out"),
      ("ENV", "read"), ("SUBPROCESS", "exec")]

SCOPES = {
    "FILESYSTEM": ["data/**", "logs/**", "out/**", "config/*.ini", "src/**", "**"],
    "NETWORK": ["api.example.com", "*.internal", "cdn.*", "*"],
    "ENV": ["APP_*", "HOME", "*"],
    "SUBPROCESS": ["git", "python", "*"],
}
TARGETS = {
    "FILESYSTEM": ["data/a.txt", "logs/x/y.log", "out/r.txt", "config/app.ini", "secret/keys.pem",
                   "../etc/passwd", "data/../../escape", "/abs/system", "src/main.py", "tmp/z"],
    "NETWORK": ["api.example.com", "db.internal", "cdn.acme.net", "evil.com",
                "api.example.com:443", "localhost"],
    "ENV": ["APP_TOKEN", "HOME", "SECRET_KEY", "PATH", "APP_"],
    "SUBPROCESS": ["git", "python", "rm", "curl"],
}


def _norm(p):
    p = p if os.path.isabs(p) else os.path.join(BASE, p)
    return os.path.normpath(p).replace("\\", "/")


def oracle(grants, kind, mode, target):
    """Independent reference decision for (kind,mode,target)."""
    scopes = grants.get((kind, mode))
    if scopes is None:
        return "DENY"
    if not scopes:
        return "ALLOW"
    if any(s in ("*", "**", "/**") for s in scopes):
        return "ALLOW"
    if kind == "FILESYSTEM":
        t = _norm(target)
        return "ALLOW" if any(fnmatch.fnmatch(t, _norm(s)) for s in scopes) else "DENY"
    if kind == "NETWORK":
        h = str(target).split(":")[0]
        return "ALLOW" if any(fnmatch.fnmatch(h, s) for s in scopes) else "DENY"
    return "ALLOW" if any(fnmatch.fnmatch(target, s) for s in scopes) else "DENY"


def build(rng):
    lines, grants = ["CAPABILITIES {"], {}
    for kind, mode in KM:
        if rng.random() < 0.5:
            n = rng.randint(0, 2)
            scopes = [rng.choice(SCOPES[kind]) for _ in range(n)]
            grants[(kind, mode)] = scopes
            q = " ".join('"%s"' % s for s in scopes)
            lines.append("  %s %s %s;" % (kind, mode, q))
    lines.append("}")
    return "\n".join(lines), grants


def guard_decide(bio, kind, mode, target, audit):
    g = Guard(bio, base_dir=BASE, audit_path=audit)
    try:
        g.check(kind, mode, target); return "ALLOW"
    except ConstitutionViolation:
        return "DENY"


def main():
    N = 5000
    rng = random.Random(20260705)     # fixed seed -> reproducible
    audit = os.path.join(tempfile.gettempdir(), "_ms_fuzz_audit.jsonl")
    if os.path.exists(audit):
        os.remove(audit)

    mismatches, sec_violations = [], []
    for _ in range(N):
        bio, grants = build(rng)
        kind, mode = rng.choice(KM)
        target = rng.choice(TARGETS[kind])
        want = oracle(grants, kind, mode, target)
        got = guard_decide(bio, kind, mode, target, audit)
        if got != want:
            mismatches.append((bio, kind, mode, target, want, got))
        if (kind, mode) not in grants and got == "ALLOW":
            sec_violations.append((bio, kind, mode, target))
    if os.path.exists(audit):
        os.remove(audit)

    print("=" * 78)
    print(f"  PROPERTY-BASED FUZZ  ({N} random constitutions x random effects, seed fixed)")
    print("=" * 78)
    print(f"  SECURITY   (undeclared kind/mode never ALLOWed): {len(sec_violations)} violations")
    print(f"  CONSISTENCY (guard == independent scope oracle): {len(mismatches)} mismatches")
    for (bio, k, m, t, want, got) in mismatches[:3]:
        print(f"    counterexample: {k}/{m} {t!r} -> guard={got}, oracle={want}")
        print(f"      constitution: {bio!r}")
    print("=" * 78)
    ok = (not sec_violations and not mismatches)
    if ok:
        print(f"  RESULT: PASS - across {N} random cases the guard never allowed an ungranted")
        print("          effect and always agreed with an independent scope oracle.")
        return 0
    print("  RESULT: FAIL - the fuzzer found a counterexample (a real discrepancy)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
