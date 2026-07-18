---
description: Show the current membrane status — mode, active .bio constitution, and scope
allowed-tools: Bash(python:*), Read
---

Report the current state of the MetaSpace Membrane for this project so the user knows
exactly what the agent is allowed to do.

1. Show the active mode (observe / dryrun / enforce) and the resolved `.bio`
   constitution path.
2. Read and summarize the constitution's granted capabilities: filesystem write scope,
   network host allowlist, and blocked command patterns.
3. If a control panel is desired, tell the user they can open it with:

   ```
   python "${CLAUDE_PLUGIN_ROOT}/cli.py" ui
   ```

Keep the summary short and concrete — the point is a one-glance answer to
"what can the agent touch right now?"
