#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project â€” reproducible proof runner.

Runs every membrane proof and reports PASS/FAIL. This is the evidence: no hosted CI
required â€” clone the repo and run one command.

    pip install wasmtime
    python run_proofs.py          # exit 0 if all proofs pass
"""

import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

PROOFS = [
    ("App membrane - WebAssembly hard proof",  "products/app_membrane/run_wasm_demo.py"),
    ("App membrane - unbypassability proof",   "products/app_membrane/bypass_proof.py"),
    ("App membrane - WASI real-program proof", "products/app_membrane/wasi/run_wasi_demo.py"),
    ("App membrane - REAL app (real work + containment)", "products/app_membrane/run_real_app_demo.py"),
    ("Synthesis closed loop (code->bio->enforce)", "evidence/demos/run_synth_demo.py"),
    ("Dogfood: synthesize from this repo's code", "evidence/demos/run_dogfood_demo.py"),
    ("Ratification (content-bound provenance)", "evidence/demos/run_ratify_demo.py"),
    ("Ratification gate (only RATIFIED runs)",  "evidence/demos/run_gate_demo.py"),
    ("Dry-run learning mode (false-positive fix)", "evidence/demos/run_dryrun_demo.py"),
    ("Ratification review (cognitive brake)",   "evidence/demos/run_ratification_review_demo.py"),
    ("Knowledge membrane (hard tier)",         "evidence/demos/run_knowledge_demo.py"),
    ("Epistemic soft tier (entailment flag)",  "evidence/demos/run_entailment_demo.py"),
    ("Agent membrane",                         "products/ai_membrane/test_hook.py"),
    ("Structural shell policy (allowlist)",    "products/ai_membrane/test_shell_policy.py"),
    ("Zero-dependency Warden path (wasmtime is proofs-only)", "evidence/run_zerodep_proof.py"),
    ("Install: user-level wiring, idempotent, installed hook blocks the attack", "evidence/run_install_proof.py"),
    ("Self-protection: a deceived agent cannot disable the membrane (worst case)", "evidence/run_selfprotect_proof.py"),
    ("Dry-run install then enforce (no over-blocking on first run)", "evidence/run_dryrun_mode_proof.py"),
    ("Per-project constitutions (user-level, self-protected)", "evidence/run_project_config_proof.py"),
    ("Control panel: configures the real membrane + rejects cross-origin (UI)", "evidence/run_ui_proof.py"),
    ("Telemetry: opt-in, anonymous, no PII, default off", "evidence/run_telemetry_proof.py"),
    ("Command catalogue: complete, alphabetical, self-explaining (panel)", "evidence/run_commands_proof.py"),
    ("Authenticity gate: tells a real program from AI slop by its effects", "evidence/run_slopgate_proof.py"),
    ("Offline licence: a real Ed25519 gate (tamper/forge/expiry caught)", "evidence/run_license_proof.py"),
    ("App membrane: a running program confined to its .bio (metaspace run)", "evidence/run_apprun_proof.py"),
    ("Analytics: cookie-free, aggregate-only, resists hostile input", "evidence/run_analytics_proof.py"),
    ("`metaspace demo` really blocks the attack (live self-test)", "evidence/run_demo_proof.py"),
    ("Uninstall: `metaspace off` clean, idempotent, agent-unreachable", "evidence/run_uninstall_proof.py"),
    ("Version parity across pyproject / plugin.json / CLI", "evidence/run_version_proof.py"),
    ("Friendly Fire: prompt-injected RCE via untrusted repo made unreachable (AI Now brief)", "evidence/run_friendly_fire_proof.py"),
    ("Threat-model matrix (honest coverage)",  "evidence/demos/run_threat_matrix_demo.py"),
    ("Self-falsification (anti-slop audit)",   "evidence/run_falsification.py"),
    ("Property-based fuzz (5000 random cases)", "evidence/run_fuzz.py"),
    ("CLI end-to-end product flow (M0)",       "evidence/run_cli_e2e.py"),
    ("Product e2e: real membrane -> audit -> report (M1)", "evidence/run_product_e2e.py"),
    ("MCP adapter-proof: same core, second harness (M2)", "evidence/run_mcp_e2e.py"),
    ("SandboxEnforcer: real program OS-confined by .bio (M3, Linux/Landlock)", "evidence/run_landlock_demo.py"),
    ("Team/CI gate: only a ratified, unbroadened .bio passes (M4)", "evidence/run_team_gate_e2e.py"),
    ("Roadmap/claim ledger integrity: claim = proof, machine-checked", "evidence/run_roadmap_proof.py"),
    ("Cursor host compatibility: one hook, two hosts, same verdicts", "evidence/run_cursor_compat_proof.py"),
    ("Env-less config: the user's mode + constitution reach every host (O-13)", "evidence/run_envless_config_proof.py"),
    ("Multi-anchor self-protection: every host's config is defended (O-14)", "evidence/run_multianchor_proof.py"),
    ("Host profiles: agent differences are data, verdict reaches all (C-38)", "evidence/run_hostprofile_proof.py"),
    ("Multi-host install: merged, backed up, idempotent, refuses to guess", "evidence/run_multihost_install_proof.py"),
    ("Hermeticity: the evidence does not depend on the machine (C-61)", "evidence/run_hermeticity_proof.py"),
    ("BASH_POLICY parse: a comment cannot empty the allowlist; empty fails closed (O-20)", "evidence/run_bashparse_proof.py"),
    ("Antigravity bridge: agy's contract in, the Warden's verdict out, fail-closed (C-64)", "evidence/run_agy_adapter_proof.py"),
    ("Anchor carve-out: user data writable, control surface sealed (C-66/O-22)", "evidence/run_anchor_carveout_proof.py"),
]


def main():
    try:
        import wasmtime  # noqa: F401
    except ImportError:
        print("Missing dependency 'wasmtime'. Install it first:  pip install wasmtime")
        return 2

    print("=" * 60)
    print("  MetaSpace Membrane â€” reproducible proofs")
    print("=" * 60)
    # Hermetic baseline. The suite used to inherit the developer's own membrane configuration:
    # most proofs never set METASPACE_MODE and silently relied on "unset means enforce". Once the
    # user-level config file became authoritative for hosts that do not propagate env (C-54), a
    # machine whose real config said `dryrun` made four core proofs fail — the evidence depended
    # on the state of the machine running it, which is exactly what "claim = proof" must not
    # tolerate. Pinning the baseline here makes the assumption explicit and the run reproducible.
    # Proofs that exercise other modes set them on their own child environment and are unaffected.
    #
    # The baseline drops EVERY `METASPACE_*` variable and re-pins only the mode, rather than
    # listing the ones known to cause trouble. That list was `METASPACE_SESSION_BIO` alone, and
    # it was already incomplete: a host that exports `METASPACE_PROJECT_ROOT` into the tool
    # environment (a `settings.json` env block does exactly that) made two proofs fail, because
    # the shipped constitution's `{{PROJECT_ROOT}}` then resolved to the developer's own working
    # area instead of the proof's temporary project. Enumerating is the wrong shape here: a
    # variable added later is a silent hole, while dropping everything and re-adding what the
    # suite needs means the only possible mistake is a proof that visibly cannot run.
    base_env = {k: v for k, v in os.environ.items() if not k.startswith("METASPACE_")}
    base_env["METASPACE_MODE"] = "enforce"
    base_env.pop("CLAUDE_PROJECT_DIR", None)   # the hook falls back to it for the project root

    results = []
    for name, rel in PROOFS:
        p = subprocess.run([sys.executable, os.path.join(HERE, rel)],
                           capture_output=True, text=True, env=base_env)
        if p.returncode == 0 and "PROOF_SKIPPED" in (p.stdout or ""):
            status = "SKIP"      # e.g. an OS-specific proof on a platform that can't run it
        elif p.returncode == 0:
            status = "PASS"
        else:
            status = "FAIL"
        results.append((name, status))
        print(f"  [{status}] {name}")
        if status == "SKIP":
            reason = next((l for l in (p.stdout or "").splitlines() if "PROOF_SKIPPED" in l), "")
            if reason:
                print("        " + reason.strip())
        if status == "FAIL":
            tail = (p.stdout or "")[-600:] + (p.stderr or "")[-600:]
            print("  ---- output ----")
            for line in tail.splitlines():
                print("  " + line)
            print("  ----------------")
    print("-" * 60)
    passed = sum(1 for _, s in results if s == "PASS")
    skipped = sum(1 for _, s in results if s == "SKIP")
    failed = sum(1 for _, s in results if s == "FAIL")
    all_ok = (failed == 0)
    summary = f"  {passed} passed"
    if skipped:
        summary += f", {skipped} skipped"
    if failed:
        summary += f", {failed} failed"
    print(summary + f"  (of {len(results)} proofs)")
    print("  RESULT:", "ALL PROOFS PASS" if all_ok else "SOME PROOFS FAILED")
    print("=" * 60)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

