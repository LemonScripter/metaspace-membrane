# Agent Survey — the four variables, empirically

**Claim:** C-44 in [`docs/CLAIMS.md`](CLAIMS.md). **Rule for this file: no inference, no vendor
documentation taken on trust.** Every cell records *how* it was verified — the exact path,
version, and extraction — so anyone can repeat it. Where a variable could not be verified, it
says so; an unverified cell may never be used to promote a claim.

## Why four variables

A membrane is **hard** on an agent only if all four hold. Three of them are the classic
interception questions; the fourth is the one that decides whether the agent can simply switch
the membrane off (see C-33).

| # | Variable | Question |
|---|---|---|
| 1 | **Ingress** | Is the intended effect observable *before* it happens? |
| 2 | **Vocabulary** | Is the effect vocabulary finite and enumerable? |
| 3 | **Egress** | Does a "deny" actually stop the effect, or is it advisory? |
| 4 | **Anchor** | Is the agent's own config a local filesystem path we can put in a deny scope? |

---

## Summary

| Agent | Ingress | Vocabulary | Egress | Anchor | Max honest TIER |
|---|---|---|---|---|---|
| **Claude Code** | ✅ PreToolUse | ✅ closed | ✅ exit 2 blocks | ✅ `~/.claude` | **HARD** (C-02, C-33) |
| **Cursor 2.3.35** | ✅ 6 blocking steps | ✅ 21 steps, extracted | ✅ blocks at call site | ✅ `~/.cursor` **and `~/.claude`** | **HARD — pending an empirical run** |
| Cline / Windsurf / Aider / Continue | — | — | — | — | not installed — unsurveyed |

> ## ⚠️ CORRECTION (2026-07-21, same day)
> **The first version of this survey was wrong on two counts, and the errors pointed the same
> way both times: they made Cursor look *less* capable than it is.** Recorded here rather than
> quietly edited, because a survey that hides its own corrections is not evidence.
>
> 1. **"12 hook names, closed vocabulary" — wrong.** Cursor has *two* enums. The 12-name one
>    (`Eb`) is what `hooks.json` validates against. The runtime step enum (`Nu`) has **21**,
>    including `preToolUse`, `postToolUse`, `sessionStart/End`, `preCompact`,
>    `subagentStart/Stop`, `workspaceOpen`. The first extraction anchored on the config enum
>    and reported it as *the* vocabulary.
> 2. **"No pre-write hook, so writes can only be ADVISORY" (O-11) — the mechanism was right,
>    the conclusion was too broad.** `afterFileEdit` genuinely cannot veto — now **confirmed by
>    experiment**, not just by reading the call site: a hook returning `permission: deny` from
>    `afterFileEdit` was ignored and the file persisted (Cursor 3.12.17, 2026-07-21). But
>    **`preToolUse` is in the blocking list**, and Cursor maps Claude Code's `Write`/`Edit` onto
>    it, so writes may still be blockable by that route. Untested — do not claim either way.
>
> 3. **The reported version was wrong.** `package.json` says 2.3.35 (the VS Code fork's internal
>    version); the running application reports `cursor_version: "3.12.17"` in its hook payload.
>    A version-sensitive detector must use the runtime value, which is only visible at runtime.
>
> **And the finding that changes the roadmap: Cursor natively reads
> `~/.claude/settings.json`** and speaks Claude Code's hook protocol, enabled by default.

---

## Cursor

**Version:** 2.3.35 · **commit:** `cf8353edc265f5e46b798bfb276861d0bf3bf120`
**Verified:** 2026-07-21, Windows 11, install at `C:\Program Files\cursor`

**How the facts below were obtained** (repeatable):

```powershell
# version
Get-Content "C:\Program Files\cursor\resources\app\package.json" | ConvertFrom-Json | % version

# the hook vocabulary and its veto semantics, from the shipped bundle
$f = "C:\Program Files\cursor\resources\app\out\vs\workbench\workbench.desktop.main.js"
$txt = [System.IO.File]::ReadAllText($f)
$txt.Substring($txt.IndexOf("beforeShellExecution") - 900, 1800)      # types.js
$txt.Substring(10846500, 4800)                                        # validators
```

Source of truth is Cursor's own `out-build/vs/base/common/hooks/types.js` and the sibling
`hooks/validators/*.js` modules, read out of the shipped bundle — not documentation.

