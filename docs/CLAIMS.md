# Claim ledger

**Rule: claim = proof.** Every user-facing statement (README, docs, plugin/marketplace copy,
outreach) must appear here with a type and, where applicable, the runnable proof that backs it.
If a claim is not in this table, it must not be published.

**Types:** `[PROVEN]` (a proof asserts it, falsifiably) · `[MEASURED]` (a recorded measurement) ·
`[ARCH]` (an architectural property, argued not asserted-by-run) · `[SCOPE-LIMIT]` (an honest
statement of what is NOT claimed).

Reproduce everything: `python run_proofs.py` (needs `pip install metaspace-membrane[proofs]`).

---

## Shipped claims (existing engine)
| Claim | Type | Backed by | Verified |
|---|---|---|---|
| Deny-by-default effect containment at the WASM/WASI chokepoint (per capability kind) | [PROVEN] | `run_wasm_demo`, `run_wasi_demo`, `run_real_app_demo`, `bypass_proof`, `run_fuzz` | Win + Linux |
| Agent tool calls are mediated before they run; obfuscated shell caught structurally; fail-closed | [PROVEN] | `test_hook`, `test_shell_policy`, `run_product_e2e`, `run_mcp_e2e` | Win + Linux |
| Prompt-injection → RCE (Friendly Fire) made unreachable; real payload fires without the membrane, never with it | [PROVEN] | `run_friendly_fire_proof` | Win (verdict) + Linux (full A/B), 23/23 |
| OS-level write containment for a stock native program (Linux Landlock) | [PROVEN] | `run_landlock_demo` | Linux |
| The membrane does not make the model injection-proof; it contains effects, not the model's prose | [SCOPE-LIMIT] | `docs/THREAT_FRIENDLY_FIRE.md` §8 | — |
| An allowlisted interpreter running its own trusted script is allowed by design | [SCOPE-LIMIT] | `docs/THREAT_FRIENDLY_FIRE.md` §8 | — |
| Confining a process that already started is the OS substrate's job, not the agent hook's | [SCOPE-LIMIT] | `SECURITY.md`, `docs/THREAT_FRIENDLY_FIRE.md` §9 | — |
| Research prototype / MVP (TRL ~3–4); no third-party security audit yet | [SCOPE-LIMIT] | `SECURITY.md` | — |

## Install claims (F1 — filled as each work item lands)
| Claim | Type | Backed by | Verified |
|---|---|---|---|
| The Warden hook + `core/` run with zero third-party dependencies (`wasmtime` is proofs-only) | [PROVEN] | `run_zerodep_proof` (WI-1) | _pending_ |
| One-step user-level install wires the hook into `~/.claude/settings.json` and it then blocks the attack | [PROVEN] | P-INSTALL (WI-2) | _pending_ |
| A deceived agent cannot disable the membrane (settings/constitution write, or `metaspace off`/`ratify` via Bash) | [PROVEN] | P-SELFPROTECT (WI-3/WI-9) | _pending_ |
| Install is idempotent and non-clobbering; uninstall reverts cleanly | [PROVEN] | P-IDEMPOTENT, P-UNINSTALL (WI-2/WI-9) | _pending_ |
| First run is dry-run/observe; enforcement begins only after the user ratifies | [PROVEN] | P-DRYRUN (WI-4) | _pending_ |
| `metaspace demo` shows the real attack being blocked (falsifiable, not a canned message) | [PROVEN] | P-DEMO (WI-5) | _pending_ |
| Version strings agree across `pyproject.toml`, `plugin.json`, CLI, and CHANGELOG | [PROVEN] | P-VERSION (WI-6/WI-8) | _pending_ |
