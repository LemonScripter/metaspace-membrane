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
| C-38 | The decision core is agent-profiled (host differences are data) | N/A | PROVEN |
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
| C-54 | The user's mode + constitution reach a host that ignores `env` | N/A | PROVEN |
| C-55 | Host binding is generated data, not hand-written per agent | N/A | PLANNED |
| C-56 | Gemini CLI surveyed against the four variables | N/A | IN-PROGRESS |
| C-57 | Hard containment on Gemini CLI, measured | HARD | PLANNED |
| C-58 | The panel shows each detected host, its mode and its achievable tier | N/A | PLANNED |
| C-59 | Self-protection covers every known host anchor, structurally | HARD | PROVEN |
| C-60 | Installing into a second host is merged, backed up and reversible | N/A | PROVEN |
| C-61 | The proof suite is hermetic — results do not depend on the machine | N/A | PROVEN |

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

### C-54 — A host that does not propagate `env` still gets the user's mode and constitution
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **Resolves:** O-13
**Measured problem:** `metaspace install` records the mode and constitution path in the `env`
block of `~/.claude/settings.json`. Claude Code injects them; **Cursor invokes the same hook and
injects nothing** (`mode_from_env=false`, `bio_from_env=false`). The hook fell back to built-in
defaults — enforcing instead of the configured observe-mode, and the *shipped* constitution
instead of the user's, so every rule set in `metaspace ui` silently did nothing on that host.
**Fix:** the settings are mirrored to `~/.claude/metaspace/config.json`, which any host can read.
Precedence: per-project registry → `env` (where the host provides it) → this file → built-in.
Claude Code is unaffected because `env` still wins. `install` / `enforce` / `dryrun` write the
mirror; `off` removes it. Each decision now records `mode_src` so a silent downgrade is visible.
**PROOF:** `run_envless_config_proof` (P-ENVLESS) · **VERIFIED:** Win (2026-07-21); Linux pending

### C-55 — A host's vocabulary binding is generated from the installed agent, not hand-written per agent
**TIER:** N/A · **STATUS:** PLANNED · **DEPENDS:** C-44 · **Related:** C-38
**Idea (user, 2026-07-21):** read an agent's own names/IDs once per installed version and bind
them to the membrane automatically, instead of authoring an adapter per agent.
**Design constraint that must hold:** the binding is a **separate artefact**, never part of the
`.bio`. Putting host vocabulary into the constitution would couple policy to vendor internals,
break portability across agents, and change the provenance fingerprint on every agent update —
flipping RATIFIED to TAMPERED (O-3) each time the vendor ships.
**Acceptance:** (a) the dialect/vocabulary table becomes data rather than code; (b) the first
live invocation *confirms* the generated profile against what the host actually sends, and
**fails closed** on mismatch rather than silently under-protecting; (c) the semantic map
(name → effect kind) stays human-authored, per name, not per version.
**Evidence it is needed and bounded:** static extraction produced the vocabulary and veto
contracts correctly, but got the payload dialect, the BOM, `env` propagation and deny-honouring
wrong — all four required a run. Detection can automate discovery; it cannot substitute for
verification. The diagnostics added for C-52/C-54 already collect what (b) needs.
**PROOF:** *(planned)*

---

# Planned and blocked claims

> These rows exist so that a change of topic cannot silently drop them. A planned claim is not a
> commitment to build it next — priority is decided separately. It is a commitment that it will
> not be forgotten, and that it may not be *asserted* before its PROOF exists.

### C-38 — The membrane's decision core is agent-profiled: the configuration Anchor is data, not a hard-coded path
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN
**What it claims:** what differs between agents is a table, not a code path. Three surveyed hosts
differ in spelling and never in meaning — `PreToolUse` / `preToolUse` / `BeforeTool`, `Bash` /
`run_shell_command`, `Write` / `write_file` — and none of it reaches `core.guard`, which still
decides on a normalized `(kind, mode, target)`. Adding a host is a row in `core/hosts.py`.
**Two design rules it pins, both arrived at by getting them wrong first:**
· host vocabulary never enters the `.bio` — a constitution naming host internals would lose
  portability and flip RATIFIED to TAMPERED on every vendor update (O-3);
· the verdict is emitted as a **superset** — `permission` (Cursor), `decision` + `reason`
  (Gemini), exit code 2 (Claude Code) all at once — rather than identifying the caller and
  guessing its dialect. A wrong guess means the verdict goes unheard, which is exactly how the
  membrane ended up inert under Cursor.
