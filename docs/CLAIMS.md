# Claim & Roadmap Ledger

**This file is the single source of truth for what the project claims, what it plans, and what
blocks it.** Nothing about the project's direction lives anywhere else. Other documents may
*explain* (rationale, architecture, threat models) but may not *contain* a plan.

## The three rules

1. **Claim = proof.** Every user-facing statement must appear here with an ID. If a claim is not
   in this ledger, it must not be published.
2. **The ledger is append-only.** A row is never rewritten, renumbered, or deleted. Direction
   changes by *adding rows* or *changing STATUS with a reason* — never by replacing the plan.
   A step may leave the plan only as `REFUTED` or `WONTDO`, with the reason recorded.
3. **A claim may never assert a stronger guarantee than its TIER.** TIER is an enumeration, not
   prose, so it cannot drift.

## Field definitions

**TIER** — the strength of the guarantee, and the thing that must never be re-litigated:

| TIER | Meaning |
|---|---|
| `HARD` | Unbypassable at the chokepoint. **Requires a stated CONDITION.** |
| `COOPERATIVE` | Holds only if effects are routed through the membrane; adversarial code at a lower level can bypass it. |
| `ADVISORY` | Informational; does not prevent anything. |
| `N/A` | Not a containment guarantee (a factual, property, or scope-limit claim). |

**STATUS** — `PROVEN` · `STATED` · `IN-PROGRESS` · `PLANNED` · `BLOCKED` · `REFUTED` · `WONTDO`

`STATED` is reserved for `[SCOPE-LIMIT]` rows: an honest boundary is *declared and documented*,
not proven by a run. Only `PROVEN` rows are required to name a runnable proof.

**BLOCKED-BY semantics** — an obstacle blocks a claim when the claim **cannot be truthfully
asserted** while the obstacle is OPEN. It is about assertability, not scheduling: work that *is*
the claim (rather than preventing it) belongs in the claim's acceptance criteria, not here.

**TYPE** — `[PROVEN]` (falsifiable proof) · `[MEASURED]` · `[ARCH]` (argued) · `[SCOPE-LIMIT]`
(an honest statement of what is *not* claimed)

**PROOF** — must name a runner present in `run_proofs.py`. **DEPENDS / BLOCKED-BY** — `C-nn` / `O-nn`.

Reproduce everything: `python run_proofs.py` (needs `pip install metaspace-membrane[proofs]`).

---

# Index

