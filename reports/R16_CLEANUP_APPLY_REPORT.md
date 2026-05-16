# R16 Cleanup Apply Report

Date: 2026-05-16  
Mode: supervised cleanup apply (strictly constrained to R15-safe actions)

## Baseline and Guardrails

- Plan source: `reports/R15_BRANCH_AND_STALE_RUN_CLEANUP_PLAN.md`
- Re-baseline commit: `fb78c79`
- Drift guard after re-baseline: `HEAD` and `origin/main` remained `fb78c79` throughout apply
- Out-of-scope protections honored:
  - no unique-commit branch deletions
  - no human-review branch deletions
  - no run folder deletions or moves
  - no project repo modifications
  - no night-run/apply/cloud actions

## Actions Executed

### 1) Stale run action (R15 conditional)

Investigation confirmed unresolved stale profile persisted for:

- `D:\_ai_brain\auto_runs\20260516_142401_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`

Applied action:

- `ws agent-mark-stale-reviewed 20260516_142401_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`

Result:

- Success
- `stale_reviewed.md` created (evidence preserved)
- No run folder deletion/move

### 2) Branch cleanup actions (R15 explicit safe list only)

Deleted branches:

- `post-queue-workstation-updates`
- `agent/workstation_control_plane/001-20260516_172407`
- `agent/workstation_control_plane/001-20260516_150312`
- `agent/workstation_control_plane/001-20260516_150712`
- `agent/workstation_control_plane/001-20260516_151453`
- `agent/workstation_control_plane/001-20260516_151525`
- `agent/workstation_control_plane/001-20260516_151725`
- `agent/workstation_control_plane/001-20260516_152159`
- `agent/workstation_control_plane/001-20260516_152438`
- `fix/agent-run-terminal-state`
- `r3-agent-contract-validation`
- `r4-agent-hygiene`
- `r4-retention-policy`
- `r5-independent-loop-design`
- `r6-loop-plan`

Branches kept (by rule):

- `main`
- all branches currently in `git branch --no-merged main` (unique-commit set / human-review set)

## Skipped / Deferred Items

- Archiving stale run folders: skipped (R15 marked as later phase)
- Any deletion outside explicit R15-safe list: skipped
- Remote branch cleanup: skipped (not in approved R15 apply scope)

## Errors and Recovery

Initial deletion attempt returned permission-denied lock errors under current sandbox context:

- `cannot lock ref ... .lock: Permission denied`

Recovery:

- reran the exact same approved deletion list with escalated permission
- all approved branch deletions succeeded

No data-loss actions were performed.

## Post-Cleanup Validation Results

Executed:

- `git status --short`
- `git branch -vv`
- `ws agent-hygiene`
- `ws ready`
- `ws loop-status`

Results:

- `git status --short`: only R16 reports are untracked
- `git branch -vv`: only `main` + non-merged branch set remain; deleted branches absent
- `ws agent-hygiene`: pass  
  report: `D:\_ai_brain\reports\AGENT_HYGIENE_20260516_231953.md`
  - Agent branches: `12` (from 20)
  - Unresolved stale `CODEX_RUNNING`: `0` (from 1)
  - Reviewed stale `CODEX_RUNNING`: `4` (from 3)
- `ws ready`: pass  
  report: `D:\_ai_brain\reports\READINESS_20260516_231953.md`
- `ws loop-status`: pass  
  report: `D:\_ai_brain\reports\LOOP_STATUS_20260516_231953.md`

## Final State Summary

- Cleanup completed as a narrow R15-scoped apply.
- Diagnostic stale-run evidence was preserved.
- No broad cleanup or non-approved branch manipulation occurred.

