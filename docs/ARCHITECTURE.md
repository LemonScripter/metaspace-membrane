# MetaSpace.Bio Engine — Architecture & technical background

> **One `.bio` constitution, three membranes, two products.** A deterministic,
> deny-by-default reference monitor that turns an *undecidable* question (`is the AI doing
> the right thing?`) into a *decidable* one (`is the effect inside the declared boundary?`).
>
> MetaSpace.Bio Engine Project — Szőke László-Ferenc (admin@metaspace.bio). **Patent pending.**

---

## 0. The core thesis: containment, not correctness

The classic question — *"does the code do what its author intended?"* — is **undecidable**
by Rice's theorem (any non-trivial semantic property of an arbitrary program is undecidable).
So proving intent-correctness does not scale.

MetaSpace **replaces the question**:

| | Question | Status |
|---|---|---|
| ~~Correctness~~ | Is the program right? | undecidable |
| **Containment** | Is the program's **effect** inside the declared boundary? | **decidable** (set membership) |

This substitution is what makes the decision **deterministic**, **constant-time in nature**,
and **verifiable**. It rests on the `.bio` language being **Turing-incomplete** → every
program is finite → the policy itself is verifiable.

**Consequence for the definition of a bug:** *a bug = a deviation from the constitution*.
That makes "a bug" machine-measurable and enforceable.

---

## 1. One pattern, three membranes

All three membranes are **the same pattern**: a reference monitor at a **chokepoint**,
**deny-by-default**, with the decision made by the **constitution**.

```
                    +---------------- constitution.bio ----------------+
                    |  CAPABILITIES {}     INVARIANTS {}    KNOWLEDGE {} |
                    +------+-------------------+-------------------+-----+
                           |                   |                   |
                    +------v------+     +-------v------+    +-------v-------+
                    | CAPABILITY  |     |   VALUE-     |    |  EPISTEMIC    |
                    | membrane    |     |  INVARIANT   |    |  membrane     |
                    | (effects)   |     |  (safety)    |    |  (facts)      |
                    +-------------+     +--------------+    +---------------+
```

| Membrane | Mediates | Harm class it contains |
|---|---|---|
| **Capability** | Effects on the world (FS/NET/ENV/SUBPROCESS/HARDWARE/IMPORT) | Effect hallucination (deletes, exfiltrates) |
| **Value invariant** | Safety bounds (numeric ranges; e.g. temperature, current, motion) | Value violation (crosses an invariant) |
| **Epistemic** | Factual assertion and knowledge-based actuation | Fact hallucination (acts on false data) |

> **Honest note on the value-invariant membrane.** In *this* repository, numeric value bounds are
> enforced as the hard tier's schema/domain **`RANGE`** check (`core/knowledge_membrane.py`, proven
> in `run_knowledge_demo`) — i.e. it is realized *inside* the epistemic-hard membrane rather than as
> a separate third enforcer. The IoT examples (temperature/current/motion) are illustrative of the
> broader MetaSpace.Bio programme and are not separately proven here.

---

## 2. The guarantee ladder (the heart of the honesty)

A membrane's guarantee is **exactly as hard as the chokepoint is unbypassable.** The system
**never claims a soft layer is hard.**

```
  heuristic     static analyzer, bash denylist        ADVISORY — can be fooled
       |
  language       monkeypatch guard                    BYPASSABLE — ctypes / syscalls
       |
  harness        session hook (PreToolUse)            HARD for the agent — sits outside it
       |
  WebAssembly    capability import                    UNBYPASSABLE — nothing to bypass
```

**Empirical proof of the top rung:** a guest that tries to reach an ungranted gate
(`wasi path_open`) fails with a link error (`unknown import`). No "forgotten syscall", no
ambient authority. → `products/app_membrane/bypass_proof.py`

---

## 3. Composition of the membranes (the deep insight)

No membrane is sufficient alone; they compose in **defense-in-depth**.

The epistemic membrane alone is only **advisory** — a malicious app could simply *not call*
`actuate()`. **It becomes hard behind the capability membrane:**

```
  CAPABILITY membrane (WebAssembly)  =>  guarantees the ONLY path to the world is the host gate
             |
  EPISTEMIC membrane                 =>  sits in the host gate's implementation -> provenance check
             v
  TOGETHER: no other actuation path (WebAssembly), and what passes is grounded (KNOWLEDGE)
```

- **The capability membrane** guarantees an unbypassable chokepoint *exists*.
- **The epistemic membrane** guarantees that *what passes through it* is grounded.
- **The agent membrane** applies the same to the developer agent itself.

