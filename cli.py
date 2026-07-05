#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace CLI — one entry point over the engine (M0 productization).

    metaspace synthesize <path> [--out FILE] [--cell NAME]   code -> draft .bio
    metaspace ratify     <bio>  [--yes] [--out FILE]         review + cognitive brake + stamp
    metaspace gate       <bio>                                exit 0 only if RATIFIED
    metaspace report     <audit.jsonl>                        human-readable session report
    metaspace init       [dir]  [--out FILE]                  synthesize a draft for a project

Cross-platform by construction: only os.path / shlex / stdlib, no OS-specific calls. Tested on
Windows; Linux/macOS CI is a stated pending gap (see STATUS / SECURITY).
"""

import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _ascii():
    # keep output encodable on any console (Windows cp1252 etc.)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def cmd_synthesize(args):
    from core.capability_analyzer import analyze_path, synthesize_bio
    if not os.path.exists(args.path):
        sys.stderr.write("path not found: %s\n" % args.path)
        return 2
    findings = analyze_path(args.path)
    base = os.path.basename(os.path.abspath(args.path.rstrip("/\\")))
    cell = args.cell or os.path.splitext(base)[0].replace("-", "_")
    bio = synthesize_bio(cell, findings)
    print(bio)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(bio + "\n")
        sys.stderr.write("\n[OK] constitution written: %s\n" % args.out)
    return 0


def cmd_ratify(args):
    from core.provenance import verify, ratify, badge, policy_fingerprint
    from core.ratification_review import review, assert_ratifiable, UnjustifiedProvisional
    if not os.path.exists(args.bio):
        sys.stderr.write("file not found: %s\n" % args.bio)
        return 2
    text = open(args.bio, encoding="utf-8").read()
    status = verify(text)
    print("status:", badge(status), " policy:", policy_fingerprint(text))
    rv = review(text)
    for c in rv["provisional"]:
        if c["justified"]:
            print("  [OK]      %s/%s %r -- %s" % (c["kind"], c["mode"], c["scope"], c["justification"]))
        else:
            print("  [MISSING] %s/%s %r  (needs a JUSTIFY reason)" % (c["kind"], c["mode"], c["scope"]))
    try:
        assert_ratifiable(text)
    except UnjustifiedProvisional as e:
        print("\nRATIFICATION REFUSED:", e)
        return 1
    if status == "RATIFIED":
        print("Already ratified and unchanged.")
        return 0
    if not args.yes:
        try:
            if input("Ratify this constitution? [y/N] ").strip().lower() not in ("y", "yes"):
                print("Aborted.")
                return 1
        except EOFError:
            print("Aborted (no tty; use --yes).")
            return 1
    out = args.out or args.bio
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(ratify(text))
    print(badge("RATIFIED"), "->", out)
    return 0


def cmd_gate(args):
    from core.provenance import verify, badge
    if not os.path.exists(args.bio):
        sys.stderr.write("file not found: %s\n" % args.bio)
        return 2
    status = verify(open(args.bio, encoding="utf-8").read())
    print("gate:", badge(status))
    if status == "RATIFIED":
        print("ALLOWED to run.")
        return 0
    print("REFUSED: only a RATIFIED constitution may run in production.")
    return 1


def cmd_report(args):
    if not os.path.exists(args.audit):
        sys.stderr.write("file not found: %s\n" % args.audit)
        return 2
    allow = deny = 0
    denied_by_kind = {}
    denied_targets = []
    for line in open(args.audit, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        d = rec.get("decision")
        if d == "ALLOW":
            allow += 1
        elif d == "DENY":
            deny += 1
            kind = rec.get("kind") or rec.get("tool") or "?"
            denied_by_kind[kind] = denied_by_kind.get(kind, 0) + 1
            tgt = rec.get("target") or rec.get("cmd") or ""
            if tgt:
                denied_targets.append((kind, tgt, rec.get("reason", "")))
    total = allow + deny
    print("=" * 66)
    print("  MetaSpace session safety report")
    print("=" * 66)
    print("  audit source :", args.audit)
    print("  decisions    :", total, " (ALLOW=%d, BLOCKED=%d)" % (allow, deny))
    if deny:
        print("  the agent attempted %d effect(s) OUTSIDE its constitution; all were BLOCKED:" % deny)
        for kind, n in sorted(denied_by_kind.items(), key=lambda x: -x[1]):
            print("    - %-12s %d blocked" % (kind, n))
        print("  examples:")
        for kind, tgt, reason in denied_targets[:5]:
            print("    [BLOCKED] %-10s %s" % (kind, str(tgt)[:60]))
    else:
        print("  no out-of-constitution effect was attempted.")
    print("=" * 66)
    return 0


def cmd_init(args):
    from core.capability_analyzer import analyze_path, synthesize_bio
    proj = os.path.abspath(args.dir)
    if not os.path.isdir(proj):
        sys.stderr.write("not a directory: %s\n" % proj)
        return 2
    findings = analyze_path(proj)
    bio = synthesize_bio(os.path.basename(proj).replace("-", "_"), findings)
    out = args.out or os.path.join(proj, "metaspace.bio")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(bio + "\n")
    print("[OK] draft constitution synthesized from the project code:")
    print("    ", out)
    print("Next: review it, then  metaspace ratify %s" % out)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="metaspace", description="MetaSpace — a provable safety membrane.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("synthesize", help="analyze code -> draft .bio")
    s.add_argument("path"); s.add_argument("--out"); s.add_argument("--cell")
    s.set_defaults(fn=cmd_synthesize)

    r = sub.add_parser("ratify", help="review + cognitive brake + stamp RATIFIED")
    r.add_argument("bio"); r.add_argument("--yes", action="store_true"); r.add_argument("--out")
    r.set_defaults(fn=cmd_ratify)

    g = sub.add_parser("gate", help="exit 0 only if the constitution is RATIFIED")
    g.add_argument("bio"); g.set_defaults(fn=cmd_gate)

    rp = sub.add_parser("report", help="human-readable session report from an audit log")
    rp.add_argument("audit"); rp.set_defaults(fn=cmd_report)

    i = sub.add_parser("init", help="synthesize a draft constitution for a project")
    i.add_argument("dir", nargs="?", default="."); i.add_argument("--out")
    i.set_defaults(fn=cmd_init)
    return p


def main(argv=None):
    _ascii()
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