| ID | Claim (short) | TIER | STATUS |
|---|---|---|---|
| C-01 | WASM/WASI deny-by-default containment | HARD | PROVEN |
| C-02 | Agent tool calls mediated before execution | HARD | PROVEN |
| C-03 | Friendly Fire prompt-injected RCE unreachable | HARD | PROVEN |
| C-04 | Landlock OS write-containment (native program) | HARD | PROVEN |
| C-05 | Does not make the model injection-proof | N/A | STATED |
| C-06 | Allowlisted interpreter on its own script is allowed | N/A | STATED |
| C-07 | Confining a started process is the substrate's job | N/A | STATED |
| C-08 | Research prototype (TRL ~3–4), no third-party audit | N/A | STATED |
| C-09 | Analytics counts accumulate | N/A | PROVEN |
| C-10 | Analytics cookie-free, aggregate-only by construction | N/A | PROVEN |
| C-11 | Analytics resists hostile input | N/A | PROVEN |
| C-12 | Telemetry uploads only a coarse event name, opt-in | N/A | PROVEN |
| C-13 | Running Python program confined to its `.bio` | COOPERATIVE | PROVEN |
| C-14 | Native binary out-of-scope write blocked at the kernel | HARD | PROVEN |
| C-15 | Python backend is language-level, bypassable | N/A | STATED |
| C-16 | `metaspace license` is a real offline Ed25519 gate | N/A | PROVEN |
| C-17 | Warden path stays zero-dependency | N/A | PROVEN |
| C-18 | Licence is an entitlement gate, not a security boundary | N/A | STATED |
| C-19 | `verify` distinguishes genuine work from slop by effects | N/A | PROVEN |
| C-20 | `verify` runs the target without real effects | COOPERATIVE | PROVEN |
| C-21 | `verify` is claims-vs-effects, not correctness | N/A | STATED |
| C-22 | Per-directory constitutions, resolved per session | N/A | PROVEN |
| C-23 | Panel configures the real membrane | N/A | PROVEN |
| C-24 | Panel rejects no-token and cross-origin requests | HARD | PROVEN |
| C-25 | UI fields always render the self-protection deny | N/A | PROVEN |
| C-26 | Panel edits rules and shows per-folder activity | N/A | PROVEN |
| C-27 | Telemetry off by default, never on the hot path | N/A | PROVEN |
| C-28 | Command catalogue complete and self-explaining | N/A | PROVEN |
| C-29 | Panel exposes `run`, `verify` and licence management | N/A | PROVEN |
| C-30 | Tools help modal in EN/HU/RO | N/A | PROVEN |
| C-31 | Warden hook + `core/` are zero-dependency | N/A | PROVEN |
| C-32 | One-step user-level install, then the attack is blocked | N/A | PROVEN |
| C-33 | A deceived agent cannot disable the membrane | HARD | PROVEN |
| C-34 | Install idempotent; `metaspace off` reverts cleanly | N/A | PROVEN |
| C-35 | First run is observe-mode | N/A | PROVEN |
| C-36 | `metaspace demo` blocks a real attack | N/A | PROVEN |
| C-37 | Version parity across packaging surfaces | N/A | PROVEN |
| C-38 | The decision core is agent-profiled (Anchor decoupled) | N/A | BLOCKED |
| C-39 | Hard containment on a second, named AI agent (Cursor) | HARD | PROVEN |
| C-40 | Any Linux process confined by its `.bio` | HARD | BLOCKED |
| C-41 | MCP-mediated effects contained across MCP servers | — | BLOCKED |
| C-42 | WordPress: compromised plugin cannot write core or exec | HARD | PLANNED |
| C-43 | Cross-OS verification on macOS | N/A | BLOCKED |
| C-44 | Empirical four-variable survey of target agents | N/A | IN-PROGRESS |
| C-45 | Roadmap and claim integrity is machine-checked | N/A | PROVEN |
| C-46 | Ratification is content-bound; only RATIFIED runs, fail-closed | HARD | PROVEN |
| C-47 | Team/CI gate breaks the build on an unratified or widened `.bio` | N/A | PROVEN |
| C-48 | Epistemic hard tier blocks ungrounded facts and actuation | HARD | PROVEN |
| C-49 | Epistemic soft tier flags faithfulness and never blocks | ADVISORY | PROVEN |
| C-50 | Code→constitution synthesis closes the loop without a human step | N/A | PROVEN |
| C-51 | Synthesis is a static heuristic; the runtime membrane is the guarantee | N/A | STATED |
| C-52 | One hook serves both Claude Code and Cursor with identical verdicts | N/A | PROVEN |
| C-53 | Hard containment on agents beyond Claude Code and Cursor | HARD | BLOCKED |

---

# Proven claims

### C-01 — Deny-by-default effect containment at the WASM/WASI chokepoint, per capability kind
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN
**CONDITION:** the guest has zero ambient authority; every effect must traverse a granted
capability import. An import that was never granted is a link error, not a runtime check.
**PROOF:** `run_wasm_demo`, `run_wasi_demo`, `run_real_app_demo`, `bypass_proof`, `run_fuzz`
**VERIFIED:** Win + Linux

### C-02 — Agent tool calls are mediated before they run; obfuscated shell is caught structurally; unreadable input fails closed
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN
**CONDITION:** the host routes every tool effect through the PreToolUse hook, and the hook's
verdict is authoritative (exit 2 ⇒ the call does not execute).
**PROOF:** `test_hook`, `test_shell_policy`, `run_product_e2e`, `run_mcp_e2e`
**VERIFIED:** Win + Linux

