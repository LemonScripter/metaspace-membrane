---
description: Ratify the project's .bio constitution so it can run in enforcing (production) mode
allowed-tools: Bash(python:*)
---

Ratify the active `.bio` constitution for this project. Ratification content-binds a
🟢 RATIFIED stamp to the exact policy fingerprint — any later silent widening becomes
🔴 TAMPERED and fails closed.

First show the user the constitution that is about to be ratified, then run:

```
python "${CLAUDE_PLUGIN_ROOT}/cli.py" ratify
```

Report the resulting provenance status (SYNTHESIZED → RATIFIED). Do **not** pass
`--yes` unless the user explicitly asks for non-interactive ratification.
