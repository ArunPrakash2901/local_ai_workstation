# Agent Run Exit State Fix Report

## Evidence Reviewed
- Failed May 16 run:
  - `D:\_ai_brain\auto_runs\20260516_142401_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`
- Stale canary run:
  - `D:\_ai_brain\auto_runs\20260516_142326_agent_canary`
- Branch history, `.gitignore`, shell wrapper, and live process list.

## Why The Shell Returned While `status.txt` Stayed `CODEX_RUNNING`
- The current branch had been reset to the initial checkpoint and did not contain the agent runner files at all.
- The failed run came from the later `b7168db` agent-runner branch, where execution entered `CODEX_RUNNING` and then never wrote terminal artifacts.
- A fresh canary on this branch exposed the concrete launcher failure: the command builder passed `"call"` as a quoted token to `cmd.exe`, producing `'"call"' is not recognized as an internal or external command`.
- That means Codex never actually started on the broken path; the runner reached `CODEX_RUNNING` before launcher failure, then returned without terminalizing the run.
- This branch now has a compact runner with a hard invariant: a non-dry run may not return while `status.txt` is still `CODEX_RUNNING`.

## May 16 Run Findings
- Codex was selected and launcher metadata was written:
  - `codex.cmd (APPDATA): C:\Users\abi62\AppData\Roaming\npm\codex.cmd`
- The run wrote `codex execution starting` to `heartbeat.log`.
- There is no evidence that Codex itself launched for that run: no stdout, stderr, exit-code, or final-report artifact was written, and the same launcher path later reproduced as a pre-launch `cmd.exe` failure during canary validation.
- `codex_stdout.md`, `codex_stderr.md`, `codex_exit_code.txt`, and `final_report.md` were never created.
- Git diff after the run was empty, so the May 16 run did not modify project files.

## Why Canary Did Not Refresh
- `20260516_142326_agent_canary` also stopped at `STARTED` with no Codex output or terminal report.
- Because the launcher failed before a terminal path completed, `reports/agent_canary_status.json` was not refreshed.
- The first repaired canary made that visible as `CODEX_FAILED`; after fixing the malformed `cmd.exe` invocation, `20260516_144158_agent_canary` completed as `AGENT_CANARY_PASSED`.
- The runner now prints both canary startup and terminal status, writes terminal artifacts, and refreshes the canary cache.

## Stale May 14 Processes
- Old `node` / `codex` / `powershell` processes from May 14 are still visible.
- They are stale relative to the May 16 runs, but this fix did not terminate them because no process cleanup was requested and they may still be attached to older sessions.
- They are worth manual review if they persist after normal Codex use, but they are not needed to explain the May 16 empty diff.

## Runtime Artifact Policy
- `auto_runs/` is generated runtime output and should not be committed.
- `.gitignore` now ignores:
  - `auto_runs/`
  - `reports/agent_canary_status.json`

## Fix Summary
- Added the missing agent runner scripts on this branch.
- Replaced event-handler output capture with bounded `ReadToEndAsync()` tasks.
- Repaired the Windows launcher call to use raw `cmd.exe /c call "<codex.cmd>" ...` arguments instead of a quoted `"call"` token.
- Added full terminal artifact guarantees:
  - `status.txt`
  - `final_report.md`
  - `codex_stdout.md`
  - `codex_stderr.md`
  - `codex_exit_code.txt`
- Added an explicit postcondition that converts any accidental `CODEX_RUNNING` return into `AGENT_INTERRUPTED`.
- Added visible canary output and cache-refresh reporting.