### C-03 — A prompt-injected RCE chain (Friendly Fire) is made unreachable: the real payload fires without the membrane, never with it
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN · **DEPENDS:** C-02
**CONDITION:** as C-02. Scope is effect-unreachability at the tool gate; OS containment of an
already-running process belongs to the substrate (see C-07).
**PROOF:** `run_friendly_fire_proof`
**VERIFIED:** Win (verdict) + Linux (full A/B)

### C-04 — OS-level write containment for a stock native program
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN
**CONDITION:** Linux with Landlock ABI ≥ 2. Write-confinement only — read and exec are not
confined in this MVP.
**PROOF:** `run_landlock_demo`
**VERIFIED:** Linux

### C-05 — The membrane does not make the model injection-proof; it contains effects, not the model's prose
`[SCOPE-LIMIT]` · **TIER:** N/A · **STATUS:** STATED
**DOCUMENTED-IN:** `docs/THREAT_FRIENDLY_FIRE.md` §8

### C-06 — An allowlisted interpreter running its own trusted script is allowed by design
`[SCOPE-LIMIT]` · **TIER:** N/A · **STATUS:** STATED
**DOCUMENTED-IN:** `docs/THREAT_FRIENDLY_FIRE.md` §8

### C-07 — Confining a process that has already started is the OS substrate's job, not the agent hook's
`[SCOPE-LIMIT]` · **TIER:** N/A · **STATUS:** STATED
**DOCUMENTED-IN:** `SECURITY.md`, `docs/THREAT_FRIENDLY_FIRE.md` §9

### C-08 — Research prototype / MVP (TRL ~3–4); no third-party security audit yet
`[SCOPE-LIMIT]` · **TIER:** N/A · **STATUS:** STATED
**DOCUMENTED-IN:** `SECURITY.md`

### C-09 — The analytics service counts visits / CTA clicks / opt-in CLI actions, and the counts accumulate
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_analytics_proof` (P-ANALYTICS) · **VERIFIED:** Win + Linux (2026-07-14)

### C-10 — Cookie-free and aggregate-only: the store has exactly one `counts(key,n)` table, so no per-person data exists to leak
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_analytics_proof` · **VERIFIED:** Win + Linux (2026-07-14)

### C-11 — Hostile input is sanitised and length-capped; a malformed body returns 400 and the server keeps serving
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_analytics_proof` · **VERIFIED:** Win + Linux (2026-07-14)

### C-12 — The CLI uploads only the coarse event name, opt-in (consent on **and** endpoint set), never blocking, never an id or path
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_telemetry_proof` (P-TELEMETRY) · **VERIFIED:** Win + Linux

### C-13 — A running Python program is confined to its `.bio` deny-by-default: granted writes really happen, undeclared writes / network / subprocess are blocked
`[PROVEN]` · **TIER:** COOPERATIVE · **STATUS:** PROVEN
**Why not HARD:** the Python backend mediates at the language level (interpreter-level
interception). Adversarial native code inside the process can bypass it. See C-15; the hard
boundary for untrusted binaries is C-14.
**PROOF:** `run_apprun_proof` (P-APPRUN) · **VERIFIED:** Win + Linux (2026-07-14)

### C-14 — A native binary's out-of-scope write is blocked at the kernel (EACCES)
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN
**CONDITION:** Linux with Landlock; write-confinement only.
**PROOF:** `run_apprun_proof` (Landlock leg) · **VERIFIED:** Linux (2026-07-14)

### C-15 — The Python backend is a language-level membrane (cross-OS, deny-by-default) but bypassable by adversarial native code
`[SCOPE-LIMIT]` · **TIER:** N/A · **STATUS:** STATED
**DOCUMENTED-IN:** `core/apprun.py` docstring

