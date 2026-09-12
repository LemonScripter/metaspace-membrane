#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hol tartunk, OS-enkent? — a valaszt a LEDGERBOL szamolja, nem tarolja.

MIERT GENERATOR ES NEM LISTA. Egy leirt teendo-lista ugyanugy elavul, mint a MASTER_MAP
"22 proofs"-a vagy a DCC_RING0 fazistablaja. Ez a szkript minden futaskor a
metaspace-membrane/docs/CLAIMS.md-bol olvas, tehat amit mutat, az mindig a mai allapot.

AMIT MUTAT
  1. per-OS matrix: melyik hatas-fajta melyik TIER-t eri el, melyik allitas alapjan
  2. a BLOCKED sorok es a pontos akadalyuk
  3. a harom kereszt-korlat, ami MINDEN OS-t egyszerre fog vissza
  4. mi a legolcsobb kovetkezo lepes

AMIT NEM MUTAT: szazalekot a ledger egeszere. A 79 sorbol ~10 olyan STATED [SCOPE-LIMIT]
es WONTDO, aminek SOSEM szabad PROVEN-ne valnia (az I1b invarians ezt ki is kenyszeriti),
tehat a "hany szazalek kesz" kerdes a ledgeren ertelmetlen. Az ertelmes kerdes az, hogy
egy adott OS-en egy adott hatas-fajta eleri-e a HARD tiert — ezt szamoljuk.

