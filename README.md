# MetaSpace Membrane

**A deterministic safety membrane for machine-generated software.**

![proofs: reproducible](https://img.shields.io/badge/proofs-reproducible-brightgreen)

MetaSpace Membrane turns an *undecidable* question — *"is this AI doing the right thing?"* —
into a *decidable* one — *"is this effect inside the declared boundary?"* — and enforces the
answer **deny-by-default**. One `.bio` constitution, three membranes, two products.

> Part of the **MetaSpace.Bio Engine Project** — Szőke László-Ferenc (admin@metaspace.bio).
> **Patent pending.**

---

## Watch the 60-second explainer

[![MetaSpace Membrane — 60-second explainer](assets/explainer-poster.png)](assets/explainer.mp4)

*Containment, not correctness — the idea in one minute.* ▶ click to play

---

## Why

You cannot prove that a generated program does the right thing (Rice's theorem — undecidable).
So we stop verifying intent and **contain effects** instead. A membrane sits at a chokepoint,
reads the constitution, and blocks anything not explicitly granted. A bug becomes *a deviation
from the constitution* — machine-measurable and enforceable.

The guarantee is only as hard as the chokepoint is unbypassable:

```
heuristic    ->  language guard  ->  harness hook  ->  WebAssembly
(advisory)       (bypassable)        (hard on agent)   (unbypassable)
```

---

## Two products, one engine

| | **Product A — App membrane** | **Product B — Agent membrane** |
|---|---|---|
| Contains | any application ⊂ its `.bio` | the coding assistant ⊂ its limits |
| Chokepoint | WebAssembly capability import | Claude Code PreToolUse hook |
| Guarantee | **unbypassable** (hard, WebAssembly only) | hard on the agent (sits outside it) |
| Status | WebAssembly + WASI substrate (real programs, demonstrated) | **shippable today** |

Both are built on the same `core/` decision engine (`guard.py`) and the same `.bio` file.

---

## Run the proofs (the evidence is a reproducible run)

```bash
pip install wasmtime
python run_proofs.py        # runs all four proofs; exit 0 if every one passes
```

Or run them individually:

```bash
python products/app_membrane/run_wasm_demo.py         # 2 ALLOW / 3 DENY + physical check
python products/app_membrane/bypass_proof.py          # ungranted gate -> unknown import (blocked)
python products/app_membrane/wasi/run_wasi_demo.py    # real Rust program contained by WASI capabilities
python evidence/demos/run_synth_demo.py               # code -> constitution -> enforcement (closed loop)
python evidence/demos/run_ratify_demo.py              # ratification is content-bound (tamper detected)
python evidence/demos/run_gate_demo.py                # production gate: only RATIFIED runs
python evidence/demos/run_knowledge_demo.py           # 2 ALLOW / 5 DENY (hallucination blocked)
python evidence/demos/run_entailment_demo.py          # soft tier flags faithfulness (never blocks)
python products/ai_membrane/test_hook.py              # 12/12
```

No hosted CI required — the proof is a command anyone can run.

---

## Install the agent membrane (Product B)

**As a Claude Code plugin (one command):**

```
/plugin marketplace add LemonScripter/metaspace-membrane
/plugin install metaspace-membrane@metaspace
```

Restart the session and run `/hooks` to confirm the PreToolUse membrane is active. The plugin
ships a hardened default constitution (project-only writes, host allowlist, dangerous-command
block); `${CLAUDE_PROJECT_DIR}` is used as the project boundary automatically.

**Or as a portable installer** (writes `.claude/settings.json` directly, with an editable
constitution in `.claude/metaspace/`):

```bash
python products/ai_membrane/install.py /path/to/your/project
```

Restart the Claude Code session, then run `/hooks` to confirm it is active. Removing the hook
block reverts either method.

The session constitution is deny-by-default: writes are limited to the project directory,
outbound network to an allowlist, and dangerous shell patterns are blocked.

---

## The `.bio` constitution

One file, three lenses:

```bio
CAPABILITIES {
  FILESYSTEM write "out/**"
  NETWORK    out   "api.allowed.com"
}

KNOWLEDGE {
  ENTITY order FROM "kb/orders.json"
  FIELD  order.status IN pending, shipped, delivered, refunded
  ACTUATE refund PROVENANCE verified_db
  CITATION REQUIRED
  SOURCE verified_db
}
```

- **Capability** — mediates effects on the world (deny-by-default).
- **Value invariant** — guards safety bounds.
- **Knowledge** — grounded facts only: no invented entities, no ungrounded actuation.

---

## Synthesize a constitution from code

Point the synthesizer at a file or directory; it detects the code's real effects
(filesystem, network, env, subprocess, hardware, import-path) and drafts a `.bio` — marked
`SYNTHESIZED`, since a human ratifies before it is trusted:

```bash
python synthesize.py path/to/app --out app.constitution.bio
```

`evidence/demos/run_synth_demo.py` runs the loop end-to-end: it synthesizes a constitution
from a sample app, feeds it straight into the membrane, and shows the app can then only do
what it declared — an effect it never had (a subprocess) is denied by default. This is a
static heuristic; the runtime membrane, not the synthesis, is the guarantee.

Ratify a reviewed constitution (SYNTHESIZED 🟡 → RATIFIED 🟢):

```bash
python ratify.py app.constitution.bio --yes
```

Ratification is **content-bound**: the stamp carries a fingerprint of the enforced policy, so
a later edit that widens a scope or adds a capability is detected as TAMPERED 🔴 — you cannot
ratify a policy and then quietly broaden it.

In production, gate the membrane on ratification — `Guard(..., require_ratified=True)` (or
`core.gate`) runs **only** a RATIFIED constitution; a SYNTHESIZED or TAMPERED one is refused,
fail-closed. A policy is enforceable only after human ratification.

---

## Layout

```
core/          shared decision engine (guard, knowledge, analyzer)
products/      app_membrane (WebAssembly) · ai_membrane (hook + installer)
evidence/      runnable proofs + decisions
docs/          ARCHITECTURE.md
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full technical background, or the
technical whitepaper [`docs/MetaSpace_Membrane_Whitepaper_EN.pdf`](docs/MetaSpace_Membrane_Whitepaper_EN.pdf)
(LaTeX source alongside; every claim is a reproducible run or true by construction).

---

## Honest limits

- Product A's hard guarantee requires the WebAssembly substrate; a language-level guard is
  bypassable and is not shipped as a product.
- The code→constitution synthesis is a static heuristic; a **dry-run learning mode**
  (`core/dryrun.py`) observes concrete runtime effects and augments the constitution *before*
  ratification, so it does not false-positive-block legitimate dynamic behaviour.
- The agent membrane affects tool effects, not the model's prose; its shell check is a
  **structural allowlist** (`core/shell_policy.py`) — obfuscation-resistant and fail-closed.
- The epistemic soft tier is not deterministic and does not block: the hard tier performs
  *containment*, the soft tier only *qualification*. The reproducible threat-model matrix
  (`evidence/demos/run_threat_matrix_demo.py`) shows exactly what each layer catches — including
  where a schema-valid but fabricated statement passes the hard layers and is only flagged.

---

© Szőke László-Ferenc — MetaSpace.Bio Engine Project. Patent pending. See [LICENSE](LICENSE).