---

## 4. Epistemic membrane: hard vs soft

**HARD tier** (deterministic, decidable → verifiable):

1. **Referential integrity** — closed-world: you cannot assert a non-existent entity.
2. **Schema/domain** — enum membership, numeric range, type, ref integrity.
3. **Provenance-locked actuation** — a side-effect only from a granted source (not the model's imagination).
4. **Citation obligation** — every factual assertion requires a known `SOURCE`.

**SOFT tier** (NOT deterministic — honestly not enforced):

- Semantic faithfulness / entailment (does the text follow from the source). Pluggable backends
  (`core/entailment.py`): a dependency-free **heuristic** (figure/term presence — catches invented
  numbers) and a **Claude LLM judge** (`claude` backend, the production path). `soft_entailment()`
  **flags** the verdict and never **blocks** — the hard tier enforces, this tier informs.

**Strict terminology (claim = proof, no more and no less).** The epistemic **hard tier** is a real
deterministic **membrane** — it *contains* (blocks). The epistemic **soft tier** is deliberately
*not* a membrane; it is an **advisory flag** — it *qualifies* (flags), never contains. We use these
words consistently so the name never claims more than the code proves.

**Threat-model matrix (from `evidence/demos/run_threat_matrix_demo.py`, reproduced honestly):**

| Attack vector | Capability | Epistemic-hard (membrane) | Epistemic-soft (advisory flag) | Shell |
|---|:---:|:---:|:---:|:---:|
| Out-of-scope file write | **BLOCK** | — | — | — |
| Invented entity assertion | — | **BLOCK** | — | — |
| Ungrounded actuation (LLM refund) | — | **BLOCK** | — | — |
| **Schema-valid entity + fabricated figure** | — | PASS | *FLAG* | — |
| Obfuscated dangerous shell command | — | — | — | **BLOCK** |
| Plausible false prose (no assertion/syscall) | — | — | — | — |

The fourth row is the honest boundary: a schema-valid but fabricated statement is **not contained**
by any hard layer — the advisory flag only *qualifies* it. Free prose is not read by the membrane
at all. Nothing here is claimed as caught that is not caught.

---

## 5. The two products (one engine, two chokepoints)

> **Product B = Product A where the "app" is the coding agent itself, and the chokepoint is
> the harness hook instead of the WebAssembly import.** Same `core.guard`, same `.bio`.

### Product A — App membrane  *(hard: WebAssembly **or** OS-sandbox)*
Any app is contained within its `.bio`: the app can only do what the constitution allows. Only
unbypassable substrates are shipped — a bypassable language-level variant is not.
- **WebAssembly**, two forms: (a) **custom capability imports** — a guest reaches the world only
  through host-granted gates mediated by `core.guard`; (b) the **WASI capability model** — a real
  compiled program (Rust → `wasm32-wasip1`) whose filesystem is limited to preopens derived from
  the `.bio`. The WASI form scales to any language without per-app host functions.
- **OS-sandbox (Linux Landlock)** — `products/app_membrane/sandbox_enforcer.py` (pure-Python
  `ctypes`) applies a Landlock ruleset from the `.bio` before `exec`-ing a **stock native binary**,
  so the kernel confines its filesystem writes to the declared scope (out-of-scope write → EACCES).
  Honest MVP scope: write confinement (read/execute unrestricted so any binary runs); Linux only;
  fail-closed if unavailable. — `run_landlock_demo`.

### Product B — Agent membrane = **MetaSpace Warden** *(MVP, proven end-to-end)*
The current AI is contained within its session constitution: the agent can only do what it
is granted.
- Mechanism: a PreToolUse hook → the harness-independent decision core (`core/agent_adapter.py` →
  `core.guard`) → hardened constitution. One-click: a Claude Code plugin + an installer script.
- **Proven product loop:** the real hook enforces the shipped constitution over a realistic
  session, logs a project-local audit (`.metaspace/`), and `metaspace report` summarizes what was
  blocked, by capability kind. — `run_product_e2e`.
- **One core, many harnesses:** a second adapter, a generic **MCP capability-broker**
  (`products/mcp_membrane/`), reaches identical verdicts via the same core — `run_mcp_e2e`. (Honest
  condition: an MCP tool the agent may *voluntarily* call is advisory; the broker is hard only when
  the agent's ambient authority is removed so its tools are the only path to effects.)
- **CLI (`metaspace`):** `synthesize / ratify / gate / report / init` — one entry point over the
  engine (`run_cli_e2e`).

**Honest limits (Product B):** affects tool effects only, not prose; the shell check is a
**structural allowlist** (obfuscation-resistant, fail-closed); a restart is needed to activate;
on error it fails closed.

---

## 6. The proof is a reproducible run, not a PDF

Every claim is a **reproducible test anyone can run** — no hosted CI required. One command
(`python run_proofs.py`) executes all of them.

| Artifact | What it proves | Command |
|---|---|---|
| `products/app_membrane/run_wasm_demo.py` | WebAssembly hard membrane (all capability kinds) | 4 ALLOW / 5 DENY across FS/NET/ENV/SUBPROCESS, scope-enforced + physical check |
| `products/app_membrane/bypass_proof.py` | Unbypassability | `unknown import` link error |
| `products/app_membrane/wasi/run_wasi_demo.py` | Real program under WASI capabilities | read/write granularity: READ + WROTE + 2 DENY (write to read-only input refused) |
| `evidence/demos/run_synth_demo.py` | Code → constitution → enforcement | app's own effects bound it; undeclared subprocess denied |
| `evidence/demos/run_ratify_demo.py` | Content-bound ratification | SYNTHESIZED → RATIFIED → TAMPERED on widening |
| `evidence/demos/run_gate_demo.py` | Ratification gate (production) | only RATIFIED runs; synthesized/tampered refused, fail-closed |
| `evidence/demos/run_knowledge_demo.py` | Epistemic hard tier | 2 ALLOW / 5 DENY |
| `evidence/demos/run_entailment_demo.py` | Epistemic soft tier | flags SUPPORTED / UNSUPPORTED, never blocks |
| `products/ai_membrane/test_hook.py` | Agent membrane | 17/17 (obfuscated commands caught structurally) |
| `products/ai_membrane/test_shell_policy.py` | Structural shell allowlist | catches obfuscation the substring denylist misses |
| `evidence/demos/run_dryrun_demo.py` | Dry-run learning mode | static-only false-positives; dry-run-augmented allows |
| `evidence/demos/run_threat_matrix_demo.py` | Honest layer coverage | hard layers PASS a fabricated fact; soft only flags |
| `products/app_membrane/run_real_app_demo.py` | Real program does real work under containment | a Rust log analyzer computes correct stats; out-of-grant read refused |
| `evidence/demos/run_dogfood_demo.py` | Synthesizer on real code (dogfood) | a real, non-trivial constitution from this repo's ~36 files |
| `evidence/demos/run_ratification_review_demo.py` | Ratification cognitive brake | an unjustified provisional capability cannot be ratified (`--yes` can't bypass) |
| `evidence/run_fuzz.py` | Property-based fuzz | 5000 random cases: deny-by-default never violated; agrees with an independent oracle |
| `evidence/run_falsification.py` | Self-falsification (anti-slop) | mutation flips the decision; sabotaging `guard.check` fails a proof; wasmtime refuses an ungranted syscall |
| `evidence/run_cli_e2e.py` | CLI product flow (M0) | synthesize → gate (refused) → ratify → gate (allowed) → report |
| `evidence/run_product_e2e.py` | Warden product loop (M1) | real hook enforces a session (6 ALLOW / 5 BLOCK) → project-local audit → `metaspace report` |
| `evidence/run_mcp_e2e.py` | MCP adapter parity (M2) | hook and MCP broker reach identical verdicts; broker refuses+doesn't-perform a denied write |
| `evidence/run_landlock_demo.py` | OS-sandbox (M3, Linux/Landlock) | a stock native program confined to its `.bio` write scope; out-of-scope write → EACCES |

All together: **`python run_proofs.py`** — 21 proofs (21/21 on Linux; on non-Linux the Landlock
proof skips honestly, so 20 pass + 1 skip). The runner is skip-aware for OS-specific proofs.

---

## 7. Repository layout

```
metaspace-membrane/
├─ core/          guard.py · agent_adapter.py · knowledge_membrane.py · capability_analyzer.py
├─ products/
│   ├─ app_membrane/   WebAssembly substrate + sandbox_enforcer.py (Landlock)   [hard]
│   ├─ ai_membrane/    hook + install.py + session.constitution.bio (Warden)     [MVP]
│   └─ mcp_membrane/   generic MCP capability-broker (second harness)            [MVP]
├─ evidence/      demos/ (runnable proofs) · run_*_e2e.py · DECISIONS.md
├─ docs/          ARCHITECTURE.md (this document) · whitepaper
├─ cli.py         the `metaspace` CLI (synthesize/ratify/gate/report/init)
└─ run_proofs.py  one command runs every proof (reproducible evidence, no hosted CI)
```
