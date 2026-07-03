# MetaSpace Membrane

**A deterministic safety membrane for machine-generated software.**

![proofs](../../actions/workflows/proofs.yml/badge.svg)

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
| Status | WebAssembly substrate (critical path) | **shippable today** |

Both are built on the same `core/` decision engine (`guard.py`) and the same `.bio` file.

---

## Run the proofs (the evidence is the build)

```bash
pip install wasmtime

# Product A — WebAssembly hard membrane
python products/app_membrane/run_wasm_demo.py     # 2 ALLOW / 3 DENY + physical check
python products/app_membrane/bypass_proof.py      # ungranted gate -> unknown import (blocked)

# Epistemic (KNOWLEDGE) membrane
python evidence/demos/run_knowledge_demo.py       # 2 ALLOW / 5 DENY (hallucination blocked)

# Product B — Agent membrane
python products/ai_membrane/test_hook.py          # 12/12
```

Every command exits `0` on success. CI runs all of them on every push.

---

## Install the agent membrane (Product B)

```bash
python products/ai_membrane/install.py /path/to/your/project
```

This writes `.claude/settings.json` with a PreToolUse hook and drops an editable
`session.constitution.bio` into `.claude/metaspace/`. Restart the Claude Code session, then
run `/hooks` to confirm it is active. Removing the hook block reverts it.

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

## Layout

```
core/          shared decision engine (guard, knowledge, analyzer)
products/      app_membrane (WebAssembly) · ai_membrane (hook + installer)
evidence/      runnable proofs + decisions
docs/          ARCHITECTURE.md
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full technical background.

---

## Honest limits

- Product A's hard guarantee requires the WebAssembly substrate; a language-level guard is
  bypassable and is not shipped as a product.
- The code→constitution synthesis is a static heuristic; the runtime membrane is the guarantee.
- The agent membrane affects tool effects, not the model's prose; its bash check is heuristic.
- The epistemic soft tier (NLI faithfulness) is not deterministic and does not block.

---

© Szőke László-Ferenc — MetaSpace.Bio Engine Project. Patent pending. See [LICENSE](LICENSE).
