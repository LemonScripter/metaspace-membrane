"""
build_features.py
-----------------
Reads the LIVE unleash backup that agy/antigravity wrote
(%TEMP% / unleash-repo-schema-v1-codeium-language-server.json), which is a
dict keyed by feature-name -> full Feature object.

Produces:
  features_patched.json  -> standard Unleash v2 client/features response
                            {"version":2,"features":[...],"segments":[]}
                            with the `json-hooks-enabled` constraint stripped
                            so it evaluates TRUE regardless of the `ide` context.

We serve the FULL feature set (every other flag keeps its real current value),
so nothing else freezes or breaks -- we only loosen the one hook gate.
"""
import json, os, sys, tempfile

# never hard-code a developer's own path: this repo is public, and a fallback like
# C:\Users\<name>\AppData\Local\Temp discloses the account it was written on
TEMP = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
BACKUP = os.path.join(TEMP, "unleash-repo-schema-v1-codeium-language-server.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "features_patched.json")

TARGET = "json-hooks-enabled"

# Hook-execution feature names referenced inside agy.exe but NOT present in the
# server flag set. If the executor gates on any of these via unleash, a missing
# flag resolves to the fallback default (false). We inject them as enabled so
# every plausible execution gate is open. Harmless if unused.
INJECT_ENABLED = [
    "enable-command-hooks",
    "enable-generative-hooks",
    "enable-command-assessor",
]


def _mk_flag(name):
    return {
        "name": name,
        "type": "release",
        "description": "injected by mock to open hook execution gate",
        "enabled": True,
        "strategies": [{"name": "default", "constraints": [], "parameters": {}}],
        "variants": [],
        "dependencies": None,
        "impressionData": False,
    }


def feasibility():
    """Best-effort check of whether agy activation can actually work on THIS machine — the honest
    counterpart to 'the files shipped'. The install always writes the hook, but activation is
    reverse-engineered and environment-dependent (O-16). Returns (ok: bool, reasons: list[str])."""
    import platform
    reasons = []
    if platform.system() != "Windows":
        reasons.append("the guarded launcher is Windows-only (PowerShell/.cmd)")
    if not os.path.exists(BACKUP):
        reasons.append("no Unleash backup found (%s) — launch agy at least once, or your build "
                       "uses a different appName" % os.path.basename(BACKUP))
    else:
        try:
            d = json.load(open(BACKUP, encoding="utf-8"))
            keys = d if isinstance(d, dict) else {f.get("name") for f in d}
            if TARGET not in keys:
                reasons.append("the '%s' feature flag is not in your Unleash backup — your agy "
                               "build or account may differ" % TARGET)
        except Exception:
            reasons.append("could not read the Unleash backup")
    return (not reasons, reasons)


def main():
    if not os.path.exists(BACKUP):
        print(f"[!] backup not found: {BACKUP}", file=sys.stderr)
        sys.exit(1)

    with open(BACKUP, encoding="utf-8") as f:
        data = json.load(f)

    # backup is {name: featureObj}; some forks wrap under "features"
    if isinstance(data, dict) and "features" in data and isinstance(data["features"], list):
        features = data["features"]
    elif isinstance(data, dict):
        features = list(data.values())
    else:
        features = data

    patched = 0
    for f in features:
        if not isinstance(f, dict):
            continue
        if f.get("name") == TARGET:
            f["enabled"] = True
            for strat in f.get("strategies") or []:
                # drop the ide=IN[jetski] constraint -> unconditional match
                if strat.get("constraints"):
                    strat["constraints"] = []
            # also neutralise any single top-level constraint field
            patched += 1

    existing = {f.get("name") for f in features if isinstance(f, dict)}
    injected = 0
    for name in INJECT_ENABLED:
        if name not in existing:
            features.append(_mk_flag(name))
            injected += 1

    resp = {"version": 2, "features": features, "segments": []}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(resp, f)

    print(f"[+] total features : {len(features)}")
    print(f"[+] patched '{TARGET}': {patched}")
    print(f"[+] injected flags : {injected}")
    print(f"[+] wrote          : {OUT}")
    if patched == 0:
        print("[!] WARNING: target flag not found in backup", file=sys.stderr)


if __name__ == "__main__":
    main()
