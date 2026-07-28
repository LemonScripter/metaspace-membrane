#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-VERSION — the version is consistent across the packaging manifest, the plugin manifest, the
CLI, and the citation metadata. A release that bumped one and forgot another would ship an
inconsistent version; this proof fails if `pyproject.toml`, `.claude-plugin/plugin.json`,
`metaspace --version` and `CITATION.cff` disagree.

WHY CITATION.cff IS CHECKED HERE. It was not, for three releases, and it drifts in a way the
others cannot: it is the only file that also carries a **DOI**, and a citation pointing at the
wrong archived version is a false statement about the artefact, not a cosmetic slip. It is also
the file most easily forgotten, because nothing imports it and no test touched it. Adding it cost
one function; leaving it out was one release away from publishing a `0.3.2` whose own citation
metadata said `0.3.1`.

THE DOI IS DELIBERATELY NOT CHECKED FOR EQUALITY WITH THE VERSION. Zenodo mints the version DOI
*after* the GitHub release exists, so at tag time no correct value can be present — an ordering
fact, not an oversight.

WHAT IS CHECKED, AND WHY IT IS NOT PLAIN EQUALITY. The first version of this proof required the
README badge and `CITATION.cff` to quote the *same* DOI. That was wrong, and it broke as soon as
the DOIs were set correctly for 0.3.2: the two files answer different questions and should not
carry the same value. A badge means "this project", so it takes the **concept DOI**, which always
resolves to the newest archived version and therefore never needs a manual edit again. A citation
means "the exact thing I ran", so `CITATION.cff` pins the **version DOI**. The rule that survives
both is: every DOI in the README must be one that `CITATION.cff` also declares — as its `doi` or
among its `identifiers`. That still catches the real failure (a badge pointing at an archive the
citation metadata knows nothing about) without forcing two files to lie about their purpose.

Run: python run_version_proof.py   (exit 0 iff everything agrees)
"""

import os
import re
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CLI = os.path.join(REPO, "cli.py")

_DOI_RE = re.compile(r"10\.5281/zenodo\.\d+")


def pyproject_version():
    text = open(os.path.join(REPO, "pyproject.toml"), encoding="utf-8").read()
    m = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else None


def plugin_version():
    data = json.load(open(os.path.join(REPO, ".claude-plugin", "plugin.json"), encoding="utf-8"))
    return data.get("version")


def cli_version():
    p = subprocess.run([sys.executable, CLI, "--version"], capture_output=True, text=True)
    out = (p.stdout or "").strip() or (p.stderr or "").strip()   # argparse may use either
    m = re.search(r"(\d+\.\d+\.\d+\S*)", out)
    return m.group(1) if m else None


def citation_version():
    text = open(os.path.join(REPO, "CITATION.cff"), encoding="utf-8").read()
    m = re.search(r'(?m)^version:\s*"?([0-9][^"\s]*)"?', text)
    return m.group(1) if m else None


def citation_dois():
    """Every DOI the citation metadata declares: the `doi` field and all `identifiers`."""
    text = open(os.path.join(REPO, "CITATION.cff"), encoding="utf-8").read()
    return _DOI_RE.findall(text)


def readme_dois():
    text = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    return _DOI_RE.findall(text)


def main():
    py, pl, cl, cf = pyproject_version(), plugin_version(), cli_version(), citation_version()
    c_dois, r_dois = citation_dois(), readme_dois()
    print("=" * 66)
    print("  P-VERSION — version parity across manifests, CLI and citation")
    print("=" * 66)
    print("  pyproject.toml      :", py)
    print("  plugin.json         :", pl)
    print("  metaspace --version :", cl)
    print("  CITATION.cff        :", cf)
    print("  DOI (CITATION.cff)  :", ", ".join(c_dois) or None)
    print("  DOI (README)        :", ", ".join(r_dois) or None)
    print("-" * 66)

    failures = []
    if not (py and py == pl == cl):
        failures.append("pyproject / plugin.json / CLI disagree")
    if cf != py:
        failures.append(f"CITATION.cff says {cf}, the package says {py}")
    if not c_dois:
        failures.append("CITATION.cff carries no well-formed Zenodo DOI")
    if not r_dois:
        failures.append("README carries no well-formed Zenodo DOI badge")
    for d in r_dois:
        if d not in c_dois:
            failures.append(f"README cites {d}, which CITATION.cff does not declare "
                            f"(it declares: {', '.join(c_dois) or 'nothing'})")

    if failures:
        print("  RESULT: FAIL")
        for f in failures:
            print("    -", f)
        print("=" * 66)
        return 1
    print("  RESULT: PASS — version and citation metadata agree")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
