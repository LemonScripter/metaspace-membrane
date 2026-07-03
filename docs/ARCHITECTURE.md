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
| **Value invariant** | Safety bounds (temperature, current, motion) | Value violation (crosses an invariant) |
| **Epistemic** | Factual assertion and knowledge-based actuation | Fact hallucination (acts on false data) |

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

- Semantic faithfulness / entailment (does the text follow from the source) → an NLI model.
- `soft_entailment()` flags it as `UNVERIFIED` and does **not** block. We do not pretend it is hard.

---

## 5. The two products (one engine, two chokepoints)

> **Product B = Product A where the "app" is the coding agent itself, and the chokepoint is
> the harness hook instead of the WebAssembly import.** Same `core.guard`, same `.bio`.

### Product A — App membrane  *(hard, WebAssembly only)*
Any app is contained within its `.bio`: the app can only do what the constitution allows.
- Only the unbypassable WebAssembly form is shipped as the product — a bypassable
  language-level variant is not.
- Two forms are demonstrated: (a) **custom capability imports** — a guest reaches the world
  only through host-granted gates mediated by `core.guard`; (b) the **WASI capability model** —
  a real compiled program (Rust → `wasm32-wasip1`) whose filesystem is limited to preopens
  derived from the `.bio`. The WASI form scales to any language without per-app host functions.

### Product B — Agent membrane  *(shippable today)*
The current AI is contained within its session constitution: the agent can only do what it
is granted.
- Mechanism: a `.claude/settings.json` PreToolUse hook → `core.guard.check()` → hardened constitution.
- One-click: a Claude Code plugin + an installer script.

**Honest limits (Product B):** affects tool effects only, not prose; the bash check is
heuristic; a restart is needed to activate; on error it fails closed.

---

## 6. The proof is a reproducible run, not a PDF

Every claim is a **reproducible test anyone can run** — no hosted CI required. One command
(`python run_proofs.py`) executes all of them.

| Artifact | What it proves | Command |
|---|---|---|
| `products/app_membrane/run_wasm_demo.py` | WebAssembly hard membrane | 2 ALLOW / 3 DENY + physical check |
| `products/app_membrane/bypass_proof.py` | Unbypassability | `unknown import` link error |
| `products/app_membrane/wasi/run_wasi_demo.py` | Real program under WASI capabilities | 1 WROTE / 2 DENY, `.bio` scope = only filesystem |
| `evidence/demos/run_knowledge_demo.py` | Epistemic hard tier | 2 ALLOW / 5 DENY |
| `products/ai_membrane/test_hook.py` | Agent membrane | 12/12 |

---

## 7. Repository layout

```
metaspace-membrane/
├─ core/          guard.py · knowledge_membrane.py · capability_analyzer.py
├─ products/
│   ├─ app_membrane/   WebAssembly substrate (membrane.py, guest, demos)   [hard]
│   └─ ai_membrane/    hook + install.py + session.constitution.bio        [shippable]
├─ evidence/      demos/ (runnable proofs) · DECISIONS.md
├─ docs/          ARCHITECTURE.md (this document)
└─ run_proofs.py  one command runs every proof (reproducible evidence, no hosted CI)
```
