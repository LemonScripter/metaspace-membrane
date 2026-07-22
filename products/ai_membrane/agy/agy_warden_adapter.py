#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agy_warden_adapter.py  —  Antigravity CLI (agy) -> MetaSpace Warden bridge (packaged).

Antigravity's `jsonhook` speaks a different shape than the Warden:

    agy IN  (stdin) : {"toolCall": {"name": "run_command",
                                    "args": {"CommandLine": "rm -rf /"}}, ...}
    agy OUT (stdout): {"decision": "allow"|"deny"|"ask"|"force_ask", "reason": ...}

The Warden speaks Claude's {tool_name, tool_input} in / exit-code + verdict_payload out. This
adapter TRANSLATES agy->Claude, invokes the UNMODIFIED Warden as a subprocess (one proven
decision core, incl. fail-closed / dry-run / self-protection / audit), and TRANSLATES the
verdict Claude->agy. It also fixes the one output mismatch: the Warden emits decision="approve"
on allow, but agy's enum only accepts allow/deny/ask/force_ask.

Packaged layout — the Warden and the agy constitution are found by STABLE package-relative paths:
    products/ai_membrane/agy/agy_warden_adapter.py   <- this file
    products/ai_membrane/session_guard_hook.py       <- ../session_guard_hook.py  (the Warden)
    products/ai_membrane/agy/agy.constitution.bio    <- beside this file (default bio)

FAIL-CLOSED: if the Warden cannot be reached, DENY (the membrane's own philosophy). Set
AGY_WARDEN_FAILOPEN=1 for a loud allow during first-run setup.
"""

import os
import re
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))                    # .../ai_membrane/agy
AI_MEMBRANE = os.path.dirname(HERE)                                  # .../ai_membrane
WARDEN = os.path.join(AI_MEMBRANE, "session_guard_hook.py")         # the unmodified Warden core
DEFAULT_BIO = os.path.join(HERE, "agy.constitution.bio")            # tuned agy constitution
DEBUG_LOG = os.path.join(HERE, "adapter_debug.jsonl")
FAILOPEN = os.environ.get("AGY_WARDEN_FAILOPEN", "") in ("1", "true", "yes")

# agy tool name (step type lowercased, CORTEX_STEP_TYPE_ prefix removed) -> canonical Claude tool
AGY_TOOL_ALIASES = {
    "run_command": "Bash", "shell_exec": "Bash", "send_command_input": "Bash",
    "propose_code": "Write", "file_change": "Write", "write_blob": "Write",
    "code_action": "Edit", "edit_notebook": "NotebookEdit",
    "delete_directory": "Write", "move": "Write",
    "view_file": "Read", "view_file_outline": "Read", "read_notebook": "Read",
    "read_terminal": "Read",
    "read_url_content": "WebFetch", "open_browser_url": "WebFetch", "search_web": "WebFetch",
}

CMD_KEYS = ["commandline", "command", "cmd", "shellcommand"]
PATH_KEYS = ["absolutepath", "targetfile", "filepath", "filename", "path", "file",
             "notebookpath", "directorypath", "dirpath"]
URL_KEYS = ["url"]


def _dbg(rec):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _pick(args, keys):
    lower = {str(k).lower(): v for k, v in (args or {}).items()}
    for k in keys:
        if k in lower and lower[k] not in (None, ""):
            return lower[k]
    return ""


def _emit_and_exit(decision, reason=""):
    out = {"decision": decision}
    if reason and decision != "allow":
        out["reason"] = reason
    # raw UTF-8 bytes: agy parses stdout as UTF-8 protojson; Windows text stdout defaults to cp1252
    # and would mangle non-ASCII in `reason`.
    sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()
    sys.exit(0)


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig")
        event = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        _dbg({"stage": "read", "error": str(e)})
        _emit_and_exit("allow" if FAILOPEN else "deny", f"agy-adapter: unreadable input ({e})")

    tool_call = event.get("toolCall") or event.get("tool_call") or {}
    agy_tool = (tool_call.get("name") or "").strip()
    agy_args = tool_call.get("args") or tool_call.get("arguments") or {}

    claude_tool = AGY_TOOL_ALIASES.get(agy_tool, agy_tool)
    tool_input = dict(agy_args) if isinstance(agy_args, dict) else {}
    cmd = _pick(agy_args, CMD_KEYS)
    path = _pick(agy_args, PATH_KEYS)
    url = _pick(agy_args, URL_KEYS)
    if cmd:
        tool_input["command"] = cmd
    if path:
        tool_input["file_path"] = path
        tool_input.setdefault("notebook_path", path)
    if url:
        tool_input["url"] = url
    claude_event = {"tool_name": claude_tool, "tool_input": tool_input}

    wps = event.get("workspacePaths") or event.get("workspace_paths") or []
    project_root = (wps[0] if isinstance(wps, list) and wps else os.getcwd())

    env = dict(os.environ)
    env["METASPACE_PROJECT_ROOT"] = str(project_root)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # agy's guard mode is decoupled from the global Claude Code mode (default enforce; the point of
    # wiring the Warden into agy is to actually block). AGY_WARDEN_MODE=dryrun to observe-only.
    env["METASPACE_MODE"] = os.environ.get("AGY_WARDEN_MODE", "enforce")
    # tuned agy constitution (allowlist + self-protection of the guard's own files)
    env["METASPACE_SESSION_BIO"] = os.environ.get("AGY_WARDEN_BIO", DEFAULT_BIO)

    try:
        proc = subprocess.run([sys.executable, WARDEN], input=json.dumps(claude_event).encode(),
                              capture_output=True, env=env, timeout=20)
    except Exception as e:
        _dbg({"stage": "invoke", "error": str(e), "agy_tool": agy_tool})
        _emit_and_exit("allow" if FAILOPEN else "deny", f"agy-adapter: Warden unreachable ({e})")

    w_out = (proc.stdout or b"").decode("utf-8", "replace").strip()
    w_err = (proc.stderr or b"").decode("utf-8", "replace").strip()
    rc = proc.returncode

    permission, reason = None, ""
    try:
        vp = json.loads(w_out) if w_out else {}
        permission = vp.get("permission") or vp.get("decision")
        reason = vp.get("reason") or vp.get("agent_message") or ""
    except Exception:
        pass
    denied = (rc == 2) or (permission in ("deny", "block"))
    if not reason:
        m = re.search(r"\[MEMBRANE (?:BLOCK|DRY-RUN)\]\s*(.*)", w_err)
        reason = (m.group(1).strip() if m else w_err[:300]) or "blocked by the constitution"

    _dbg({"stage": "decide", "agy_tool": agy_tool, "claude_tool": claude_tool,
          "denied": denied, "rc": rc, "permission": permission,
          "target": (cmd or path or url)[:120], "reason": reason[:200] if denied else ""})

    if denied:
        _emit_and_exit("deny", f"[MetaSpace membrane] {reason}")
    _emit_and_exit("allow")


if __name__ == "__main__":
    main()
