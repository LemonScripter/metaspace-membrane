---
description: Run the authenticity gate on a Python file — catch AI slop by its real effects
allowed-tools: Bash(python:*)
argument-hint: <path/to/app.py> [--expect writes|network|subprocess]
---

Run the MetaSpace authenticity gate on the target file to check whether it actually
does what it claims. The gate runs the app under a recording membrane and classifies
it by its **real effects**: `CONSISTENT`, `HOLLOW` (claims work but produces no
effects), `HIDDEN-EFFECT` (undeclared network/subprocess), or `NO-EFFECTS`.

Execute:

```
python "${CLAUDE_PLUGIN_ROOT}/cli.py" verify $ARGUMENTS
```

Then explain the verdict to the user in plain language, and — if the verdict is
HOLLOW or HIDDEN-EFFECT — point to the specific claimed-vs-actual effect mismatch.
