# Agent-Agnostic Membrane — Design Rationale

> ## ⚠️ This document no longer contains a plan
> **The roadmap that used to live in §8 is void.** It has been dissolved into rows C-38…C-42 of
> **`docs/CLAIMS.md`**, which is now the single source of truth for what the project claims,
> plans, and is blocked by — machine-checked by `run_roadmap_proof` (P-ROADMAP).
>
> What remains here is **rationale**: the analysis of *why* the generalisation is shaped this
> way. Rationale is durable; plans are not. Do not add a schedule, a phase list, or a priority
> order to this file — add a row to the ledger instead. Recorded as I-48.

**Status:** design rationale (2026-07-19; demoted to rationale-only 2026-07-21).
Original decision: I-47. Superseding decision: I-48 in `evidence/DECISIONS.md`.
**Thesis:** *containment, not correctness* — one `.bio` constitution, enforced at whatever
boundary the effect-emitter exposes, deny-by-default.

This document is the canonical plan for generalizing the membrane from "the Claude Code
Warden" to a universal effect-containment layer. It is grounded in the current code, not
aspiration: the decision core is already harness-independent, and two adapters already prove it.

---

## 1. The seam already exists

`core/agent_adapter.py::decide(kind, mode, target, guard)` decides a **normalized effect**:

```
(kind, mode, target)   kind ∈ {SHELL, FILESYSTEM, NETWORK, ENV, SUBPROCESS, …}
```

Two adapters already map their world onto it and prove the core is generic:

- **Claude Code PreToolUse hook** (`products/ai_membrane/session_guard_hook.py`) — maps
  `{tool_name, tool_input}` → `(kind, mode, target)`; enforces with exit code 2 (block).
  Pattern: **interception (veto)**.
- **Generic MCP capability-broker** (`products/mcp_membrane/server.py`) — exposes mediated
  effect tools; every effect goes through the broker. Pattern: **brokering (mediation)**.

Generalization is therefore **not "one new adapter"** but recognizing that every effect-emitter
differs in exactly three places, and the core is independent of all three:

| Variable | Claude Code | What varies per target |
|---|---|---|
| **Ingress** — how the intended effect is observed | PreToolUse JSON on stdin | per target |
| **Vocabulary** — tool/call → effect | Write/Edit/Bash… | per target |
| **Egress** — how a deny actually stops the effect | exit code 2 | per target |

---

## 2. Two generalization axes (do not conflate them)

| Axis | Question | Mechanism | Examples |
|---|---|---|---|
| **1 — Agent breadth** | how many *AI agents* do we protect? | hook / MCP-proxy / library adapters | Claude Code, Cursor, LangChain |
| **2 — Program breadth** | can we confine *any program*? | **OS substrate** (Landlock/seccomp + `.bio`) | WordPress, a binary, an AI-written script |

Axis 1 is about how an AI agent *emits* effects. Axis 2 is language/runtime generalization:
confine a process at a boundary you control, regardless of whether it is an "agent".

---

## 3. Agent taxonomy (Axis 1) — where effects cross a boundary you control

| # | Agent type | Examples | Enforcement pattern | Hardness |
|---|---|---|---|---|
| 1 | Hook agent | Claude Code | pre-tool hook adapter | hard on the agent |
| 2 | MCP agent | Cursor, Cline, Claude Desktop, Windsurf | **MCP proxy** (in front of real MCP servers) | hard if all effects route through MCP |
| 3 | Function-calling agent | OpenAI/Anthropic SDK loop, LangChain, LlamaIndex | **library decorator** (`@membrane.mediate`) | cooperative guardrail (your own agent) |
| 4 | Ambient-code agent | code interpreter, autonomous coder without a hook | **substrate** (`metaspace run`: WASM/Landlock) | hard, coarser (OS scope) |
| 5 | Black-box / hosted | SaaS agent | **network proxy / syscall filter** at the boundary you own | only what the boundary permits |

---

## 4. The unifying insight — the OS substrate is the truly universal membrane

`.bio` + Landlock/seccomp confines a Linux **process**, and it does not care whether that
process is an AI agent, an AI-written script, or `php-fpm`. Same core, same `.bio` grammar,
same deny-by-default. This is exactly the DCC pillar: *bounds which effects code may cause,
for ANY program*. Precedent: `dcc-shield` already confines a non-AI process (AUR builds,
Landlock + namespaces). WordPress protection is an **application of this pillar, not a pivot**.

Consequence: **Axis-2 work (confine any process) simultaneously delivers (a) the substrate
fallback for un-hookable agents and (b) WordPress/any-app protection.** One engine, two payoffs.

---

## 5. The `AgentAdapter` contract (the seam, made explicit)

Today the "map event → effect" + "enforce verdict" logic is implicit and duplicated (hook +
broker). Promote it to a documented, tested interface in `core/`:

```python
class AgentAdapter:
    def normalize(self, event) -> list[Effect]:      # target event → normalized effects
        ...
    def enforce(self, effect, verdict) -> Response:  # verdict → the target's own language
        ...                                          # (exit code / JSON-RPC error / exception)
```

`decide()` in the middle is unchanged. Every new target = a thin `AgentAdapter` subclass plus a
tool-name table. This makes "the same core on a different harness" literally true, not a slogan.