### C-16 — `metaspace license` is a real offline Ed25519 gate: tampered, forged and expired keys are rejected
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_license_proof` (P-LICENSE) · **VERIFIED:** Win + Linux (2026-07-14)

### C-17 — The free Warden membrane stays zero-dependency; licence crypto is the optional `[pro]` extra and never on the enforcement hot path
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_zerodep_proof` + `core/license.py` · **VERIFIED:** Win + Linux

### C-18 — A licence is a soft entitlement gate, not a security boundary; as of this release nothing is gated
`[SCOPE-LIMIT]` · **TIER:** N/A · **STATUS:** STATED
**DOCUMENTED-IN:** `core/license.py` docstring

### C-19 — `metaspace verify` tells a genuine program from AI slop by its observed effects, not its output
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_slopgate_proof` · **VERIFIED:** Win + Linux (2026-07-13)

### C-20 — The authenticity gate runs the target safely: writes go to a sandbox, network and subprocess are recorded and blocked
`[PROVEN]` · **TIER:** COOPERATIVE · **STATUS:** PROVEN
**Why not HARD:** same interpreter-level mediation as C-13.
**PROOF:** `run_slopgate_proof` + `core/verify.py` · **VERIFIED:** Win + Linux (2026-07-13)

### C-21 — It detects the claims-vs-effects gap for Python programs — not general correctness or quality (Rice's theorem)
`[SCOPE-LIMIT]` · **TIER:** N/A · **STATUS:** STATED
**DOCUMENTED-IN:** `core/verify.py` docstring

### C-22 — Each working directory can have its own constitution and mode, stored user-level; the hook resolves per project and falls back to the default
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **DEPENDS:** C-33
**PROOF:** `run_project_config_proof` (F4-1) · **VERIFIED:** Win + Linux (2026-07-13)

### C-23 — `metaspace ui` configures the real membrane per project; the change actually drives the hook
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_ui_proof` (F4-2) · **VERIFIED:** Win + Linux (2026-07-13)

### C-24 — The panel defends itself: no token → 403, cross-origin → 403; a malicious web page cannot reconfigure the membrane
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN
**CONDITION:** the panel binds to 127.0.0.1 only and issues a fresh token per launch.
**PROOF:** `run_ui_proof` (F4-2) · **VERIFIED:** Win + Linux (2026-07-13)

### C-25 — The friendly UI fields always render a constitution containing the self-protection deny; no UI input can produce a disable-able config
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **DEPENDS:** C-33
**PROOF:** `core/bio_fields.py` (via `run_ui_proof`) · **VERIFIED:** Win + Linux (2026-07-13)

### C-26 — The panel can edit an existing folder's rules and show per-folder activity
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_ui_proof` (F4-3) · **VERIFIED:** Win + Linux (2026-07-13)

### C-27 — Usage telemetry is off by default, opt-in, anonymous, and never on the enforcement hot path
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_telemetry_proof` (F4-3) · **VERIFIED:** Win + Linux (2026-07-13)

### C-28 — The command catalogue is complete, alphabetical, self-explaining, and covers every shipped default
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_commands_proof` + `run_ui_proof` (F4-4) · **VERIFIED:** Win + Linux (2026-07-13)

### C-29 — The panel runs the app membrane and the authenticity gate, and manages licence status, all localhost + token + same-origin
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **DEPENDS:** C-24
**PROOF:** `run_ui_proof` (F4-5) · **VERIFIED:** Win + Linux (2026-07-14)

### C-30 — The Tools card ships a plain-language help modal in EN / HU / RO explaining `verify` and `run`
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_ui_proof` (F4-6) · **VERIFIED:** Win (2026-07-14); Linux re-run pending

### C-31 — The Warden hook and `core/` run with zero third-party dependencies (`wasmtime` is proofs-only)
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_zerodep_proof` (WI-1) · **VERIFIED:** Win + Linux (2026-07-12)

### C-32 — A one-step user-level install wires the hook into the agent's settings, and it then blocks the attack
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_install_proof` (WI-2) · **VERIFIED:** Win + Linux (2026-07-12)