### 1. Ingress — **exists**

Five hooks fire *before* the effect: `beforeShellExecution`, `beforeMCPExecution`,
`beforeReadFile`, `beforeTabFileRead`, `beforeSubmitPrompt`.

### 2. Vocabulary — **closed, 12 names**

Extracted verbatim from `hooks/types.js`:

```
beforeShellExecution   beforeMCPExecution     afterShellExecution    afterMCPExecution
beforeReadFile         afterFileEdit          beforeTabFileRead      afterTabFileEdit
stop                   beforeSubmitPrompt     afterAgentResponse     afterAgentThought
```

### 3. Egress — **partial**, and this is the decisive column

Each hook's response is checked by a validator that defines exactly what the hook may return:

| Hook | Validator module | Response contract | Can veto? |
|---|---|---|---|
| `beforeShellExecution` | `beforeCommandExecutionHookResponse.js` | `permission: allow \| deny \| ask` | ✅ **yes** |
| `beforeMCPExecution` | `beforeCommandExecutionHookResponse.js` | `permission: allow \| deny \| ask` | ✅ **yes** |
| `beforeReadFile` | `beforeReadFileResponse.js` | `permission: allow \| deny` | ✅ yes |
| `beforeTabFileRead` | `beforeTabFileReadResponse.js` | `permission: allow \| deny` | ✅ yes |
| `beforeSubmitPrompt` | `beforePromptSubmitResponse.js` | `continue: boolean` | ✅ halts prompt |
| `afterFileEdit` | `afterEditFileResponse.js` | *(no permission field)* | ❌ **no** |
| `afterTabFileEdit` | `afterTabFileEditResponse.js` | *(no permission field)* | ❌ no |
| `afterShellExecution` / `afterMCPExecution` | `after*Response.js` | *(no permission field)* | ❌ no |
| `stop` / `afterAgentResponse` / `afterAgentThought` | *(various)* | message fields only | ❌ no |

**There is no `beforeFileEdit` or `beforeWriteFile`.** The only file-mutation hooks are
`afterFileEdit` and `afterTabFileEdit`, and their validators accept no `permission` field — so
the write has already happened by the time we see it.

### 4. Anchor — **local and lockable**

| Path | Exists on this machine | Role |
|---|---|---|
| `~/.cursor/` | ✅ | user-level config root (`argv.json`, `ide_state.json`, `extensions/`, `projects/`) |
| `~/.cursor/mcp.json` | ❌ (not yet created) | MCP server config — string `mcp.json` present in the bundle |
| `hooks.json` | — | hook registration; the bundle ships a settings UI for it, including an "Invalid hooks.json found" error path |
| `%APPDATA%\Cursor\User\settings.json` | ✅ | editor settings (VS Code-derived layout) |

All are ordinary local files, so the C-33 self-protection pattern (put the Anchor inside a
`FILESYSTEM deny` scope) transfers in principle.

### The authoritative blocking list (call-site evidence, supersedes the validator table)

The validator modules describe the *advertised* response contract. What actually blocks is a
literal list in `packages/hooks/src/types.ts`:

```js
sWo = [ beforeShellExecution, beforeMCPExecution, beforeReadFile,
        beforeTabFileRead, subagentStart, preToolUse ]
```

Six steps can block. Verified at their call sites: `beforeReadFile` and `beforeTabFileRead`
`throw` on `permission === "deny"`; `subagentStart` throws and blocks subagent creation.

**`afterFileEdit` confirmed non-blocking at the call site** — its result is awaited and then
never inspected:

```js
await this.cursorHooksService.executeHookForStep(Nu.afterFileEdit, {
  conversation_id, generation_id, model, file_path,
  edits: [{ old_string, new_string }]
})            // no permission check; wrapped in a try/catch that only logs
```

**Validator contract ≠ implemented behaviour.** The `subagentStart` call site contains:
*"The 'ask' permission for subagentStart hooks is not yet implemented"* — yet its validator
accepts `ask`. Any detector that reads only validators will over-state what the host does.

### Claude Code compatibility — the decisive finding

Cursor ships `packages/hooks/src/claude-code-types.ts` and **reads Claude Code's own config**:

```js
claudeUserConfigUri = <userHome>/.claude/settings.json
isClaudeCodeHooksEnabled() { return this.thirdPartyExtensibilityObservable.get() ?? true }
```

