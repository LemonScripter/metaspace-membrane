# Run the Warden from an installed copy, not from the repository

**Why.** On this machine the development tree and the enforcing engine are the same files:
`.claude/settings.json` points the hook at `metaspace-membrane/products/ai_membrane/session_guard_hook.py`,
which imports `metaspace-membrane/core/`. The constitution therefore has to deny `core/**` — and
denying it makes the engine undevelopable. Both properties are wanted; they only conflict because
one copy is doing two jobs.

Splitting them gives three things at once: the enforcing engine becomes an artefact the agent
cannot write, the repository becomes ordinary source it can develop, and what enforces here is the
**same artefact users install** — which the release gate already verifies.

**The location matters.** The installed copy must sit outside the agent's write scope, which is
`C:/Users/lszok/Documents/_metaspace_kodvedelem/**` plus the project memory directory. A venv
inside the repo would be writable and would defeat the point. `C:\Users\lszok\.metaspace-warden`
is outside it, so the default deny protects it with no extra rule.

---

## 1. Create the venv and install the released package  *(you run this — it writes outside my scope)*

```
python -m venv "C:\Users\lszok\.metaspace-warden"
"C:\Users\lszok\.metaspace-warden\Scripts\python.exe" -m pip install metaspace-membrane==0.3.2
```

Installing from PyPI rather than from the working tree is deliberate: what enforces on this
machine should be the artefact everyone else gets.

## 2. Point the project hook at it

`C:\Users\lszok\Documents\_metaspace_kodvedelem\.claude\settings.json` — only the `args` line
changes; the matcher, the timeout and the whole `env` block stay as they are.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit|Read|Bash|WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "C:\\Users\\lszok\\.metaspace-warden\\Scripts\\python.exe",
            "args": [
              "C:\\Users\\lszok\\.metaspace-warden\\Lib\\site-packages\\products\\ai_membrane\\session_guard_hook.py"
            ],
            "timeout": 30
          }
        ]
      }
    ],
  },
  "env": {
    "METASPACE_SESSION_BIO": "C:\\Users\\lszok\\Documents\\_metaspace_kodvedelem\\constitution\\session\\session.constitution.bio",
    "METASPACE_PROJECT_ROOT": "C:\\Users\\lszok\\Documents\\_metaspace_kodvedelem",
    "METASPACE_MODE": "enforce"
  }
}
```

Note the `command` changes too: the hook must run under the **venv's** interpreter so it imports
the installed `core/`, not the repository's.

*(Careful with the trailing comma after `]` above — remove it; it is there only to show where the
`hooks` block ends. Valid JSON has no trailing commas.)*

## 3. Relax the constitution — the repo is now just source

`constitution/session/session.constitution.bio`, section A. These two denies existed only because
the repo *was* the engine. Delete them:

```bio
    FILESYSTEM deny  "C:/Users/lszok/Documents/_metaspace_kodvedelem/metaspace-membrane/core/**";
    FILESYSTEM deny  "C:/Users/lszok/Documents/_metaspace_kodvedelem/metaspace-membrane/products/ai_membrane/session_guard_hook.py";
```

Keep the other two (`constitution/**` and `.claude/**`) — those still guard the live membrane.

## 4. Restart Claude Code

The `env` block and the hook path are read at startup.

---

## What changes about how engine fixes land

An edit to `core/` in the repository no longer changes what enforces. That is the point, and it
has a consequence worth stating plainly: **an engine fix reaches the live membrane only when you
reinstall it.** After merging something like C-68:

```
"C:\Users\lszok\.metaspace-warden\Scripts\python.exe" -m pip install --force-reinstall --no-deps "C:\Users\lszok\Documents\_metaspace_kodvedelem\metaspace-membrane\dist\metaspace_membrane-<version>-py3-none-any.whl"
```

…or simply `pip install -U metaspace-membrane` once the fix is released. Upgrading the thing that
constrains you should be a deliberate act, not a side effect of editing a file.

## How to verify it took

```
python -c "import os;print(os.environ.get('METASPACE_MODE'))"
```

and, after any tool call, the newest line of `.metaspace/session_audit.jsonl` — it records
`eff_mode` and `mode_src`. The clearest single check is that an edit to
`metaspace-membrane/core/shell_policy.py` is now **allowed**, while an edit to
`constitution/session/session.constitution.bio` is still **denied**.