### C-33 — A deceived agent cannot disable the membrane, even in the worst case (project root = home)
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN
**CONDITION:** the agent's configuration **Anchor** is a local filesystem location placed inside a
`FILESYSTEM deny` scope, and the disabling commands (`metaspace off`, `ratify`) are not
shell-allowlisted. Today the Anchor is `~/.claude`.
**Note:** this CONDITION is what O-1 and O-5 generalise. C-39 restates this claim for a second
agent and cannot be asserted until that agent's Anchor satisfies the same condition.
**PROOF:** `run_selfprotect_proof` (WI-3) · **VERIFIED:** Win + Linux (2026-07-12)

### C-34 — Install is idempotent and non-clobbering; `metaspace off` reverts cleanly and is agent-unreachable
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **DEPENDS:** C-33
**PROOF:** `run_install_proof` + `run_uninstall_proof` · **VERIFIED:** Win + Linux (2026-07-13)

### C-35 — First run is dry-run / observe (warns, does not block); blocking begins only after `metaspace enforce`
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_dryrun_mode_proof` (WI-4) · **VERIFIED:** Win + Linux (2026-07-12)

### C-36 — `metaspace demo` shows the real attack being blocked (falsifiable, not a canned message)
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_demo_proof` (WI-5) · **VERIFIED:** Win + Linux (2026-07-13)

### C-37 — Version strings agree across `pyproject.toml`, `.claude-plugin/plugin.json`, and `metaspace --version`
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_version_proof` (WI-6) · **VERIFIED:** Win + Linux (2026-07-13)

### C-46 — Ratification is content-bound: a policy widened after ratifying is detected as TAMPERED, and only a RATIFIED constitution runs
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN
**CONDITION:** the consuming process loads its constitution through `core.gate` (or
`Guard(..., require_ratified=True)`). Code that bypasses the gate is not covered.
**PROOF:** `run_ratify_demo`, `run_gate_demo`, `run_ratification_review_demo`
**VERIFIED:** Win + Linux

### C-47 — A team/CI gate breaks the build on an unratified or silently widened constitution
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **DEPENDS:** C-46
**Note:** a build-time process control, not a containment boundary — its effect depends on the
repository enforcing the check (e.g. branch protection). No hosted-CI badge is claimed.
**PROOF:** `run_team_gate_e2e` · **VERIFIED:** Win + Linux

### C-48 — The epistemic hard tier blocks ungrounded entities, out-of-schema values and unprovenanced actuation
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN
**CONDITION:** knowledge assertions and actuations are routed through the knowledge membrane;
it is a closed-world check against the declared knowledge base.
**PROOF:** `run_knowledge_demo` · **VERIFIED:** Win + Linux

### C-49 — The epistemic soft tier flags faithfulness but never blocks
`[PROVEN]` · **TIER:** ADVISORY · **STATUS:** PROVEN
**PROOF:** `run_entailment_demo`, `run_threat_matrix_demo` · **VERIFIED:** Win + Linux

### C-50 — Synthesis closes the loop: code → constitution → enforcement with no human step in between, and an effect the app never declared is denied by default
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_synth_demo`, `run_dogfood_demo` · **VERIFIED:** Win + Linux

### C-51 — The code→constitution synthesis is a static heuristic; the runtime membrane, not the synthesis, is the guarantee
`[SCOPE-LIMIT]` · **TIER:** N/A · **STATUS:** STATED
**DOCUMENTED-IN:** `README.md` (Synthesize a constitution from code), `docs/ARCHITECTURE.md`

