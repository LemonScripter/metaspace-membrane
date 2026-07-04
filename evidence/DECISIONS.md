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
| I-9 | **Content-bound ratification** (`core/provenance.py`). The RATIFIED stamp carries a fingerprint of the enforced policy (capabilities + knowledge + bash). A post-ratification edit that changes the policy reads as TAMPERED. | Ratification (C-5) must not be forgeable by editing the file after approval. |
| I-10 | **Ratification gate** (`core/gate.py`, `Guard(require_ratified=True)`): in production only a RATIFIED constitution runs; SYNTHESIZED / TAMPERED is refused (fail-closed). | Closes the chain: a policy is enforceable only after human ratification and cannot be broadened afterwards. |
| I-11 | **Structural shell policy** (`core/shell_policy.py`): the agent membrane's shell check is now a lexer-based allowlist (real program names, obfuscation-resistant) + token-based denylist, replacing the substring heuristic. | Addresses external critique #2: a substring denylist both misses obfuscated commands and false-positives on harmless ones; a structural allowlist resolves the actual programs and fails closed. |
| I-12 | **Dry-run learning mode** (`core/dryrun.py`): before ratification, run the program once with effects recorded (observe, never block) and merge the concrete observed effects into the synthesized constitution. | Addresses external critique #3: static synthesis under-declares dynamic code, so a ratified static-only constitution false-positive-blocks legitimate behaviour and pushes developers to wildcards. The dry-run makes the ratified constitution match reality. |
| I-13 | **Threat-model matrix + strict terminology.** A reproducible matrix runs each layer's real check per attack vector. Terminology is fixed: *containment* = hard/structural block; *qualification* = the soft tier's non-blocking flag. | Addresses external critique #1: the soft/hard boundary must be explicit. The matrix shows honestly that a schema-valid but fabricated statement is NOT contained by the hard layers — only qualified by the soft tier. |
| I-14 | **Ratification review / cognitive brake** (`core/ratification_review.py`): dry-run-learned capabilities are *provisional* and must each carry a `JUSTIFY` reason; ratification is refused (fail-closed) otherwise, and `--yes` cannot bypass it. | Addresses the second review: the dry-run's convenience opens a risk of smuggling a capability past a fatigued approver. The brake forces a per-item, read-gated justification. Honest limit: it enforces a justification's *presence*, not its *truth*. |
| I-15 | **Complete capability mediation at the WebAssembly gate** (`products/app_membrane`): one guard-mediated host import per capability KIND — FILESYSTEM write/read, NETWORK, ENV, SUBPROCESS — each scope-enforced (in-scope ALLOW, out-of-scope DENY); an ungranted kind is unreachable by construction. | Delivers the "structural hardness" the reviews asked for: every declarable effect, not just filesystem, is hard-mediated at the unbypassable chokepoint. |

## Evidence

| Proves | Command | Result |
|---|---|---|
| WebAssembly hard membrane (all capability kinds) | `python products/app_membrane/run_wasm_demo.py` | 4 ALLOW / 5 DENY across FS write+read / NET / ENV / SUBPROCESS, scope-enforced + physical check, exit 0 |
| Unbypassability | `python products/app_membrane/bypass_proof.py` | `unknown import` link error, exit 0 |
| Real program under WASI | `python products/app_membrane/wasi/run_wasi_demo.py` | read/write granularity: READ + WROTE + 2 DENY (write to read-only input refused), exit 0 |
| Code -> constitution -> enforcement | `python evidence/demos/run_synth_demo.py` | synthesized policy bounds the app; an undeclared effect (subprocess) is denied by default, exit 0 |
| Content-bound ratification | `python evidence/demos/run_ratify_demo.py` | SYNTHESIZED -> RATIFIED -> TAMPERED when the policy is widened after ratifying, exit 0 |
| Ratification gate (production) | `python evidence/demos/run_gate_demo.py` | synthesized/tampered REFUSED, ratified RUNS and enforces, exit 0 |
| Epistemic hard tier | `python evidence/demos/run_knowledge_demo.py` | 2 ALLOW / 5 DENY, exit 0 |
| Epistemic soft tier | `python evidence/demos/run_entailment_demo.py` | flags SUPPORTED / UNSUPPORTED, never blocks, exit 0 |
| Agent membrane | `python products/ai_membrane/test_hook.py` | 17/17 (incl. obfuscated commands caught structurally), exit 0 |
| Structural shell policy | `python products/ai_membrane/test_shell_policy.py` | resolves real program names; catches 4 obfuscations the substring denylist misses; fails closed, exit 0 |
| Dry-run learning mode | `python evidence/demos/run_dryrun_demo.py` | static-only constitution false-positive-DENIES a real write; dry-run-augmented ALLOWS it, exit 0 |
| Threat-model matrix | `python evidence/demos/run_threat_matrix_demo.py` | each layer's real check per vector; hard layers PASS a fabricated fact, soft only FLAGS it, exit 0 |
| Ratification cognitive brake | `python evidence/demos/run_ratification_review_demo.py` | a smuggled, unjustified dry-run capability cannot be ratified; a justified one can, exit 0 |

The evidence is a reproducible run, not a document: `python run_proofs.py` reproduces all of the above.