**Acceptance met:** all existing proofs stay green (byte-identical behaviour for Claude Code),
and multiple anchors self-protect (C-59).
**PROOF:** `run_hostprofile_proof` (P-HOSTS) · **VERIFIED:** Win (2026-07-21); Linux pending

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

### C-56 — Gemini CLI surveyed against the four variables
**TIER:** N/A · **STATUS:** IN-PROGRESS · **Extends:** C-44
**Gemini CLI 0.50.0** (npm `@google/gemini-cli`), read from its **unminified** bundle — original
source paths and comments intact, so extraction confidence is far higher than for Cursor.
· **Ingress:** `BeforeTool` — *"Can intercept, validate, or modify tool calls"*; also
  `BeforeModel`, `AfterModel`, `BeforeToolSelection`.
· **Vocabulary:** events `BeforeTool/AfterTool/BeforeAgent/AfterAgent/SessionStart/SessionEnd/
  PreCompress/Notification`; tools `run_shell_command`, `write_file`, `replace`, `read_file`,
  `glob`, `grep`, `ls`.
· **Egress:** `isBlockingDecision() = decision === "block" || decision === "deny"`; also
  `continue: false` stops the agent, and a BeforeTool hook may rewrite the tool input. Verified
  at the call site in `executeToolWithHooks`.
· **Anchor:** `~/.gemini/settings.json`, `hooks.BeforeTool[]`; four sources — project, user,
  system, extension.
· Ships an official `gemini hooks migrate` that converts Claude Code hook configs.
**Still missing:** an actual run. Static reading is stronger here than for Cursor, but the BOM
class of surprise only appears at runtime.
**DOCUMENTED-IN:** `docs/AGENT_SURVEY.md`

### C-57 — Hard containment on Gemini CLI, measured
**TIER:** HARD · **STATUS:** PLANNED · **DEPENDS:** C-56, C-38
**CONDITION (required before this may be asserted):** the effect reaches the membrane through
Gemini's `BeforeTool` step, Gemini honours a `decision: "deny"` verdict, **and** `~/.gemini` is
itself inside a `FILESYSTEM deny` scope so the agent cannot uninstall the hook it is subject to.
The third clause is not optional: without it the guarantee is self-undermining.
**Why blocked, and it is not a formality:** Cursor was free because it *borrows* Claude's anchor
(`~/.claude/settings.json`), so O-1 never bit. Gemini uses its own (`~/.gemini/settings.json`).
Installing there without extending self-protection to that anchor would hand a deceived agent a
fresh way to switch the membrane off — see O-14. HARD may not be asserted for Gemini until the
anchor it is installed into is itself defended.
**PROOF:** *(planned)*

