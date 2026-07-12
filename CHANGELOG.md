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

### Security
- **Self-protection:** the shipped constitution now denies writes to the Claude config
  (`FILESYSTEM deny "{{CLAUDE_HOME}}/**"`), enforced by a new FILESYSTEM write **deny-override**
  in the guard. Even in the worst case — Claude Code opened at the home directory, so `~/.claude`
  is inside the granted write scope — a deceived agent cannot write `settings.json` or the
  constitution, and `metaspace off`/`ratify` are not on the shell allowlist, so it cannot disable
  the membrane via Bash either. Proven by `run_selfprotect_proof.py` (P-SELFPROTECT).

### Added
- **`metaspace --version`** and a version-parity check: `pyproject.toml`, `.claude-plugin/plugin.json`,
  and the CLI must report the same version. Proven by `run_version_proof.py` (P-VERSION).
- **`metaspace off`** — one-command uninstall: removes the hook and `METASPACE_*` env from
  `settings.json`, preserving every other setting/hook; idempotent; `--purge` also deletes the
  installed constitution. A human action the agent cannot reach (`metaspace` is not shell-
  allowlisted). Proven by `run_uninstall_proof.py` (P-UNINSTALL).
- **`metaspace demo`** — a live self-test: it spawns the REAL hook over the Friendly-Fire attack
  in a throwaway repo and shows every malicious effect blocked (and normal work allowed), exiting
  non-zero if anything leaks. A real end-to-end block, not a printed claim. Proven by
  `run_demo_proof.py` (P-DEMO).
- **Dry-run/observe first-run.** A fresh install starts in dry-run: the hook records and warns
  (on stderr) what it *would* block, but lets it through, so the first session is never
  over-blocked. `metaspace enforce` turns on blocking; `metaspace dryrun` returns to observe;
  `metaspace install --enforce` skips dry-run. Mode carried in `METASPACE_MODE`. Proven by
  `run_dryrun_mode_proof.py` (P-DRYRUN).
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
  `run_proofs.py`. Suite is now **30 proofs**: 30/30 on real Linux, 29 pass + 1 skip on Windows
  (Landlock is Linux-only).
- Planning baseline for the easy-install work: `docs/INSTALL_PLAN.md`, `docs/CLAIMS.md` (claim
  ledger), and DECISIONS `I-27`.

### Fixed
- Proof runner: the Friendly-Fire proof's POSIX-only leg no longer emits a string that collides
  with the suite's `PROOF_SKIPPED` sentinel, so the proof is correctly reported **PASS** on
  Windows (Section A proves the verdict cross-OS; only the real-payload leg is POSIX-only).