---

## 6. Honest guarantee ladder (anti-slop — always state the condition)

| Pattern | Guarantee | Condition |
|---|---|---|
| Hook / MCP-proxy interception | hard on the agent | the host routes ALL effects through the hook/proxy |
| Broker | hard | ambient authority removed (broker tools are the only effect path) |
| Library decorator | **cooperative** | the developer routes ALL effects through it — a guardrail for *your* agent, not containment of a hostile one |
| Substrate (WASM/Landlock/seccomp) | hard, unbypassable | coarser (OS/syscall scope); the hard tier is Linux |

The membrane's guarantee is always "at the chokepoint you control." This table is the set of
supported chokepoints.

---

## 7. WordPress as a substrate application (worked example, Axis 2)

WordPress is a PHP application (taxonomy #4–#5): no tool boundary to intercept, so it is the
substrate line, not the adapter line. Its effects map onto the same `(kind, mode, target)`:

```bio
CELL WordPressSite {
  CAPABILITIES {
    # WordPress may write ONLY to uploads/cache — core + plugins are READ-ONLY at runtime
    FILESYSTEM write "{{WP_ROOT}}/wp-content/uploads/**";
    FILESYSTEM write "{{WP_ROOT}}/wp-content/cache/**";
    FILESYSTEM read  "{{WP_ROOT}}/**";
    # outbound network only to update servers — a compromised plugin cannot exfiltrate
    NETWORK    out   "api.wordpress.org", "downloads.wordpress.org";
    # no exec/system/shell_exec — removes the #1 RCE vector
    SUBPROCESS deny;
  }
}
```

Value proposition: *a WordPress that physically cannot overwrite its own core, cannot exec, and
cannot phone home — even when a plugin is compromised.* This defeats the common **outcome** of a
WP compromise, without auditing any plugin.

**Two-tier enforcement:**
- **Hard tier (OS):** launch `php-fpm` under Landlock (file scope) + seccomp (`execve` block);
  the whole worker pool inherits it. Unbypassable, Linux-only, coarser.
- **Soft tier (PHP):** an `auto_prepend_file` mu-plugin routing dangerous functions
  (`file_put_contents`, `exec`, `curl`) through the membrane. Cooperative (raw syscalls bypass)
  but catches real-world plugin misbehavior and AI-generated slop.

**Honest limits specific to WordPress:**
1. Legitimate WP writes to `wp-content` (plugin/theme install, updates) → needs a **maintenance
   mode** (wider scope during updates) vs **serving mode** (locked), analogous to observe/enforce.
2. Host-level network allowlist is hard at the OS layer (Landlock network is port-level in ABI v4)
   → needs a userspace proxy or eBPF. Coarser than the FS/exec tiers.
3. Database (SQL) is not an OS effect → a new `DATABASE` kind + a DB proxy or WP db-layer hook.
4. `php-fpm` is a long-running daemon, not a one-shot script → generalize `metaspace run` from
   one-shot to service launch (Landlock applies at launch; clean).

---

## 8. Roadmap — moved to the ledger

**The G1–G4 phase table that stood here is void (I-48).** It described work; the project now
tracks *claims* instead, because a claim carries its own falsifiability while a phase does not.

| Former phase | Now tracked as |
|---|---|
| G1 — `AgentAdapter` contract | **C-38** — the decision core is agent-profiled (Anchor is data) |
| G2 — MCP proxy | **C-41** — effects through arbitrary MCP servers are contained |
| G3 — universal substrate | **C-40** — any Linux process is confined to its `.bio` |
| G4 — WordPress PoC | **C-42** — a compromised plugin cannot write core or exec |
| — (newly surfaced) | **C-39** — hard containment on a second, named agent |
| — (newly surfaced) | **C-44** — empirical four-variable survey of target agents |

Two things the phase table could not express, and the ledger does:

1. **Preconditions are data.** Each row names the obstacles that block it (`O-1`…`O-10`), so an
   obstacle discovered during analysis is recorded once and never rediscovered as "new".
2. **Sequencing is not baked in.** The former table asserted G2-before-G3 on adoption grounds.
   That ordering is a *decision*, not a property of the work, and it is not settled here — see
   §4 and §6 for the analysis that bears on it. Priority is chosen against the ledger, where all
   dependencies and blockers are visible at once.

Each claim still ships a falsifiable proof in `run_proofs.py` (claim = proof) — now enforced by
P-ROADMAP rather than by discipline.

---

## 9. Positioning & monetization alignment

- **Positioning (honest):** the membrane does not *detect* hallucination; it makes the *effect*
  of a hallucinating/deceived/malicious agent unreachable. Containment, not correctness. Carry
  the landing's line forward: "the agent can be completely deceived — the harmful effect still
  cannot occur."
- **Monetization (BSL):** the license reserves "a commercial safety-membrane product/service"
  (Competing Use). The **MCP proxy** (team/enterprise agent-fleet protection) and the
  **universal substrate** (hosting / WordPress protection as a service) are the natural **Pro**
  surface — the core stays free (adoption), the managed/hosted proxy + substrate orchestration
  is paid.
