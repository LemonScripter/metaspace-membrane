# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com); the project uses semantic versioning.
Reproduce any claim: `python run_proofs.py` (needs `pip install metaspace-membrane[proofs]`).

## [Unreleased] — Warden easy-install (F1)

### Changed
- **Dependencies:** the Warden agent hook and `core/` are now **zero third-party dependencies**.
  `wasmtime` moved from a runtime dependency to an optional `[proofs]` extra — it is needed only
  to run the WebAssembly/WASI proofs, not for the shipped agent protection. Runtime install:
  `pip install metaspace-membrane`; to run the proof suite: `pip install metaspace-membrane[proofs]`.

### Added
- **`metaspace install`** — one-step user-level installer (default `~/.claude/`): merges the
  PreToolUse hook into `settings.json` and drops an editable constitution into
  `~/.claude/metaspace/`. User-level by design so the membrane's config sits outside any
  project's write-scope (self-protection); `--project DIR` offers the agent-reachable variant
  with a printed caveat. Idempotent and non-clobbering; the hook uses the same single
  command-string form as the plugin `hooks.json`.
- **P-INSTALL + P-IDEMPOTENT** proof (`evidence/run_install_proof.py`): runs the real installer
  into a temp HOME, checks the real `settings.json` (one hook, unrelated keys/hooks preserved,
  no pinned project root, second install does not duplicate), then drives the REAL hook with the
  INSTALLED constitution and confirms it blocks the Friendly-Fire vectors and allows legit work.
- **P-ZERODEP** proof (`evidence/run_zerodep_proof.py`): the entire Warden decision path imports
  and makes real decisions with `wasmtime` made unimportable — falsifiable, wired into
  `run_proofs.py`. Suite is now **25 proofs**: 25/25 on real Linux, 24 pass + 1 skip on Windows
  (Landlock is Linux-only).
- Planning baseline for the easy-install work: `docs/INSTALL_PLAN.md`, `docs/CLAIMS.md` (claim
  ledger), and DECISIONS `I-27`.

### Fixed
- Proof runner: the Friendly-Fire proof's POSIX-only leg no longer emits a string that collides
  with the suite's `PROOF_SKIPPED` sentinel, so the proof is correctly reported **PASS** on
  Windows (Section A proves the verdict cross-OS; only the real-payload leg is POSIX-only).
