# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com); the project uses semantic versioning.
Reproduce any claim: `python run_proofs.py` (needs `pip install metaspace-membrane[proofs]`).

## [Unreleased] — Warden control panel (F4, in progress)

### Added
- **Privacy-first analytics service (`analytics/`) + opt-in CLI upload.** A tiny stdlib HTTP
  service that *counts* — and nothing more: cookie-free, no IP / user-agent / per-event rows
  stored, only aggregate counters in SQLite, so there is nothing personal to leak (the store can
  answer "how many", never "who"). Endpoints: `POST /a` (landing visit/CTA beacon), `POST /t`
  (opt-in CLI action), `GET /stats` (+ a minimal dashboard). Every stored token is sanitised to
  `[a-z0-9_.-]` and length-capped, so a hostile beacon cannot inject or crash it. The CLI uploads
  **only the coarse event name**, and **only** when telemetry consent is on **and**
  `METASPACE_ANALYTICS_URL` is set (default: no network, no id). `analytics/server.py`; proven by
  `run_analytics_proof.py` (P-ANALYTICS).
- **`metaspace run` — the app membrane: run a program confined to its `.bio` (deny-by-default
  effects).** The app-side counterpart of the Warden (which guards the coding *agent*): here a
  *running program* — including one an AI wrote — can only produce the effects its constitution
  grants. A **Python** target runs under an in-process membrane on **any OS** (writes to undeclared
  paths, network, and subprocess are blocked deny-by-default; declared effects hit the real
  resource; reads pass through); a **native binary** is confined by the Linux kernel (**Landlock**)
  as a hard boundary. `core/apprun.py`; proven by `run_apprun_proof.py` (P-APPRUN): a granted write
  really lands on disk while an out-of-scope write, a network call, and a subprocess are all blocked
  — and on Linux a native program's out-of-scope write fails at the kernel (EACCES). Honest scope:
  the Python backend is a language-level membrane (usable, cross-OS), bypassable by adversarial
  native code — use the Landlock backend for a hard boundary against untrusted binaries.
- **Offline licence layer (open-core monetisation infrastructure) — `metaspace license` /
  `keygen` / `issue`.** Paid tiers are unlocked by an Ed25519-signed key verified **fully
  offline** against an embedded vendor public key — no phone-home, works air-gapped. The free
  Warden membrane stays **zero-dependency** (the licence crypto lives in the optional `[pro]`
  extra and is never on the enforcement hot path). A licence is a soft entitlement gate, not a
  security boundary. **Nothing is gated yet** — everything runs free — but the entitlement is
  real: `is_pro()` exists and flipping one gate turns a feature Pro later. `core/license.py`;
  proven by `run_license_proof.py` (P-LICENSE): a genuine key verifies, a tampered / forged /
  expired key is rejected, and the safe default is the free tier.
- **`metaspace verify` — authenticity gate (the "slop" detector).** Point it at an AI-written
  Python program: it runs the program under a recording membrane (writes redirected to a throwaway
  sandbox; network and subprocess recorded and blocked — nothing dangerous happens) and reports
  whether it actually does what it claims. Catches the commonest AI slop — code that prints "saved
  1,000,000 rows!" but writes nothing (**HOLLOW**) — and a program that phones home to an undeclared
  host (**HIDDEN-EFFECT**), while a genuine program reads **CONSISTENT**. The verdict comes from the
  observed effect-trace, so a program can't fake it with a success message. `core/verify.py`; proven
  by `run_slopgate_proof.py` (P-SLOPGATE). Honest scope: the claims-vs-effects gap for Python, not
  general correctness.
- **Command picker + info list in the panel:** the "Allowed commands" field offers type-to-search
  autocomplete from a curated catalogue of common developer commands, and a "What can these do?"
  modal explains every command in one or two sentences (alphabetical, filterable). Backed by
  `core/command_catalog.py`, served at `/api/commands`. Proven by `run_commands_proof.py`.
- **Panel polish + opt-in telemetry:** edit an existing folder's rules in the panel, view
  per-folder activity (allowed / blocked / would-block), and toggle anonymous usage stats.
  Telemetry is **off by default, anonymous, never stores code / paths / personal data, and is
  never on the enforcement hot path** (`core/telemetry.py`; `metaspace telemetry on|off|status`).
  Proven by `run_telemetry_proof.py` (P-TELEMETRY) and the extended `run_ui_proof.py`.
- **`metaspace ui`** — a localhost control panel to configure the membrane per working directory:
  pick a folder, set what the agent may write / reach / run, choose Observe or Enforce. Zero-dep
  (stdlib `http.server`); it binds `127.0.0.1`, and a per-launch token + Origin/Host checks defend
  it so a malicious website cannot reconfigure the membrane. Friendly toggles map to a real `.bio`
  that always includes the self-protection deny (`core/bio_fields.py`). `metaspace projects` lists
  configured directories. Proven by `run_ui_proof.py` (P-UI-API + P-UI-CSRF).
- **Per-working-directory constitutions** (`core/project_config.py`): each working directory can
  have its own constitution + enforcement mode, all stored user-level under `~/.claude/metaspace`
  (registry + `projects/<hash>.bio`), so they stay outside any project's write scope —
  self-protection preserved. The hook resolves the current project's config at runtime and falls
  back to the install default. Proven by `run_project_config_proof.py` (P-PROJECT-RESOLVE).

## [0.2.0] — 2026-07-13 — Warden easy-install (F1)

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