HASZNALAT:  python os_matrix.py          (a metaspace-membrane repo gyokerebol)
"""
import io
import os
import re
import sys

# A ledger a REPO sajat docs/ konyvtaraban van: az eszkoz es az adat egyutt utazik,
# tehat barmely gepen, barmely konyvtarnevvel mukodik. (Korabban abszolut ut allt itt,
# mert a szkript egy masik repoban szuletett — az agens write-scope-ja miatt, nem tervezesbol.)
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "CLAIMS.md")

# A matrix cellai: (membran, hatas-fajta) -> {OS: (allitas, hogyan olvassuk)}
# Csak AZONOSITOT tarolunk; a TIER/STATUS/VERIFIED a ledgerbol jon futaskor.
CELLS = [
    ("Ágens-membrán", "Claude Code",  {"Linux": "C-03", "Windows": "C-02", "macOS": None}),
    ("Ágens-membrán", "Cursor",       {"Linux": "C-39", "Windows": "C-39", "macOS": None}),
    ("App-membrán",   "FILESYSTEM",   {"Linux": "C-75", "Windows": "C-13", "macOS": None}),
    ("App-membrán",   "SUBPROCESS",   {"Linux": "C-79", "Windows": "C-13", "macOS": None}),
    ("App-membrán",   "NETWORK",      {"Linux": "C-76", "Windows": "C-13", "macOS": None}),
    ("App-membrán",   "kompozíció",   {"Linux": "C-77", "Windows": ("C-77", "fail-closed: megtagad"),
                                        "macOS": ("C-77", "fail-closed: megtagad")}),
]

# Kereszt-korlatok: nem OS-specifikusak, tehat egyik platformon sem lehet "kesz" amig allnak.
CROSS = [("O-33", "a membrán csak a MEGNEVEZHETŐ hatások felett deny-by-default"),
         ("C-74", "a membrán saját KÓDJA cserélhető/eltávolítható (O-35)"),
         ("C-63", "engedélyezett értelmező ellenőrizetlen kódot futtathat")]


def parse():
    t = io.open(LEDGER, encoding="utf-8").read()
    idx = {}
    for m in re.finditer(r'^\| (C-\d+) \| (.+?) \| (.+?) \| (\w+(?:-\w+)?) \|$', t, re.M):
        idx[m.group(1)] = {"short": m.group(2).strip(), "tier": m.group(3).strip(),
                           "status": m.group(4).strip()}
    for m in re.finditer(r'^### (C-\d+) — .+?$(.*?)(?=^### |\Z)', t, re.M | re.S):
        cid, body = m.group(1), m.group(2)
        if cid not in idx:
            continue
        v = re.search(r'\*\*VERIFIED:\*\*\s*([^\n*]+)', body)
        b = re.search(r'\*\*BLOCKED-BY:\*\*\s*([^\n*·]+)', body)
        idx[cid]["verified"] = v.group(1).strip() if v else ""
        idx[cid]["blocked_by"] = b.group(1).strip() if b else ""
        # kimondott fenntartas a claim torzseben: a matrix NE mossa el
        cav = re.search(r'⚠ \*\*(.{0,90}?)\*\*', body)
        idx[cid]["caveat"] = cav.group(1).strip() if cav else ""
    obs = {}
    for m in re.finditer(r'^\| \*\*(O-\d+)\*\* \| (.{0,120})', t, re.M):
        obs[m.group(1)] = re.sub(r'\*+', '', m.group(2)).strip()
    return idx, obs


def verified_on(ver, osname):
    """Mert-e az adott OS-en. A 'pending' szo a kulcs: a 'Linux pending' AZT jelenti, hogy
    NINCS meg Linux-meres — ha erre a puszta 'Linux' szora illesztunk, a hianyzo merest
    sikernek konyveljuk el. Ez a mérőeszköz-hibák elso szabalya."""
    v = ver.lower()
    keys = {"Linux": ["linux"], "Windows": ["win"], "macOS": ["mac", "darwin"]}[osname]
    for k in keys:
        for m in re.finditer(re.escape(k), v):
            tail = v[m.end():m.end() + 14]
            if "pend" in tail or "hiány" in tail:
                continue          # "<os> pending" = epp hogy NINCS merve
            return True
    return False


def cell(idx, cid, osname, note=""):
    if cid is None:
        return "nincs mérés", ""
    c = idx.get(cid)
    if not c:
        return "?", ""
    tier, st, ver = c["tier"], c["status"], c.get("verified", "")
    mark = {"PROVEN": "✅", "BLOCKED": "⛔", "PLANNED": "…", "IN-PROGRESS": "…"}.get(st, "")
    if st == "PROVEN" and not verified_on(ver, osname):
        return "⚠ nem mérve itt", cid
    star = "*" if c.get("caveat") else ""
    if note:
        return "%s %s%s" % (mark, note, star), cid
    return "%s %s/%s%s" % (mark, tier, st, star), cid


def main():
    if not os.path.exists(LEDGER):
        sys.stderr.write("nincs meg a ledger: %s\n" % LEDGER)
        return 1
    idx, obs = parse()
    tot = len(idx)
    st = {}
    for c in idx.values():
        st[c["status"]] = st.get(c["status"], 0) + 1

    print("=" * 78)
    print("  HOL TARTUNK — a metaspace-membrane ledgeréből számolva")
    print("=" * 78)
    print("  %d állítás · %s" % (tot, " · ".join("%s %d" % (k, v) for k, v in sorted(st.items()))))
    print()
    print("  A 'hány százalék' a ledger egészén értelmetlen: a STATED [SCOPE-LIMIT] sorok")
    print("  SOSEM lehetnek PROVEN (I1b invariáns). Az értelmes kérdés OS + hatás-fajta.")
    print()
    print("-" * 78)
    print("  %-16s %-13s %-22s %-22s %s" % ("membrán", "fajta", "Linux", "Windows", "macOS"))
    print("-" * 78)
    for memb, kind, oses in CELLS:
        row = []
        for o in ("Linux", "Windows", "macOS"):
            spec = oses[o]
            cid0, note = spec if isinstance(spec, tuple) else (spec, "")
            txt, cid = cell(idx, cid0, o, note)
            row.append("%s %s" % (txt, cid) if cid else txt)
        print("  %-16s %-13s %-22s %-22s %s" % (memb, kind, row[0][:21], row[1][:21], row[2][:20]))
    print("-" * 78)
    cav = [(c, idx[c]["caveat"]) for c in sorted(idx, key=lambda x: int(x[2:])) if idx[c].get("caveat")]
    if cav:
        print()
        print("  * = a sor KIMONDOTT fenntartast hordoz (a reszlet a claimben):")
        for c, w in cav:
            print("      %-6s %s" % (c, w[:86]))
    print()
    print("  BLOKKOLT sorok és az akadályuk:")
    for cid in sorted(idx, key=lambda c: int(c[2:])):
        c = idx[cid]
        if c["status"] == "BLOCKED":
            bb = c.get("blocked_by", "?")
            first = bb.split(",")[0].strip()
            print("    %-6s %-52s %-14s %s" % (cid, c["short"][:50], bb[:13],
                                               obs.get(first, "")[:0]))
            if first in obs:
                print("           └─ %s: %s" % (first, obs[first][:92]))
    print()
    print("  KERESZT-KORLÁTOK — minden OS-t egyszerre fognak vissza:")
    for cid, why in CROSS:
        stt = idx.get(cid, {}).get("status", obs.get(cid) and "OPEN" or "?")
        print("    %-6s [%s]  %s" % (cid, stt, why))
    print()
    print("  A LEGOLCSÓBB KÖVETKEZŐ LÉPÉSEK (nem igényelnek Macet és gyártói döntést):")
    todo = [(cid, idx[cid]["short"]) for cid in sorted(idx, key=lambda c: int(c[2:]))
            if idx[cid]["status"] in ("PLANNED", "IN-PROGRESS")]
    for cid, short in todo:
        print("    %-6s %s" % (cid, short[:64]))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
