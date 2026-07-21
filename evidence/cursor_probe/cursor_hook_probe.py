#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor hook probe — the empirical leg of the agent survey (C-44).

The survey's Cursor findings were extracted from the shipped bundle
(`vs/base/common/hooks/types.js` + `hooks/validators/*.js`). That is strong evidence of the
*contract*, but it is not a run. This probe closes the four gaps the survey lists as unverified:

  U1  the `hooks.json` schema and discovery order        -> proven by the hook firing at all
  U2  the payload shape passed to each hook              -> logged verbatim
  U3  empirical execution (no hook had ever been run)    -> this is the run
  U4  whether `permission: deny` is actually honoured    -> the sentinel command must not execute

…and it is designed to FALSIFY O-11 if O-11 is wrong. O-11 states that Cursor cannot veto a file
write, because its only file-mutation hooks fire afterwards and their validators accept no
`permission` field. So this probe *deliberately returns `permission: deny` from `afterFileEdit`*.
If the edit is nevertheless on disk, O-11 is confirmed by experiment, not by reading minified JS.
If the edit is somehow prevented, O-11 is refuted and the survey must be corrected.

SAFETY — this probe is deliberately inert for normal work:
  * it ALLOWS everything by default; it denies only a command containing the sentinel below,
  * it never modifies anything, only appends to its own log,
  * remove it by deleting ~/.cursor/hooks.json (Cursor watches the file and reloads live).

Response contract (from the bundle, Cursor 2.3.35):
  beforeShellExecution / beforeMCPExecution -> {"permission": "allow"|"deny"|"ask", ...}
  beforeReadFile / beforeTabFileRead        -> {"permission": "allow"|"deny"}
  after*                                    -> no permission field is validated
"""

import os
import sys
import json
import datetime

SENTINEL = "METASPACE_PROBE_DENY"
LOG = os.path.join(os.path.expanduser("~"), ".cursor", "metaspace_probe_log.jsonl")


def log(record):
    record["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass          # a probe must never break the user's editor


def main():
    hook_name = sys.argv[1] if len(sys.argv) > 1 else "(not passed as argv)"
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception as e:
        raw = f"<stdin unreadable: {e}>"

    try:
        payload = json.loads(raw) if raw.strip() else None
    except Exception:
        payload = None

    # U2: record the payload verbatim, plus how the hook name reached us (argv? a payload field?)
    log({
        "hook_argv": hook_name,
        "argv_all": sys.argv[1:],
        "raw_stdin": raw[:4000],
        "payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else None,
        "payload": payload if isinstance(payload, dict) else None,
    })

    blob = raw  # match against the whole payload: we do not yet know the field names (U2)

    # U4 + O-11: deny the sentinel. On beforeShellExecution this must PREVENT execution.
    # On afterFileEdit the same response should be ignored — that is the O-11 experiment.
    if SENTINEL in blob:
        response = {
            "permission": "deny",
            "user_message": "MetaSpace probe: denied by the survey probe (expected).",
            "agent_message": "This command was blocked by a hook probe. Do not retry.",
        }
        log({"decision": "DENY", "reason": "sentinel present", "response": response})
    else:
        response = {"permission": "allow"}

    sys.stdout.write(json.dumps(response))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