### C-52 — The same Warden hook runs under both Claude Code and Cursor and reaches identical verdicts on the same effects
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **DEPENDS:** C-02
**Why N/A and not HARD:** this claims *dialect compatibility* — that one hook parses both hosts'
payloads and answers in both contracts. It does **not** claim containment strength on Cursor:
what Cursor actually enforces is bounded by O-11 (post-edit hooks are observational) and by
which effects route through a blocking hook at all. A Cursor TIER may not be asserted until
that is measured per effect kind.
**PROOF:** `run_cursor_compat_proof` (P-CURSOR, 19 checks against a captured real payload)
**VERIFIED:** Win (2026-07-21); Linux pending

---

# Planned and blocked claims

> These rows exist so that a change of topic cannot silently drop them. A planned claim is not a
> commitment to build it next — priority is decided separately. It is a commitment that it will
> not be forgotten, and that it may not be *asserted* before its PROOF exists.

### C-38 — The membrane's decision core is agent-profiled: the configuration Anchor is data, not a hard-coded path
**TIER:** N/A · **STATUS:** BLOCKED · **BLOCKED-BY:** O-1, O-7
**Acceptance:** the Claude profile reproduces byte-identical behaviour (all existing proofs stay
green) **and** a second profile with a different Anchor self-protects correctly.
**PROOF:** *(planned: `run_profile_proof`)*

