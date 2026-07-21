# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com); the project uses semantic versioning.
Reproduce any claim: `python run_proofs.py` (needs `pip install metaspace-membrane[proofs]`).

## [Unreleased]

### Added
- **Agent-agnostic design rationale** (`docs/AGENT_AGNOSTIC_DESIGN.md`, decision I-47). Analyses
  the generalization from "the Claude Code Warden" to a universal effect-containment layer,
  grounded in the existing harness-independent core: two axes (agent breadth vs program breadth),
  an honest per-pattern guarantee ladder, and a WordPress worked example on the OS substrate.
  *(Its G1→G4 roadmap was superseded by I-48 below and now lives as ledger rows; the document is
  rationale-only.)*
- **One ledger: `docs/CLAIMS.md` is now the single source of truth for claims, plans and
  blockers** (decision I-48). Forward-looking statements previously lived in seven documents,
  none authoritative over the others, so the effective plan depended on which file you opened —
  and "hard vs cooperative" was re-argued each time because it lived in prose. The existing claim
  ledger was extended rather than replaced: stable append-only `C-nn` IDs, a **TIER enumeration**
  (`HARD` / `COOPERATIVE` / `ADVISORY` / `N/A`) where every `HARD` claim must state its
  CONDITION, a `STATUS`, `DEPENDS` / `BLOCKED-BY` references, and an **obstacle register**
  (`O-nn`). All 37 shipped claims migrated with nothing lost; 14 more were added, including six
  the README already asserted but the ledger did not cover (ratification, team/CI gate, epistemic
  tiers, synthesis). Governing rule: the plan is never rewritten — rows are added or STATUS
  changed with a reason.
- **`evidence/run_roadmap_proof.py` (P-ROADMAP)** — the ledger's rules are mechanism now, not
  discipline. Checks that every `PROVEN` claim names a runner registered in `run_proofs.py`, that
  nothing is in progress on an unproven dependency, that an open obstacle forces its claims to
  `BLOCKED`, that every `HARD` claim states a CONDITION, and that **every guarantee-bearing
  README paragraph traces to a claim ID**. Shipped in observe mode, then flipped to enforcing
  once the public surface was aligned — mirroring the membrane's own dry-run-then-enforce
  default. Falsification-tested: an untagged guarantee sentence makes it fail.

- **Hard containment on a second agent, measured (C-39).** Cursor's agent was told to write
  outside the granted scope using its file-editing tool; the membrane blocked it and the file
  was never created — verified on disk, twice, across a Cursor restart. The audit records
  `host_event=preToolUse`, `dialect=hybrid`, `host_version=3.12.17`. All four survey variables
  are satisfied: Ingress = `preToolUse`, Vocabulary = 21 enumerated steps, Egress = block
  observed, Anchor = `~/.claude` (already protected by C-33).
- **Every hook decision now records how it was reached** — dialect, the host's own event name
  and version, the mode actually in force, and whether the host propagated `env`. Two facts had
  been invisible in the audit and had to be inferred, and inference is what kept getting
  retracted: a Cursor-shaped payload normalised to tool `Write` was indistinguishable from a
  Claude-shaped one, and a configured `dryrun` was silently running as the built-in `enforce`.
- **Cursor host support in the Warden hook**, with `run_cursor_compat_proof` (P-CURSOR, 24
  checks) driving the real hook against a **captured Cursor payload** (PII-scrubbed, BOM intact
  — `evidence/fixtures/`). One hook now serves both hosts and reaches identical verdicts; the
  Claude Code contract is unchanged. Claimed as **C-52**, deliberately at `N/A` tier: this is
  dialect compatibility, *not* a containment-strength claim for Cursor (see O-11).
- **`docs/AGENT_SURVEY.md`** — the empirical four-variable survey behind C-44, with the exact
  commands used, and its own corrections recorded in place rather than quietly edited.
- **`evidence/cursor_probe/`** — an agent capability detector prototype plus the behavioural
  hook probe used to run the experiment.

### Fixed
- **A host that ignores `env` silently got different rules (O-13 → C-54).** `metaspace install`
  records the mode and constitution path in the `env` block of `~/.claude/settings.json`; Claude
  Code injects them, Cursor does not. Measured: `mode_from_env=false`, `bio_from_env=false`. The
  hook therefore fell back to built-in defaults — **enforcing instead of the configured
  observe-mode**, so a Cursor user got hard blocking with no warning session, and the **shipped**
  constitution instead of their own, so every rule set in `metaspace ui` silently did nothing
  there. The settings are now mirrored to `~/.claude/metaspace/config.json`, which any host can
  read. Precedence: per-project registry → `env` where provided → this file → built-in, so Claude
  Code is unaffected. `install`/`enforce`/`dryrun` write the mirror and `off` removes it, and each
  decision records `mode_src` so this class of silent downgrade is visible in the audit.
  Proven by `run_envless_config_proof` (P-ENVLESS).
- **The Warden denied every tool call under Cursor.** Cursor does invoke hooks registered in
  `~/.claude/settings.json` — verified by running it — but three assumptions inherited from
  Claude Code were wrong, and the hook fail-closed on all of them:
  1. Cursor prefixes its JSON payload with a **UTF-8 BOM**, which `json.loads` rejects → every
     call became "unreadable input" → deny. Now decoded with `utf-8-sig` from raw bytes.
  2. Cursor takes the verdict from a **JSON `permission` field on stdout** and ignores Claude
     Code's exit-code-2 contract → even a decided block did nothing. The hook now emits both.
  3. Cursor sends its **own payload dialect** (`hook_event_name` + `command`/`file_path`) even
     when registered through Claude's settings file → after fixing (1) the hook would have found
     no `tool_name` and silently allowed everything, which is worse than failing closed. A
     dialect normalisation now maps both shapes onto the same effect vocabulary.