### C-58 — The control panel shows each detected host, its mode, and the tier actually achievable there
**TIER:** N/A · **STATUS:** PLANNED · **DEPENDS:** C-56
**Why this is load-bearing, not cosmetic:** the panel currently speaks of one host ("the folder
where you run Claude Code") and shows a single protected/unprotected state. With three hosts
whose achievable tiers differ per effect kind — Cursor's post-edit hooks are observational
(O-11), Gemini's BeforeTool can even rewrite tool input — one combined indicator would be false.
The TIER matrix the ledger enforces in text has to reach the surface the user actually looks at,
or the hard/soft conflation returns through the UI.
**Must also surface:** per-host install state (separate anchors, separate files) and host-specific
caveats such as O-13.
**PROOF:** *(planned)*

### C-59 — Self-protection covers every known host's config anchor, and does not depend on the constitution's text
`[PROVEN]` · **TIER:** HARD · **STATUS:** PROVEN · **DEPENDS:** C-33 · **Resolves:** O-14
**CONDITION:** the effect passes through the agent hook, and the host's anchor appears in
`core/agent_anchors.py`. A host whose anchor is unknown to that list is not covered — adding a
host means adding its anchor, and that is the one manual step this claim depends on.
**Why it is enforced from code, not from the `.bio`:** the deny used to be a single
`{{CLAUDE_HOME}}` line emitted into each generated constitution. That covered Claude Code and,
by luck rather than design, Cursor — which reads the same `~/.claude/settings.json`. Gemini has
its own anchor. A constitution written before a host existed cannot name it, and a hand-edited
one may have had the line removed, so a text-based guarantee is one edit or one release behind.
The hook now injects the anchor scopes into the guard's deny set directly. Anchors are only ever
added to the DENY side, so a wrong entry over-blocks (loud, correctable) rather than opening a
silent hole.
**PROOF:** `run_multianchor_proof` (P-ANCHORS) — driven with a deliberately **legacy**
constitution that denies only `{{CLAUDE_HOME}}`, in the worst case where the project is opened
at the home directory so every anchor sits inside the granted write scope. `~/.cursor/hooks.json`
and `~/.gemini/settings.json` are blocked anyway; reads still pass; a look-alike directory
(`.claudette`) is not over-blocked.
**VERIFIED:** Win (2026-07-21); Linux pending

### C-60 — Installing into a second host preserves the user's config, is reversible, and refuses to guess
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **DEPENDS:** C-38
**Why this is a claim and not a footnote:** writing into somebody's editor configuration is the
most destructive thing this tool does. A membrane that eats a user's config in order to protect
them has not helped. The properties matter more than the feature.
· **Non-clobbering** — unrelated settings and third-party hooks on the same event survive.
· **Backed up** — a `.metaspace.bak` is written before the first modification.
· **Idempotent** — installing twice leaves one entry.
· **Host-native shape** — the Gemini entry uses `BeforeTool` and Gemini's own tool names in the
  matcher; no Claude vocabulary leaks in.
· **Refuses rather than guesses** — a host whose config location is unknown is declined with a
  reason (O-16). Writing a file nothing reads would look like success and protect nothing.
· **Fails safe on damage** — a malformed config is reported, never overwritten.
`--dry-run` reports the intended change without touching the file or creating a backup.
**PROOF:** `run_multihost_install_proof` (P-INSTALL-HOSTS, 24 checks, throwaway HOME)
**VERIFIED:** Win (2026-07-21); Linux pending

### C-61 — The proof suite is hermetic: its result does not depend on the machine it runs on
`[PROVEN]` · **TIER:** N/A · **STATUS:** PROVEN · **Resolves:** O-17
**How it was found:** after C-54 made the user-level config file authoritative for hosts that do
not propagate `env`, four core proofs (`test_hook`, `run_friendly_fire_proof`, `run_product_e2e`,
`run_mcp_e2e`) began failing on a machine whose real `~/.claude/metaspace/config.json` said
`dryrun`. None of them set `METASPACE_MODE`; all silently relied on "unset means enforce". The
proofs were reading the developer's own membrane configuration — so the evidence depended on the
state of the machine producing it, which is precisely what `claim = proof` cannot tolerate.
**Fix:** `run_proofs.py` pins a hermetic baseline for every child (`METASPACE_MODE=enforce`, no
inherited `METASPACE_SESSION_BIO`). Proofs that exercise other modes set them on their own child
environment and are unaffected. Verified with a developer config still set to `dryrun`: the whole
suite passes, where four proofs previously failed.
**Side effect worth noting:** an installed Warden's environment used to leak into the suite and
cause false failures, which required running it as `env -u METASPACE_MODE -u METASPACE_SESSION_BIO`.
That workaround is no longer needed.
**PROOF:** `run_hermeticity_proof` (P-HERMETIC) — reproduces the pollution against a real hook
run, shows the baseline neutralising it, and checks the runner actually passes it to children.
**VERIFIED:** Win (2026-07-21)

---

# Obstacle register

> An obstacle is a discovered fact that blocks a claim. Once numbered here it is never
> "rediscovered" — it is either `OPEN`, `RESOLVED` (with how), or `ACCEPTED-LIMIT` (a boundary we
> choose to live with and must state publicly).

| ID | Obstacle | Evidence | Status | Blocks |
|---|---|---|---|---|
| **O-1** | The configuration Anchor `~/.claude` is hard-coded in five places: `core/project_config.py:27`, `core/license.py:106`, `core/telemetry.py:54`, `core/bio_fields.py:59`, `core/apprun.py:46` **Resolved by C-38 + C-59:** host vocabulary and config anchors are now data (`core/hosts.py`, `core/agent_anchors.py`) and the anchor denies are injected from code. The membrane's OWN storage path was split out as O-15, since it blocks nothing. | verified in code | RESOLVED | — |
| **O-2** | `SHELL` is absent from `KINDS` (`core/guard.py:28`) and is handled on a separate path; the allow/deny parse is triplicated across `session_guard_hook.py:92-100`, `core/bio_fields.py:37-39`, `core/provenance.py:51`. Any new adapter mediating exec must re-implement it. | verified in code | OPEN | C-53, C-41 |
| **O-3** | Adding a capability kind changes the provenance fingerprint (`core/provenance.py:51`), which can flip existing RATIFIED constitutions to TAMPERED. Requires a migration, not an edit. | verified in code | OPEN | C-41 |
| **O-4** | MCP tool vocabularies are open-world: tool names are server-defined and unbounded, so there is no sound mapping from a tool call to `(kind, mode, target)`. Schema/description inference would be heuristic classification — i.e. correctness, which this project rejects. | verified by design analysis | OPEN | C-41 |
| **O-5** | For a hosted / SaaS agent the configuration Anchor lives server-side, so no local deny-scope can exist. The HARD tier is therefore structurally unreachable for such agents — a boundary, not a defect. | inferred; needs confirmation per agent | OPEN | C-53 |
| **O-6** | The hard substrate tier is Linux-only (Landlock/seccomp). Windows and macOS have no equivalent in the current design. | verified in code | ACCEPTED-LIMIT | — |
| **O-7** | The ingress mechanism and Anchor location of every candidate target agent (Cursor, Cline, Windsurf, …) are **unverified** — no claim about them may be planned on, let alone published. | not yet verified | OPEN | C-53, C-41 |
| **O-8** | `core/apprun.py:32` `run_python()` is an interpreter-level monkeypatch set. It is the part that does *not* generalise; the generalising part is `sandbox_enforcer.py` (Linux-only). "Partly done" overstates the substrate's readiness. | verified in code | OPEN | C-40 |
| **O-9** | No macOS machine is available to the project. | stated | OPEN | C-43 |
| **O-10** | The BSL Competing-Use scope and its interaction with the patent position await legal review. Non-blocking for the grant. | stated | OPEN | — |
| **O-17** | The proof suite inherited the developer's own membrane configuration: most proofs never set `METASPACE_MODE` and relied on "unset means enforce". Once C-54 made the user-level config authoritative, a real config saying `dryrun` failed four core proofs — evidence that depended on the machine. **Resolved by C-61** (hermetic baseline in `run_proofs.py`). | **empirical run** | RESOLVED | — |
| **O-16** | **Antigravity CLI (`agy`) is detected but not surveyable statically.** A 156 MB Go binary whose string table is fully concatenated, so — unlike Cursor's JS and Gemini's unminified bundle — the hooks config path cannot be read out. Evidence it *has* a hook system: `hooks.json` (19 occurrences), `PreToolUse`/`PostToolUse`, `"unsupported hook type: %q"`, `"No hooks.json found at %s"`, and a `hooks_manager.go` log line *loaded 0 named hooks from 0 hooks.json file(s)*. **Discovery method (cheap, empirical):** drop a marker `hooks.json` in each candidate location and watch that count go 0→1. Until then the profile records the path as unknown and install is refused (C-60). | verified in vendor binary | OPEN | a future Antigravity claim |
| **O-15** | The membrane's own state (`project_config`, `license`, `telemetry`) lives under `~/.claude/metaspace` — inside *one host's* config directory. A Gemini-only user gets a stray `~/.claude` tree, and `metaspace off --purge` on the Claude side would delete state other hosts still rely on. Split out of O-1: architectural and a minor purge bug, **not** a security issue, and it blocks no claim. | verified in code | OPEN | — |
| **O-14** | **Self-protection covers only one anchor.** Every generated constitution denies `{{CLAUDE_HOME}}/**` (`core/bio_fields.py`), which defends the Claude Code config — and, because Cursor reads that same file, Cursor too. **Gemini uses its own anchor** (`~/.gemini/settings.json`). Installing into a new host without extending the deny to that host's anchor gives a deceived agent a fresh route to disable the membrane there: exactly the attack C-33 exists to stop. Also affects any per-project constitution written before a new anchor was known. **Resolved by C-59:** the anchors are injected from code, so constitutions written before a host existed — or hand-edited — are protected too. | verified in code | RESOLVED | — |
| **O-13** | **Cursor does not propagate the `env` block from `~/.claude/settings.json` to hooks.** Measured: `mode_from_env=false`, `bio_from_env=false`. Two consequences. (a) `METASPACE_MODE=dryrun` never arrives, so the hook runs in its built-in `enforce` default — safe-by-default, but it defeats the observe-first rollout (C-35): a Cursor user gets hard blocking with no warning session. (b) `METASPACE_SESSION_BIO` never arrives either, so the **shipped** constitution is used, not the user's — per-project configuration made in `metaspace ui` is silently ignored under Cursor. **Resolved by C-54** (settings mirrored to a file every host can read). | **empirical run** | RESOLVED | — |
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