### C-39 — Hard containment on a second, named AI agent, with verdict-parity against the Claude Code hook
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN · **DEPENDS:** C-38, C-52
**Agent:** Cursor 3.12.17 (runtime version; `package.json` reports the fork's internal 2.3.35).
**CONDITION:** the effect reaches the membrane through Cursor's `preToolUse` step, registered as
a `PreToolUse` hook in `~/.claude/settings.json`, and Cursor honours the verdict. Measured for
`FILESYSTEM/write`; **not** measured for every effect kind, and expressly not via the post-edit
hooks (O-11).
**Measured 2026-07-21:** Cursor's agent attempted a write outside the granted scope using its
file-editing tool (not the terminal). It was blocked and **the file was never created** —
verified on disk, twice, across a Cursor restart. Audit records `host_event=preToolUse`,
`dialect=hybrid`, `host_version=3.12.17`.
**Four variables, all satisfied:** Ingress = `preToolUse`; Vocabulary = 21 steps enumerated;
Egress = block observed, file absent; Anchor = `~/.claude` (already protected by C-33).
**PROOF:** `run_cursor_compat_proof` (P-CURSOR, 24 checks) · **VERIFIED:** Win (2026-07-21); Linux pending

### C-53 — Hard containment on an agent other than Claude Code or Cursor
**TIER:** HARD · **STATUS:** BLOCKED · **BLOCKED-BY:** O-1, O-2, O-5, O-7
**Why this row exists:** C-39 was originally written as a generic "second agent" claim and
inherited these blockers. Cursor turned out to need *none* of them resolved — same `~/.claude`
Anchor (so O-1 never bit), no new adapter (O-2), a local host (O-5), and O-7 was discharged for
Cursor specifically by the survey. The generic ambition is therefore split out here, keeping the
obstacles attached to the claim they actually block rather than to one that is already proven.
**CONDITION:** the four variables must be measured for each new agent, as in C-44 — a host that
lacks a lockable local Anchor cannot reach HARD (O-5).
**PROOF:** *(planned)*

### C-40 — Any Linux process, in any language, is confined to its `.bio`
**TIER:** HARD · **STATUS:** BLOCKED · **BLOCKED-BY:** O-8
**CONDITION:** Linux; syscall/LSM-level scope, coarser than the tool-gate tiers.
**Note:** this claim is Anchor-independent — it does not require the target to cooperate, which
is why it remains available even if C-39 proves unreachable for a given agent.
**PROOF:** *(planned: extends `run_landlock_demo`)*

### C-41 — Effects mediated through arbitrary MCP servers are contained
**TIER:** — · **STATUS:** BLOCKED · **BLOCKED-BY:** O-3, O-4, O-7
**TIER is undecided** and stays `—` until the O-4 architecture is chosen; no containment strength
may be asserted for MCP in the meantime.
**Open architectural question:** per-server capability granularity versus confining the MCP
server process under C-40. The TIER cannot be fixed until this is decided.
**PROOF:** *(planned)*

### C-42 — A compromised WordPress plugin cannot write WordPress core and cannot exec
**TIER:** HARD · **STATUS:** PLANNED · **DEPENDS:** C-40
**CONDITION:** Linux; `php-fpm` launched under the substrate (O-6 is an accepted limit, already
stated in this CONDITION). Serving mode only — plugin/theme
updates require a wider maintenance scope.
**PROOF:** *(planned)*

### C-43 — Cross-OS verification on macOS
**TIER:** N/A · **STATUS:** BLOCKED · **BLOCKED-BY:** O-9
**PROOF:** *(planned: existing suite, run on macOS)*

### C-44 — An empirical, reproducible survey of target agents against the four variables
**TIER:** N/A · **STATUS:** IN-PROGRESS · **Resolves:** O-7 (partially)
**Acceptance:** for each surveyed agent, all four variables recorded with the exact command,
version and config path used to verify them — no inference, no vendor-documentation claims taken
on trust.
**Progress:** **Cursor 2.3.35 surveyed** (2026-07-21) — all four variables recorded from the
shipped bundle (`hooks/types.js` + `hooks/validators/*.js`), not from documentation. Result: a
12-name closed hook vocabulary, real `permission: deny` veto on shell / MCP / file-read, a local
lockable Anchor (`~/.cursor`), and **no pre-write hook** → O-11. Claude Code is the proven
baseline. Cline / Windsurf / Aider / Continue / Copilot remain unsurveyed (not installed), so
O-7 stays OPEN.
**DOCUMENTED-IN:** `docs/AGENT_SURVEY.md`
**PROOF:** *(planned: `run_survey_proof` — structural completeness of the survey: every listed
agent has all four variables filled or explicitly marked unverified)*

### C-45 — The roadmap and claim ledger are machine-checked, not maintained by discipline
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**PROOF:** `run_roadmap_proof` (P-ROADMAP) · **VERIFIED:** Win (2026-07-21); Linux pending
**Falsification-tested:** an untagged guarantee sentence added to `README.md` makes the proof
exit 1 with the correct reason; removing it restores PASS. I4 was flipped from observe to
enforcing on 2026-07-21 once every guarantee-bearing README paragraph traced to a claim.
**Acceptance — the four invariants:**
1. every `PROVEN` row names a PROOF present in `run_proofs.py`;
2. no row is `IN-PROGRESS` while any of its `DEPENDS` is not `PROVEN`;
3. every `OPEN` obstacle forces its blocked claims to `BLOCKED`;
4. every load-bearing public statement traces to a claim ID and does not exceed its TIER
   — **observe-mode first** (reports, does not fail), enforced only once the public surface is aligned.
**PROOF:** *(in progress: `run_roadmap_proof`)*

---

# Obstacle register

> An obstacle is a discovered fact that blocks a claim. Once numbered here it is never
> "rediscovered" — it is either `OPEN`, `RESOLVED` (with how), or `ACCEPTED-LIMIT` (a boundary we
> choose to live with and must state publicly).

| ID | Obstacle | Evidence | Status | Blocks |
|---|---|---|---|---|
| **O-1** | The configuration Anchor `~/.claude` is hard-coded in five places: `core/project_config.py:27`, `core/license.py:106`, `core/telemetry.py:54`, `core/bio_fields.py:59`, `core/apprun.py:46` | verified in code | OPEN | C-38, C-53 |
| **O-2** | `SHELL` is absent from `KINDS` (`core/guard.py:28`) and is handled on a separate path; the allow/deny parse is triplicated across `session_guard_hook.py:92-100`, `core/bio_fields.py:37-39`, `core/provenance.py:51`. Any new adapter mediating exec must re-implement it. | verified in code | OPEN | C-53, C-41 |
| **O-3** | Adding a capability kind changes the provenance fingerprint (`core/provenance.py:51`), which can flip existing RATIFIED constitutions to TAMPERED. Requires a migration, not an edit. | verified in code | OPEN | C-41 |
| **O-4** | MCP tool vocabularies are open-world: tool names are server-defined and unbounded, so there is no sound mapping from a tool call to `(kind, mode, target)`. Schema/description inference would be heuristic classification — i.e. correctness, which this project rejects. | verified by design analysis | OPEN | C-41 |
| **O-5** | For a hosted / SaaS agent the configuration Anchor lives server-side, so no local deny-scope can exist. The HARD tier is therefore structurally unreachable for such agents — a boundary, not a defect. | inferred; needs confirmation per agent | OPEN | C-53 |
| **O-6** | The hard substrate tier is Linux-only (Landlock/seccomp). Windows and macOS have no equivalent in the current design. | verified in code | ACCEPTED-LIMIT | — |
| **O-7** | The ingress mechanism and Anchor location of every candidate target agent (Cursor, Cline, Windsurf, …) are **unverified** — no claim about them may be planned on, let alone published. | not yet verified | OPEN | C-38, C-53, C-41 |
| **O-8** | `core/apprun.py:32` `run_python()` is an interpreter-level monkeypatch set. It is the part that does *not* generalise; the generalising part is `sandbox_enforcer.py` (Linux-only). "Partly done" overstates the substrate's readiness. | verified in code | OPEN | C-40 |
| **O-9** | No macOS machine is available to the project. | stated | OPEN | C-43 |
| **O-10** | The BSL Competing-Use scope and its interaction with the patent position await legal review. Non-blocking for the grant. | stated | OPEN | — |
| **O-13** | **Cursor does not propagate the `env` block from `~/.claude/settings.json` to hooks.** Measured: `mode_from_env=false`, `bio_from_env=false`. Two consequences. (a) `METASPACE_MODE=dryrun` never arrives, so the hook runs in its built-in `enforce` default — safe-by-default, but it defeats the observe-first rollout (C-35): a Cursor user gets hard blocking with no warning session. (b) `METASPACE_SESSION_BIO` never arrives either, so the **shipped** constitution is used, not the user's — per-project configuration made in `metaspace ui` is silently ignored under Cursor. | **empirical run** | OPEN | — |
| **O-11** | **`afterFileEdit` cannot veto a write — confirmed by experiment.** A hook returning `permission: deny` from `afterFileEdit` was ignored: the file was created and persisted (Cursor 3.12.17, 2026-07-21). Consistent with the call site, which awaits the hook result and never inspects it. **Scope narrowed after measurement:** this does *not* prove write containment is impossible on Cursor — `preToolUse` is in the blocking list and receives Claude's `Write`/`Edit`, which is untested. It proves only that the post-edit hooks are observational. | **empirical run** + call site | OPEN | — |
| **O-12** | Cursor's hook payload is **UTF-8 BOM-prefixed** and uses its own dialect (`hook_event_name` + `command`/`file_path`) even when the hook is registered via `~/.claude/settings.json`, and it takes the verdict from a JSON `permission` on stdout, ignoring Claude Code's exit-code-2 contract. Untreated, the Warden fail-closed on every Cursor tool call. **RESOLVED** by three fixes in `session_guard_hook.py`, proven by `run_cursor_compat_proof` against a captured payload. | empirical run | RESOLVED | — |

---

# Superseded planning documents

The following contained forward-looking plans and are demoted. They are kept for their rationale
and history; **their roadmaps are void** and have been dissolved into the rows above.

| Document | New role |
|---|---|
| `docs/AGENT_AGNOSTIC_DESIGN.md` | rationale only — the G1–G4 table is superseded by C-38…C-42 |
| `docs/INSTALL_PLAN.md` | historical (the WI series completed as C-31…C-37) |
| `evidence/DECISIONS.md` | retained, different genre: *why* we decided, not *what* we will do |
