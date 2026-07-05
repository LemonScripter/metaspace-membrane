# Security & threat model

**Status:** research prototype (TRL ~3–4). No third-party security audit yet. This document
states the trust boundary honestly and invites red-teaming.

## Trusted computing base (TCB) — assumed intact
The guarantees hold only if these are sound:
- the WebAssembly runtime (`wasmtime`) correctly enforces the capability model (no ambient authority);
- the host operating system and filesystem (including, for the OS-sandbox path, the Linux kernel's Landlock LSM);
- for the agent membrane: the Claude Code harness delivers `PreToolUse` events faithfully and runs the hook outside the agent;
- the Python interpreter hosting the membrane.

If any of these is compromised, the guarantees do not hold. We do not claim otherwise.

## Attacker model
The attacker **controls the code** that runs — as a WebAssembly guest (Product A) or as the AI
agent whose tool calls are mediated (Product B). That is: the attacker is the possibly
compromised, buggy, or hallucinating generated program / agent. The attacker does **not** control
the constitution (the defender authors and ratifies it), the host runtime, or the OS.

## Guaranteed (hard, and proven by a runnable proof)
- **Deny-by-default effect containment** at the WebAssembly/WASI chokepoint: an ungranted effect is
  unreachable; a granted effect is bounded to its declared scope, per capability kind
  (FS r/w, network, env, subprocess). — `run_wasm_demo`, `run_wasi_demo`, `run_real_app_demo`,
  `bypass_proof`, `run_fuzz` (5000 random cases).
- **Agent tool calls mediated before they run**; obfuscated shell caught structurally; fail-closed on
  unreadable input. Proven end-to-end as a product (the real hook enforces a session, writes an
  audit, and `metaspace report` summarizes it) and across harnesses (the same core decides
  identically via a generic MCP broker). — `test_hook`, `test_shell_policy`, `run_product_e2e`, `run_mcp_e2e`.
- **OS-level write containment (Linux Landlock)**: a stock native program's filesystem writes are
  confined by the kernel to its `.bio` write scope; an out-of-scope write is refused with EACCES.
  Fail-closed if Landlock is unavailable. — `run_landlock_demo` (Linux only).
- **Epistemic hard tier**: no invented entities, values within declared numeric ranges, no ungrounded
  actuation, citation required. — `run_knowledge_demo`.
- **Content-bound ratification + gate**; dry-run-learned capabilities require a justification. —
  `run_ratify_demo`, `run_gate_demo`, `run_ratification_review_demo`.

## NOT guaranteed (honest non-goals)
- The content-level **truth** of a schema-valid statement — only the soft **advisory flag** qualifies
  it (see the threat matrix in `docs/ARCHITECTURE.md`).
- **Free-form prose** — the membrane does not read it.
- The **truth** of an AI-generated ratification justification — only its *presence* is enforced.
- **Static-synthesis completeness** under heavy dynamism — mitigated by the dry-run, not eliminated.
- Anything at all if the **TCB** is compromised.

## How to try to break it (red-team invitation)
Concrete surfaces to attack:
1. **Escape the WASM/WASI sandbox** — reach a file, host, or effect outside the `.bio`. Start from
   `evidence/run_falsification.py` and `evidence/run_fuzz.py` and extend the adversary.
2. **Bypass the structural shell allowlist** with a novel obfuscation — `core/shell_policy.py`.
3. **Smuggle a capability past the ratification brake** without a justification — `core/ratification_review.py`.
4. **Find a `(constitution, effect)` where `guard.check` allows something out of scope** — widen the
   generators in `run_fuzz.py`, change the seed.
5. **Escape the Landlock write-confinement** — get a program under `sandbox_enforcer.py` to modify a
   file outside its `.bio` write scope (note the honest MVP scope: writes only, Linux only).

We welcome counterexamples. The best contribution is a **new failing proof**: a test that the
current code cannot pass. If you find one, it is a real bug, not a rhetorical point.

## Reproduce the evidence
`pip install wasmtime && python run_proofs.py` — **21 proofs** (21/21 on Linux; on non-Linux the
Landlock proof skips, so 20 pass + 1 skip). Each claim maps to a runnable proof; the suite includes
a self-falsification audit that fails if the proofs are hollow.

## Responsible disclosure
Report security issues to **admin@metaspace.bio**.
