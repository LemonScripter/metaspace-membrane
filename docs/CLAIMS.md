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

## Analytics claims (F6-2 — privacy-first statistics)
| Claim | Type | Backed by | Verified |
|---|---|---|---|
| The service counts visits / CTA clicks / opt-in CLI actions and the counts accumulate | [PROVEN] | `run_analytics_proof` (P-ANALYTICS) | Win + Linux (2026-07-14) |
| Cookie-free and aggregate-only: the store has exactly one `counts(key,n)` table — no ip / cookie / user-agent / per-event data exists to leak | [PROVEN] | `run_analytics_proof` | Win + Linux (2026-07-14) |
| Hostile input is sanitised to `[a-z0-9_.-]` and length-capped; a malformed body → 400 and the server keeps serving; a `DROP TABLE` beacon does nothing | [PROVEN] | `run_analytics_proof` | Win + Linux (2026-07-14) |
| The CLI uploads only the coarse event name, opt-in (consent on **and** endpoint set), never blocking or fatal, never an id/path | [PROVEN] | `core/telemetry.py` (+ P-TELEMETRY) | Win + Linux |

## App-membrane claims (F8 — `metaspace run`)
| Claim | Type | Backed by | Verified |
|---|---|---|---|
| A running Python program is confined to its `.bio` deny-by-default: granted writes really happen (incl. relative paths), undeclared writes / network / subprocess are blocked | [PROVEN] | `run_apprun_proof` (P-APPRUN) | Win + Linux (2026-07-14) |
| A native binary's out-of-scope write is blocked at the kernel (Landlock, EACCES) — a hard boundary | [PROVEN] | `run_apprun_proof` (Landlock leg) | Linux (2026-07-14) |
| The Python backend is a language-level membrane (cross-OS, deny-by-default) but bypassable by adversarial native code; the hard boundary for untrusted binaries is Landlock (Linux) | [SCOPE-LIMIT] | `core/apprun.py` docstring | — |

## Monetisation claims (F6 — open-core licence)
| Claim | Type | Backed by | Verified |
|---|---|---|---|
| `metaspace license` is a real offline Ed25519 gate: only a correctly-signed, unexpired key from the right vendor verifies; tampered / forged / expired keys are rejected | [PROVEN] | `run_license_proof` (P-LICENSE) | Win + Linux (2026-07-14) |
| The free Warden membrane stays zero-dependency; licence crypto is the optional `[pro]` extra and never on the enforcement hot path | [PROVEN] | `run_zerodep_proof` + `core/license.py` | Win + Linux |
| A licence is a soft entitlement gate, not a security boundary; as of this release nothing is gated — every feature runs free | [SCOPE-LIMIT] | `core/license.py` docstring | — |

## Authenticity-gate claims (F7)
| Claim | Type | Backed by | Verified |
|---|---|---|---|
| `metaspace verify` tells a genuine program from AI slop by its observed effects, not its output (HOLLOW / HIDDEN-EFFECT / CONSISTENT) | [PROVEN] | `run_slopgate_proof` (F7) | Win + Linux (2026-07-13) |
| The gate runs the target safely: writes go to a sandbox, network/subprocess are recorded and blocked | [PROVEN] | `run_slopgate_proof` + `core/verify.py` | Win + Linux (2026-07-13) |
| It detects the claims-vs-effects gap for Python programs — NOT general correctness or quality (Rice's theorem) | [SCOPE-LIMIT] | `core/verify.py` docstring | — |

## Control-panel claims (F4 — filled as each work item lands)
| Claim | Type | Backed by | Verified |
|---|---|---|---|
| Each working directory can have its own constitution + mode, all stored user-level (self-protected); the hook resolves per-project and falls back to the default | [PROVEN] | `run_project_config_proof` (F4-1) | Win + Linux (2026-07-13) |
| `metaspace ui` (localhost panel) configures the real membrane per project; the change actually drives the hook | [PROVEN] | `run_ui_proof` (F4-2) | Win + Linux (2026-07-13) |
| The panel defends itself: no-token → 403, and a cross-origin request (a malicious website) → 403 — a web page cannot reconfigure the membrane | [PROVEN] | `run_ui_proof` (F4-2) | Win + Linux (2026-07-13) |
| The friendly UI fields always render a constitution containing the self-protection deny (no UI input can produce a disable-able config) | [PROVEN] | `core/bio_fields.py` (via `run_ui_proof`) | Win + Linux (2026-07-13) |
| The panel can edit an existing folder's rules (change takes effect on the hook) and show per-folder activity | [PROVEN] | `run_ui_proof` (F4-3) | Win + Linux (2026-07-13) |
| Usage telemetry is off by default, opt-in, anonymous, never stores code/paths/PII, and is never on the enforcement hot path | [PROVEN] | `run_telemetry_proof` (F4-3) | Win + Linux (2026-07-13) |
| The panel offers type-to-search command autocomplete and an info list that explains every command; the catalogue is complete, alphabetical, and covers every shipped default | [PROVEN] | `run_commands_proof` + `run_ui_proof` (F4-4) | Win + Linux (2026-07-13) |
| The panel also runs the app membrane (`/api/run`: granted effects allowed, undeclared blocked) and the authenticity gate (`/api/verify`: NO-EFFECTS / HIDDEN-EFFECT), and manages licence status (activate valid / reject invalid / remove), all localhost + token + same-origin | [PROVEN] | `run_ui_proof` (F4-5) | Win + Linux (2026-07-14) |

## Install claims (F1 — filled as each work item lands)
| Claim | Type | Backed by | Verified |
|---|---|---|---|
| The Warden hook + `core/` run with zero third-party dependencies (`wasmtime` is proofs-only) | [PROVEN] | `run_zerodep_proof` (WI-1) | Win + Linux (2026-07-12) |
| One-step user-level install wires the hook into `~/.claude/settings.json` and it then blocks the attack | [PROVEN] | `run_install_proof` (WI-2) | Win + Linux (2026-07-12) |
| A deceived agent cannot disable the membrane (settings/constitution write, or `metaspace off`/`ratify` via Bash) — even in the worst case (project root = home) | [PROVEN] | `run_selfprotect_proof` (WI-3) | Win + Linux (2026-07-12) |
| Install is idempotent and non-clobbering; `metaspace off` reverts cleanly (idempotent, agent-unreachable) | [PROVEN] | `run_install_proof` + `run_uninstall_proof` | Win + Linux (2026-07-13) |
| First run is dry-run/observe (warns, does not block); blocking begins only after `metaspace enforce` | [PROVEN] | `run_dryrun_mode_proof` (WI-4) | Win + Linux (2026-07-12) |
| `metaspace demo` shows the real attack being blocked (falsifiable, not a canned message) | [PROVEN] | `run_demo_proof` (WI-5) | Win + Linux (2026-07-13) |
| Version strings agree across `pyproject.toml`, `.claude-plugin/plugin.json`, and `metaspace --version` | [PROVEN] | `run_version_proof` (WI-6) | Win + Linux (2026-07-13) |
