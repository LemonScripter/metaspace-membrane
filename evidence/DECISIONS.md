# Decisions & evidence

Every design decision is recorded so it can be reviewed independently. Every claim maps to
a runnable proof (see `evidence/demos/` and `products/*/`).

## Conceptual

| # | Decision | Rationale |
|---|---|---|
| C-1 | **Containment, not correctness.** The goal is not to prove code correct, but to bound its effects. | Rice's theorem: intent-conformance of arbitrary code is undecidable. |
| C-2 | **A bug = a deviation from the constitution.** | Makes "a bug" machine-measurable and enforceable. |
| C-3 | **Three membranes:** capability / value-invariant / epistemic. | Covers effect, value and fact hallucination. |
| C-4 | **Dual artifact from one `.bio`:** membrane (negative) + conformance test (positive). | The same source both locks and checks. |
| C-5 | **Provenance is communicated:** 🟢 RATIFIED vs 🟡 SYNTHESIZED. | Honest signalling of whether a human ratified the constitution. |
| C-6 | **Epistemic: hard vs soft split.** Referential integrity is hard; content faithfulness is soft (NLI). | Semantic faithfulness is not deterministic — it must not be claimed as hard. |
| C-7 | **Substrate target: WebAssembly + capability import; MVP language: Python.** | WebAssembly = unbypassable deny-by-default. |

## Implementation

| # | Decision | Rationale / limit |
|---|---|---|
| I-1 | **Name-based static effect detection** in the analyzer. | Simple, fast, enough for synthesis + CI. Aliasing/dynamism can evade it → the hard guarantee is the runtime membrane. |
| I-2 | **One shared decision engine** (`core.guard.check`) powers all layers. | One source, consistent decisions. |
| I-3 | **WebAssembly membrane uses named capability imports (a Linker).** | Name-based linking is the correct capability model and yields a precise `unknown import` error for ungranted gates. |
| I-4 | **Product A ships only the WebAssembly-hard variant.** | No over-promising: a bypassable language-level guard is not a product. |
| I-5 | **Agent membrane = a PreToolUse hook** in the harness, outside the agent. | An AI cannot be its own reference monitor — the membrane must sit outside it. |
| I-6 | **Fail-closed error handling:** unreadable input or unloadable constitution → deny. | A membrane that cannot see the request must not allow it. A loud block beats a silent bypass. |
| I-7 | **WASI capability model for real programs.** The filesystem preopen set is derived from the `.bio`; a WASI-compiled program (any language) can reach nothing else. | Standard, scalable containment of real compiled programs without per-app host functions. |
| I-8 | **Soft tier = pluggable entailment backends** (`core/entailment.py`): a dependency-free heuristic and a Claude LLM judge. Flags, never blocks. | Real semantic faithfulness is non-deterministic (C-6); the soft tier informs while the hard tier enforces. |

## Evidence

| Proves | Command | Result |
|---|---|---|
| WebAssembly hard membrane | `python products/app_membrane/run_wasm_demo.py` | 2 ALLOW / 3 DENY + physical check, exit 0 |
| Unbypassability | `python products/app_membrane/bypass_proof.py` | `unknown import` link error, exit 0 |
| Real program under WASI | `python products/app_membrane/wasi/run_wasi_demo.py` | read/write granularity: READ + WROTE + 2 DENY (write to read-only input refused), exit 0 |
| Code -> constitution -> enforcement | `python evidence/demos/run_synth_demo.py` | synthesized policy bounds the app; an undeclared effect (subprocess) is denied by default, exit 0 |
| Epistemic hard tier | `python evidence/demos/run_knowledge_demo.py` | 2 ALLOW / 5 DENY, exit 0 |
| Epistemic soft tier | `python evidence/demos/run_entailment_demo.py` | flags SUPPORTED / UNSUPPORTED, never blocks, exit 0 |
| Agent membrane | `python products/ai_membrane/test_hook.py` | 12/12, exit 0 |

The evidence is a reproducible run, not a document: `python run_proofs.py` reproduces all of the above.
