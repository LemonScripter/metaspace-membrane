# Install & use MetaSpace Warden

A deny-by-default safety membrane for a Claude Code agent. It sits in the harness, **outside the
model**, and mediates every tool call: the agent can be fully prompt-injected and the harmful
effect still cannot happen. See the worked case study in
[`THREAT_FRIENDLY_FIRE.md`](THREAT_FRIENDLY_FIRE.md).

Every claim on this page is backed by a runnable proof — see [`CLAIMS.md`](CLAIMS.md) and reproduce
with `python run_proofs.py`.

---

## Requirements

**Python 3.10+** is the only prerequisite. The Warden hook itself has **zero third-party
dependencies** (standard library only), so there is nothing else to install — no build step, no
native toolchain. Get Python from [python.org](https://python.org), or `brew install python` /
`sudo apt install python3` / `winget install Python.Python.3`.

*(A standalone, no-Python binary is a possible future convenience for Python-free environments;
it is deliberately deferred — the Python path is the fastest runtime and keeps a single, proven
decision core.)*

## Quickstart (recommended: CLI, user-level, dry-run first)

```bash
pip install "git+https://github.com/LemonScripter/metaspace-membrane"
metaspace install            # user-level (~/.claude), starts in DRY-RUN (observe, no blocking)
metaspace demo               # 5-second live self-test: watch it block the attack
# restart Claude Code; work a normal session, then:
metaspace report             # see what it WOULD have blocked
metaspace enforce            # turn on blocking when you're satisfied
```

- **User-level by design.** The membrane's own config lives in `~/.claude/`, *outside* any
  project's write scope — so the same rule that stops the attack also stops the attack from
  disabling the membrane. Even if you open Claude Code at your home directory, the agent cannot
  write `settings.json` or the constitution, and it cannot run `metaspace off` (not shell-allowed).
- **Dry-run first** so the membrane never over-blocks your first session. Review, then `enforce`.

### Alternative: the Claude Code plugin

```
/plugin marketplace add LemonScripter/metaspace-membrane
/plugin install metaspace-membrane
```

The plugin wires the same hook. Note it **enforces immediately** (no dry-run) — installing it is a
deliberate opt-in. The CLI path above is recommended if you want the dry-run onboarding.

---

## Commands

| Command | What it does |
|---|---|
| `metaspace install [--project DIR] [--enforce] [--force]` | Wire the membrane. Default: user-level, dry-run. `--project` installs into one repo (agent-reachable — less safe). `--enforce` skips dry-run. |
| `metaspace demo` | Live self-test: drive the real hook over the Friendly-Fire attack and show every effect blocked. |
| `metaspace report [audit.jsonl]` | Human-readable session report (what was allowed / blocked / would-block). |
| `metaspace enforce [--project DIR]` | Leave dry-run; start blocking. |
| `metaspace dryrun [--project DIR]` | Return to dry-run/observe. |
| `metaspace off [--project DIR] [--purge]` | Remove the membrane (idempotent). `--purge` also deletes the constitution. |
| `metaspace --version` | Print the version. |

The constitution is an editable `.bio` file at `~/.claude/metaspace/session.constitution.bio` —
adjust the write scope, the network host allowlist, and the shell program allowlist for your work.

---

## What it protects against — and what it does NOT

**Protects (proven, at the tool-call boundary):** running an untrusted repo's script/binary
(`./security.sh`, `./code_policies`, and every shell-wrapper form), network exfiltration, and
writes outside the project — all deny-by-default, even when the model is fully deceived.

**Does NOT claim (honest limits):**
1. It does not make the model injection-proof; it contains *effects*, not the model's reasoning.
2. An **allowlisted interpreter running its own script** (e.g. `python build.py`) is allowed by
   design; a payload delivered that way is contained by the filesystem/network deny-by-default and
   by the OS-level substrate (Landlock/WASM), not by the shell gate.
3. Confining a process that already started is the OS substrate's job, not this hook's.
4. Maturity: research prototype / MVP (TRL ~3–4); no third-party security audit yet.

Full detail in [`THREAT_FRIENDLY_FIRE.md`](THREAT_FRIENDLY_FIRE.md) §8, and the trust boundary in
[`../SECURITY.md`](../SECURITY.md).

---

## Reproduce the proofs

```bash
git clone https://github.com/LemonScripter/metaspace-membrane
cd metaspace-membrane
python3 -m venv .venv && . .venv/bin/activate
pip install ".[proofs]"          # wasmtime, only needed to run the WASM/WASI proofs
python run_proofs.py             # exit 0 iff all proofs pass
```

The Warden hook itself has **zero third-party dependencies**; `wasmtime` is only for the proof
suite. No hosted CI, no account, no network callouts.