- **A stale, factually wrong proof count in `README.md`.** It advertised "22/22 on Linux and
  21 pass + 1 skip on Windows" long after the suite had grown past that. Replaced with a
  count-free statement plus pointers to this changelog and the ledger, so the README cannot drift
  out of date again. Found by the new I4 audit — the first defect the mechanism caught in
  published copy.

### Changed
- **`docs/AGENT_AGNOSTIC_DESIGN.md` demoted to rationale-only**; its §8 now maps the old G1–G4
  phases to ledger rows C-38…C-42. `docs/INSTALL_PLAN.md` marked historical (its work items
  shipped as C-31…C-37). `evidence/DECISIONS.md` keeps a distinct genre: *why* we decided, not
  *what* we will do.

### Note
- Deliberately unchanged: the **Zenodo record**. A documentation refactor is not a release and
  must not mint a DOI version; `10.5281/zenodo.21438905` remains the immutable `v0.3.1` snapshot.

## [0.3.1] — 2026-07-19 — Packaging fix

### Fixed
- **`metaspace demo` / `metaspace install` failed from a pip install** ("cannot locate the
  shipped hook/constitution"). The `session.constitution.bio` data file was not included in
  the built wheel (setuptools ships only `.py` by default). Added `[tool.setuptools.package-data]`
  so the shipped `.bio` constitution and the WASI `.wasm` guest are packaged. Verified end-to-end:
  `pip install` into a clean venv → `metaspace demo` runs and blocks the attack.

## [0.3.0] — 2026-07-18 — Warden control panel, tools & open-core license

### Changed
- **License: Proprietary → Business Source License 1.1 (open-core), now in effect.** The prior
  "permission is NOT granted to use" license was self-contradictory for a `pip install`-able tool
  and blocked adoption. The Licensed Work is now **free to use, copy, modify and redistribute for
  any non-competing purpose** (internal use, research, education, and products that depend on it);
  each version converts to **Apache-2.0** four years after release. The only reserved use is a
  competing commercial safety-membrane product/service. Synced across `LICENSE`, `pyproject.toml`
  (`BUSL-1.1` + PyPI classifiers + URLs), `.claude-plugin/plugin.json`, and `README.md`. Counsel
  refinement of the Competing-Use scope and per-version Change Date is a follow-up (see
  `docs/LICENSE.BSL.draft.md`), not a blocker to the granted rights.

### Added
- **A trilingual (EN/RO/HU) "What's this?" help modal on "Add a working directory".**
  An "ⓘ What's this?" link next to the button opens a guide (EN·HU·RO switch, shares the same
  `ms_lang` preference as the Tools modal; default EN) explaining: what a working directory is,
  that adding it registers a per-folder `.bio` (project-only writes, network allowlist, blocked
  commands, deny-by-default), the observe-vs-enforce distinction, and — answering a common
  question — that the **authenticity check needs only a file** (own throwaway sandbox) while
  **"run under a membrane" needs the folder** (it supplies both the constitution and the scope
  effects are confined to). Ends with the self-protection note (`~/.claude`, outside projects).
  Zero deps (inline, self-contained). Proven by `run_ui_proof.py` (the page ships the `dirinfo`
  modal + trigger and all three languages).
- **Plugin-marketplace listing polish (discoverability).** Added slash **commands**
  (`/metaspace-report`, `/metaspace-ratify`, `/metaspace-verify`, `/metaspace-status`) under
  `commands/` — thin wrappers over the CLI, so the plugin ships more than a lone hook.
  Added `license` (`LicenseRef-Proprietary`) and `repository` fields plus `claude-code` /
  `security` keywords to `.claude-plugin/plugin.json`. Added README **Screenshots** section
  with `assets/panel.png` (the live control panel, a project in *enforcing* mode) and
  `assets/landing.png` (the deny-by-default value proposition). Version parity proof still green.
- **A plain-language "How do these tools work?" help modal on the Tools card (EN/HU/RO).**
  An "ⓘ How do these work?" link opens a trilingual guide (an in-modal EN·HU·RO switch,
  remembered locally; default EN) explaining how to use the authenticity gate (`verify`) and
  the app membrane (`run`): what to enter (the program's **entry file** — the one you'd start
  with `python`), **why** (the tools *run* the program, they don't scan it, so one entry point
  covers the whole run — imported files included), what each verdict means
  (CONSISTENT / HOLLOW / HIDDEN-EFFECT / NO-EFFECTS), and the honest limits (Python only;
  claims-vs-effects, not general correctness; reads don't affect the verdict; the hard boundary
  for untrusted binaries is Landlock on Linux). Zero deps (inline, self-contained). Proven by the
  extended `run_ui_proof.py` (the page ships the EN/HU/RO copy).
- **The control panel now surfaces the app membrane, the authenticity gate, and licence
  status.** So the panel (`metaspace ui`) shows a real, visible change and you can drive every
  feature in one place: run a Python program under the **app membrane** (`/api/run` → the granted
  effects allowed, undeclared writes/network/subprocess blocked), run the **authenticity gate** on
  a file (`/api/verify` → verdict: NO-EFFECTS flags a do-nothing program, HIDDEN-EFFECT catches an
  undeclared network/subprocess), and view / activate / remove a **licence** key (`/api/license`,
  verified offline). All three inherit the panel's self-defence (localhost + per-launch token +
  same-origin). Proven by the extended `run_ui_proof.py`.
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