Enabled by default. It also loads Claude project and project-local configs, respects workspace
trust, and logs under a `[Claude]` prefix.

Hook-name map: `PreToolUse→preToolUse`, `PostToolUse→postToolUse`,
`UserPromptSubmit→beforeSubmitPrompt`, `Stop`, `SubagentStop`, `SessionStart`, `SessionEnd`,
`PreCompact`. `PermissionRequest` and `Notification` map to null (unsupported).

Tool-name map: **`Bash→Shell`, `Read→Read`, `Write→Write`, `Edit→Write`**, `Grep→Grep`,
`WebFetch→WebFetch`, `WebSearch→WebSearch`, `Task→Task`; `Glob` unsupported and ignored with a
warning. MCP tools `mcp__server__tool` normalise to `MCP:tool`.

**Consequence: the Warden hook this project already ships — a `PreToolUse` entry in
`~/.claude/settings.json` handling `Bash`/`Read`/`Write`/`Edit` — is the exact shape Cursor
consumes.** The "second agent adapter" may require little or no new code, and the Anchor is
`~/.claude`, which C-33 already protects.

### What this means

- Shell, MCP and file-read containment on Cursor can be **HARD**, on the same condition as
  C-02 (the host routes those effects through the hook and honours `permission: deny`).
- **File-write containment is probably also reachable** — not via `afterFileEdit`, which cannot
  veto, but via `preToolUse`, which is in the blocking list and receives Claude's `Write`/`Edit`
  tools. This must be confirmed by a run before it may be claimed.
- `beforeMCPExecution` is a pleasant surprise: Cursor already mediates MCP calls at a
  chokepoint, so protecting a Cursor user needs **no MCP proxy** (C-41's mechanism). It does
  **not** resolve O-4 — we get the interception for free but still lack a sound mapping from an
  arbitrary MCP tool name to `(kind, mode, target)`.
- The convergence on Claude Code's hook format suggests the per-agent adapter burden may be far
  smaller than assumed — but one data point is not a standard.

### Payload shapes (extracted from call sites)

```js
beforeReadFile     { conversation_id, generation_id, model, content, file_path, attachments }
beforeTabFileRead  { conversation_id, generation_id, model:"tab", file_path, content }
afterFileEdit      { conversation_id, generation_id, model, file_path,
                     edits:[{old_string, new_string}] }
subagentStart      { conversation_id, generation_id, model, subagent_id, subagent_type, task,
                     parent_conversation_id, tool_call_id, subagent_model,
                     is_parallel_worker, git_branch }
```

### Not yet verified (do not claim these)

1. **Empirical execution — still the main gap.** No hook has been run. Every finding above is
   static extraction from the shipped bundle: strong for the contract, silent on whether it
   behaves as written. Three extraction bugs were found and fixed while producing this document,
   which is precisely why a run is required before any TIER is claimed.
2. Whether a **user-registered `preToolUse`** (via `~/.claude/settings.json`) actually fires in
   Cursor and blocks a `Write`. This is the single highest-value experiment available.
3. Whether `permission: deny` can be **overridden** by user settings, and what
   `thirdPartyExtensibilityObservable` is bound to (it defaults to enabled, but something sets it).
4. `hooks.json` accepts only the 12 `Eb` names; how the other 9 runtime steps are registered
   (plugin hooks? team hooks? Claude-compat only?) is unresolved.

---

## Claude Code (baseline, for comparison)

Already proven in the suite rather than surveyed: Ingress = `PreToolUse` on stdin; Vocabulary =
the tool table in `products/ai_membrane/session_guard_hook.py`; Egress = exit code 2 prevents the
call (C-02, `run_friendly_fire_proof`); Anchor = `~/.claude`, held in a deny scope (C-33,
`run_selfprotect_proof`). Critically, `PreToolUse` covers `Write`/`Edit`/`MultiEdit` — the
pre-write interception Cursor lacks.

---

## Unsurveyed agents

Not installed on the survey machine, therefore **entirely unverified**: Cline, Windsurf, Aider,
Continue, Zed, Claude Desktop. GitHub Copilot Chat is present as a VS Code extension
(`github.copilot-chat-0.37.6`) but has not been examined.

Per O-7, no adapter work may be planned on these until their four variables are recorded here
the same way.
