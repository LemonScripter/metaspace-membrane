#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P-ZERODEP — the Warden agent hook and core/ run with ZERO third-party dependencies.

wasmtime is needed only for the WebAssembly/WASI proofs, NOT for the agent membrane (the
shipped protection). This proof makes `wasmtime` unimportable, then imports the entire Warden
decision path and drives a REAL decision (blocking a Friendly-Fire command and an out-of-scope
write) — proving the shipped protection needs no third-party package.

Falsifiable: if any module on the Warden path grows an `import wasmtime` (or the block is
circumvented), the import raises and this proof FAILS. It is not a print("PASS").

Run: python run_zerodep_proof.py   (exit 0 iff the Warden path is dependency-free and works)
"""

import os
import sys
import importlib.abc

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class _Blocker(importlib.abc.MetaPathFinder):
    """Refuse to import wasmtime (and submodules), simulating a machine without it."""
    BLOCKED = ("wasmtime",)

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in self.BLOCKED:
            raise ModuleNotFoundError(f"[zerodep proof] import of '{name}' blocked on purpose")
        return None  # defer to the normal finders for everything else


def main():
    # If wasmtime slipped in before we installed the block, the test would be meaningless.
    if "wasmtime" in sys.modules:
        print("FAIL: wasmtime was already imported before the block was set up")
        return 1
    sys.meta_path.insert(0, _Blocker())

    print("=" * 76)
    print("  P-ZERODEP — Warden hook + core/ import and decide with wasmtime UNAVAILABLE")
    print("=" * 76)

    # 1) import the ENTIRE Warden decision path with wasmtime blocked
    try:
        from core.guard import Guard, ConstitutionViolation
        from core.shell_policy import check as shell_check
        from core import agent_adapter  # noqa: F401  (imports guard + shell_policy)
        import products.ai_membrane.session_guard_hook as hook  # the shipped hook module
    except ModuleNotFoundError as e:
        print(f"FAIL: the Warden path pulled in a blocked third-party module -> {e}")
        return 1
    print("  [ok] imported core.guard, core.shell_policy, core.agent_adapter, session_guard_hook")

    # 2) belt-and-suspenders: nothing on the path actually imported wasmtime
    if "wasmtime" in sys.modules:
        print("FAIL: wasmtime ended up imported by the Warden path")
        return 1
    print("  [ok] 'wasmtime' is NOT in sys.modules after importing the whole Warden path")

    # 3) drive REAL decisions on the real modules (dependency-free), and assert they hold
    ALLOW = {"python", "git", "ls", "bash", "sh"}
    ok, _ = shell_check("./security.sh", allow=ALLOW, deny=[])
    if ok:
        print("FAIL: shell policy allowed ./security.sh")
        return 1
    print("  [ok] real shell_policy BLOCKS ./security.sh (Friendly-Fire vector)")

    guard = Guard('CELL T { CAPABILITIES { FILESYSTEM write "proj/**"; } }',
                  base_dir=os.path.join(REPO_ROOT, "proj"), audit_path=False)
    blocked = False
    try:
        guard.check("FILESYSTEM", "write", "/etc/evil")
    except ConstitutionViolation:
        blocked = True
    if not blocked:
        print("FAIL: guard allowed an out-of-scope write")
        return 1
    print("  [ok] real Guard BLOCKS an out-of-project write (deny-by-default)")

    print("-" * 76)
    print("  RESULT: PASS — the shipped Warden protection runs with zero third-party deps.")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
