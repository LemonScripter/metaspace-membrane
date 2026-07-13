#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-LICENSE — the offline licence layer is a REAL signature gate, not a flag (F6, I-41).

No mock: we generate a genuine Ed25519 keypair, sign a real licence token, and prove that
the verifier accepts ONLY a correctly-signed, unexpired key from the RIGHT vendor:

  1. a freshly issued Pro key verifies -> tier=pro                 (genuine key works)
  2. one flipped byte in the key -> rejected                       (tamper-evident)
  3. verified against a DIFFERENT vendor's public key -> rejected  (can't forge across keys)
  4. an already-expired key -> rejected                            (time-bound)
  5. no licence installed -> tier=free                             (safe default)
  6. install a key into a temp HOME, current()/is_pro() read it back; remove() -> free again

If the [pro] crypto extra is absent the proof prints PROOF_SKIPPED (the suite marks SKIP),
exactly like the Linux-only Landlock proof on Windows.
"""

import os
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from core import license as lic


def main():
    if not lic.available():
        print("PROOF_SKIPPED: the [pro] crypto extra (cryptography) is not installed")
        return 0

    fails = []

    def check(cond, msg):
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            fails.append(msg)

    # a genuine vendor keypair, and a second (attacker) keypair
    priv, pub = lic.generate_keypair()
    _apriv, apub = lic.generate_keypair()

    # 1. genuine Pro key verifies against the right public key
    key = lic.issue(priv, "buyer@example.com", tier="pro", days=365)
    p = lic.verify(key, pub)
    check(p is not None and p.get("tier") == "pro", "a genuine Pro key verifies -> tier=pro")

    # 2. tamper: flip one character in the signature part
    head, _dot, tail = key.partition(".")
    bad = tail[0] and (("A" if tail[0] != "A" else "B") + tail[1:])
    tampered = head + "." + bad
    check(lic.verify(tampered, pub) is None, "a tampered key is rejected")

    # 3. right key, WRONG vendor public key -> rejected
    check(lic.verify(key, apub) is None, "a genuine key under the wrong vendor key is rejected")

    # 4. expired key -> rejected (days negative => expiry in the past)
    expired = lic.issue(priv, "buyer@example.com", tier="pro", days=-1)
    check(lic.verify(expired, pub) is None, "an expired key is rejected")

    # 5 & 6. install/read/remove against a temp HOME, using the genuine vendor key as the
    #        embedded one (env override) so install_license() verifies with it.
    home = tempfile.mkdtemp(prefix="ms_lic_home_")
    old_env = os.environ.get("METASPACE_LICENSE_PUBKEY")
    os.environ["METASPACE_LICENSE_PUBKEY"] = pub
    try:
        check(lic.current(home).get("tier") == "free" and not lic.is_pro(home),
              "no licence installed -> free (safe default)")
        # a forged key (attacker's signature) must NOT install
        forged = lic.issue(_apriv, "thief@example.com", tier="pro", days=365)
        check(lic.install_license(forged, home) is None,
              "a key signed by a different key cannot be installed")
        # the genuine key installs and reads back as pro
        check(lic.install_license(key, home) is not None, "a genuine key installs")
        check(lic.is_pro(home) and lic.current(home).get("tier") == "pro",
              "installed licence reads back as Pro")
        check(lic.remove_license(home) and not lic.is_pro(home),
              "removing the licence returns to free")
    finally:
        if old_env is None:
            os.environ.pop("METASPACE_LICENSE_PUBKEY", None)
        else:
            os.environ["METASPACE_LICENSE_PUBKEY"] = old_env
        shutil.rmtree(home, ignore_errors=True)

    print("-" * 60)
    if fails:
        print("RESULT: FAIL —", len(fails), "check(s) failed")
        return 1
    print("RESULT: PASS — licences are a real offline Ed25519 gate (tamper/forge/expiry all caught)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
