# -*- coding: utf-8 -*-
"""
Offline licence layer (open-core monetisation infrastructure).

Design (I-41, F6):
  - The Warden membrane itself is FREE and stays zero-dependency; this module is only
    loaded on the licence path (`metaspace license`) and never on the enforcement hot path.
  - Licences are Ed25519-signed tokens verified fully OFFLINE against an embedded vendor
    public key. No phone-home, no online activation, works air-gapped.
  - A licence is a soft entitlement gate, not a security boundary: it decides which tier
    a feature runs at, nothing about containment. (Containment is core/guard.py.)
  - As of F6 nothing is gated yet ("infra now, everything free"): `is_pro()` exists and is
    proven, but no shipped command refuses to run without Pro. Flipping a single gate turns
    a feature Pro later; see cli.py.

Crypto lives in the optional `[pro]` extra (`pip install metaspace-membrane[pro]`), so the
zero-dep runtime is unaffected. `available()` reports whether the extra is present.
"""

import os
import json
import base64
import datetime

# --- vendor public key -------------------------------------------------------
# Placeholder key: its private half was generated and discarded on purpose, so no valid
# licence can be issued against it yet. Before activating paid tiers the vendor runs
# `metaspace keygen`, keeps the private key secret, and sets METASPACE_LICENSE_PUBKEY (or
# replaces this constant) with the matching public key.
VENDOR_PUBLIC_KEY = "EcPyFMwYKwiJ84mGlitK2Q13snf9MifMAyAjMddRKjQ"


def vendor_pubkey():
    return os.environ.get("METASPACE_LICENSE_PUBKEY", "").strip() or VENDOR_PUBLIC_KEY


def available():
    """True if the [pro] crypto extra is installed."""
    try:
        import cryptography.hazmat.primitives.asymmetric.ed25519  # noqa: F401
        return True
    except Exception:
        return False


def _b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _today():
    return datetime.date.today().isoformat()


# --- issuance (vendor side; needs the private key) ---------------------------
def generate_keypair():
    """Return (private_b64, public_b64) raw Ed25519 keys. Vendor keeps the private half secret."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization as ser
    k = Ed25519PrivateKey.generate()
    priv = k.private_bytes(ser.Encoding.Raw, ser.PrivateFormat.Raw, ser.NoEncryption())
    pub = k.public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw)
    return _b64e(priv), _b64e(pub)


def issue(private_b64, email, tier="pro", days=365):
    """Sign a licence token: base64url(payload).base64url(signature)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    k = Ed25519PrivateKey.from_private_bytes(_b64d(private_b64))
    payload = {
        "email": email,
        "tier": tier,
        "issued": _today(),
        "expires": (datetime.date.today() + datetime.timedelta(days=days)).isoformat() if days else None,
    }
    msg = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    sig = k.sign(msg)
    return _b64e(msg) + "." + _b64e(sig)


# --- verification (client side; needs only the public key) -------------------
def verify(key_str, public_b64=None):
    """Return the payload dict if the token is validly signed and unexpired, else None."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    pub = public_b64 or vendor_pubkey()
    try:
        msg_b64, sig_b64 = key_str.strip().split(".", 1)
        msg = _b64d(msg_b64)
        sig = _b64d(sig_b64)
        Ed25519PublicKey.from_public_bytes(_b64d(pub)).verify(sig, msg)
        payload = json.loads(msg.decode())
    except Exception:
        return None
    exp = payload.get("expires")
    if exp and _today() > exp:
        return None
    return payload


# --- installed licence (client side) -----------------------------------------
def _license_path(home=None):
    home = home or os.path.expanduser("~")
    return os.path.join(home, ".claude", "metaspace", "license.txt")


def install_license(key_str, home=None):
    """Verify then persist a licence token. Returns the payload, or None if invalid."""
    payload = verify(key_str)
    if not payload:
        return None
    path = _license_path(home)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key_str.strip() + "\n")
    return payload


def remove_license(home=None):
    path = _license_path(home)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def current(home=None):
    """The active entitlement: the installed licence's payload, else the free tier."""
    path = _license_path(home)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                payload = verify(f.read())
            if payload:
                return payload
        except Exception:
            pass
    return {"tier": "free"}


def is_pro(home=None):
    return current(home).get("tier") == "pro"
