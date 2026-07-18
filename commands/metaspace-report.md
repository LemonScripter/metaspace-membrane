---
description: Summarize this session's membrane audit into a human-readable safety report
allowed-tools: Bash(python:*)
---

Run the MetaSpace Membrane session report and present it to the user.

Execute:

```
python "${CLAUDE_PLUGIN_ROOT}/cli.py" report
```

Then summarize for the user: how many tool calls the membrane observed, how many
were **allowed** vs **blocked**, and list any blocked effects (out-of-scope writes,
disallowed network hosts, dangerous commands). If there were blocks, explain briefly
why each was denied by the active `.bio` constitution.
