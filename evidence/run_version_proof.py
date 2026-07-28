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

THE DOI IS DELIBERATELY NOT CHECKED FOR EQUALITY WITH ANYTHING. Zenodo mints the version DOI
*after* the GitHub release exists, so at tag time no correct value can be present — an ordering
fact, not an oversight. What IS checked is that a DOI is present and well-formed, and that the
README badge and the CITATION file quote the SAME one, since those two are updated by hand in the
same follow-up step and are the pair most likely to fall out of step.

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


def citation_doi():
    text = open(os.path.join(REPO, "CITATION.cff"), encoding="utf-8").read()
    m = _DOI_RE.search(text)
    return m.group(0) if m else None


def readme_doi():
    text = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    found = _DOI_RE.findall(text)
    return found[0] if found else None


def main():
    py, pl, cl, cf = pyproject_version(), plugin_version(), cli_version(), citation_version()
    c_doi, r_doi = citation_doi(), readme_doi()
    print("=" * 66)
    print("  P-VERSION — version parity across manifests, CLI and citation")
    print("=" * 66)
    print("  pyproject.toml      :", py)
    print("  plugin.json         :", pl)
    print("  metaspace --version :", cl)
    print("  CITATION.cff        :", cf)
    print("  DOI (CITATION.cff)  :", c_doi)
    print("  DOI (README badge)  :", r_doi)
    print("-" * 66)

    failures = []
    if not (py and py == pl == cl):
        failures.append("pyproject / plugin.json / CLI disagree")
    if cf != py:
        failures.append(f"CITATION.cff says {cf}, the package says {py}")
    if not c_doi:
        failures.append("CITATION.cff carries no well-formed Zenodo DOI")
    if not r_doi:
        failures.append("README carries no well-formed Zenodo DOI badge")
    if c_doi and r_doi and c_doi != r_doi:
        failures.append(f"README DOI {r_doi} != CITATION DOI {c_doi}")

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
