# Warden — easy-install plan (F1: plugin-turnkey)

**Goal:** a developer protects their Claude Code agent against the Friendly-Fire class of
attack in essentially one step, sees it working in seconds, and cannot have the protection
silently disabled by a deceived agent.

**Branch:** `feat/warden-install` (off `main` @ `ac0f3db`). Version target: **0.2.0**.
**Status:** planning locked; execution in progress (WI-1 first).

---

## Locked decisions (2026-07-12)
1. **Install scope: user-level only** (`~/.claude/`). The membrane's own configuration lives
   *outside* the project write-scope, so the same deny-by-default rule that stops the attack
   also stops the attack from disabling the membrane. (Project-level install may exist later
   as a documented option with an explicit tamper warning; not in the MVP.)
2. **First-run behavior: dry-run / observe.** On install the membrane logs what it *would*
   block but does not block; the user reviews, ratifies, then `enforce`s. A security tool that
   over-blocks on minute one gets uninstalled; dry-run avoids that.
3. **Explicit off switch:** a user-invoked `metaspace off` / uninstall exists — but it is a
   *human* action, unreachable through the agent's tool calls (see the self-protection note).

### Self-protection is part of the threat model (the core property)
The disable path is itself an effect the agent must not be able to trigger. The self-protection
proof (P-SELFPROTECT) must show a fully-deceived agent fails on **all** disable routes:
- writing `~/.claude/settings.json` or the constitution via the hook → BLOCK (outside project scope);
- running `metaspace off` / `metaspace ratify` as a Bash command → BLOCK (`metaspace` is not on
  the shell allowlist);
- only the human, outside the agent's tool calls, can run `metaspace off`.

---

## Anti-slop validation — systematized
**Invariant: claim = proof.** Every user-facing claim maps to a runnable proof or an honest label.

- **Claim ledger** (`docs/CLAIMS.md`): each claim carries a type (`[PROVEN]` / `[MEASURED]` /
  `[ARCH]` / `[SCOPE-LIMIT]`), the proof command that backs it, and last-verified OS+date. Docs
  and marketing may only state claims listed there.
- **Definition of Done (per work item, before merge):**
  - [ ] feature implemented;
  - [ ] a **falsifiable** proof added to `run_proofs.py` that FAILS if the feature is broken or
        removed (never a `print("PASS")`);
  - [ ] **no-mock:** the proof drives the REAL artifact (real hook, real `settings.json` in a temp
        HOME, real canary), like the Friendly-Fire A/B;
  - [ ] honest scope stated (what it does NOT do);
  - [ ] `DECISIONS.md` entry with rationale + limit;
  - [ ] full suite green on Windows + real Linux (Tokyo); macOS noted if untestable;
  - [ ] claim ledger + CHANGELOG + version updated.
- **Falsification-first:** for each claim, write the negative test (the one that catches the
  failure) alongside the feature — mutate the `.bio` → the decision flips; sabotage the guard →
  the proof fails.
- **The runner is the gate, not prose:** `python run_proofs.py` stays green; docs cannot claim
  what the runner does not show.
- **CI:** extend the M4 team-gate workflow to run the whole suite + install proofs; red = no
  merge. (Honest note, per I-25: hosted Actions is billing-blocked on this repo, so no green-badge
  claim; self-verified locally + Tokyo; the workflow is adoptable on forks.)

### New proofs the install work requires (no-mock)
| Proof | Proves (falsifiably) |
|---|---|
| **P-ZERODEP** | the Warden hook + `core/` import and decide with `wasmtime` unavailable (0-dep split holds) |
| **P-INSTALL** | temp HOME → installer merges the hook into `~/.claude/settings.json` (idempotent, non-clobbering) → the real hook blocks the Friendly-Fire vectors through that config |
| **P-SELFPROTECT** ⭐ | a deceived agent fails on every disable route (settings write, constitution write, `metaspace off`/`ratify` via Bash) |
| **P-IDEMPOTENT** | install twice / over existing settings → no corruption or duplicates; uninstall reverts cleanly |
| **P-DRYRUN** | dry-run logs-not-blocks; after ratify → blocks |
| **P-DEMO** | `metaspace demo` runs the real proof; sabotage → the demo FAILS (not a canned PASS) |
| **P-UNINSTALL** | `metaspace off` (human) reverts the install cleanly and the agent cannot invoke it |
| **P-VERSION** | `pyproject.toml` == `plugin.json` == `metaspace --version` == CHANGELOG top |

---

## Work items (each ships with its proof)
| # | Work item | Proof (DoD) |
|---|---|---|
| **WI-1** ✅ | Dependency split: `wasmtime` → `[project.optional-dependencies] proofs`; core stays 0-dep | P-ZERODEP — **done** |
| **WI-2** ✅ | User-level installer: `metaspace install` (default `~/.claude/`; `--project DIR` for the agent-reachable variant) → merges `settings.json` + constitution in `~/.claude/metaspace/`, idempotent + non-clobbering, single command-string hook (matches the plugin) | P-INSTALL, P-IDEMPOTENT (`run_install_proof`) — **done** |
| **WI-3** ⭐ ✅ | Self-protecting default constitution: `FILESYSTEM deny "{{CLAUDE_HOME}}/**"` enforced by a write deny-override in the guard, plus `metaspace` not on the shell allowlist. Blocks every disable route even when project root = home | P-SELFPROTECT (`run_selfprotect_proof`) — **done** |
| **WI-4** ✅ | Dry-run/observe as the default post-install state (hook `METASPACE_MODE`); `metaspace enforce` / `dryrun` to switch; `install --enforce` to skip | P-DRYRUN (`run_dryrun_mode_proof`) — **done** |
| **WI-5** | `metaspace demo` self-test wrapping the Friendly-Fire proof against the installed config | P-DEMO |
| **WI-9** | `metaspace off` / uninstall (user-invoked, agent-unreachable) | P-UNINSTALL (+ P-SELFPROTECT) |
| **WI-6** | Plugin finalization: `plugin.json`/`hooks.json`/marketplace consistent; `CLAUDE_PROJECT_DIR`; version parity | P-VERSION + plugin-load smoke |
| **WI-7** | Docs: `INSTALL.md` (quickstart + honest scope + reproduce), README quickstart, claim ledger | claim ledger |
| **WI-8** | VC/release: `CHANGELOG.md`, semver 0.1.0→0.2.0, `v0.2.0` tag plan, CI extension | P-VERSION |

**Sequence:** WI-1 → WI-2 → **WI-3** → WI-4 → WI-5 → **WI-9** → WI-6 → WI-7 → WI-8.
Each merges to `main` only with a green DoD, via PR. `main` stays green; tag `v0.2.0` when the
suite is green cross-OS; GitHub Release notes = the CHANGELOG section + reproduce commands.

---

## Open items (non-blocking)
- macOS is still unverified (no host); the "cross-OS easy install" claim stays scoped until it is.
- Default network allowlist content for the shipped constitution (kept minimal; dry-run softens
  first-run friction).
- Standalone-binary distribution (PyInstaller, for the "no Python" segment) is a later phase, not F1.
