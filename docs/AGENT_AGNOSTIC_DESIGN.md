# Agent-Agnostic Membrane — Design & Roadmap (canonical)

**Status:** design canon (2026-07-19). Decision recorded as I-47 in `evidence/DECISIONS.md`.
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

## 8. Roadmap (G-phases)

| Phase | Content | Note |
|---|---|---|
| **G1** | `AgentAdapter` contract (refactor, zero behavior change) + proof | everything else rides on it; hook + broker re-seated onto it |
| **G2** | **MCP proxy** (interception) in front of real MCP servers + proof with a real MCP agent | Axis 1 — biggest ecosystem reach with one integration |
| **G3** | **Universal substrate**: generalize `metaspace run` from one-shot Python to any process/language via Landlock/seccomp | Axis 2 — protects agent-made programs (partly exists: `run` / `verify`) |
| **G4** | **WordPress PoC** on the G3 substrate (`php-fpm` confined; proof: "compromised plugin cannot write core / cannot exec") | Axis 2 applied, a separate PoC |
| later | `DATABASE` kind · JS/TS SDK (decorator + Node MCP proxy) · per-host hook tables (Cursor/Cline/Aider) | as demand arrives |

Each phase ships a new falsifiable proof in `run_proofs.py` (claim = proof).

**Sequencing rationale:** G2 extends the just-launched product to the whole MCP ecosystem
(maximal near-term adoption). G3 is the universal substrate — and it is the *same engine* that
G4 (WordPress) rides on, so G3 is not a detour before WordPress; it is what makes WordPress a
small PoC. Anti-regress: substrate targets (WordPress and others) stay separate PoCs so they
never fork focus from the primary product line.

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
