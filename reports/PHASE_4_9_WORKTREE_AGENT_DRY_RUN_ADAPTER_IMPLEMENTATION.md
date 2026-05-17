# Phase 4.9: Worktree Agent Dry-Run Adapter Implementation

## Overview
Phase 4.9 implements the `ws agent-run-worktree` command in a dry-run-only capacity. This command serves as the critical bridge for running agent tasks inside isolated, verified worktrees instead of the main repository. It ensures all execution prerequisites are met and prepares a complete execution packet for a future supervised agent run.

## Files Changed
- **`scripts/ws`**: Added `agent-run-worktree` to the help menu (under "Agent & Loops") and added the dispatcher logic to call the new shell script.
- **`scripts/ws_agent_run_worktree.sh`** (New): Implemented the dry-run logic, including argument parsing, robust validations (project registry, task structure, worktree alignment, and cleanliness), and packet generation.

## Command Behavior
The command `ws agent-run-worktree <project_key> <task_file> --worktree <path> --dry-run [flags]` performs the following:
1. **Mandates `--dry-run`**: Explicitly rejects any attempt to run without the dry-run flag in this phase.
2. **Validates Project & Task**: Ensures the project exists in `registry/projects.yaml` and the task file exists with explicit "Allowed Files" defined.
3. **Validates Worktree**:
   - Ensures the path exists and is under `D:\_ai_brain\worktrees`.
   - Confirms the worktree is active and listed by `git worktree list`.
   - Verifies the worktree is `READY` (synced and aligned with main) via `ws worktree-review`.
4. **Validates Git Status**: Ensures both the target worktree and the main repository are perfectly clean.
5. **Generates Dry-Run Packet**: Creates a timestamped folder under `auto_runs/` containing:
   - `status.txt`: `WORKTREE_AGENT_DRY_RUN_READY`
   - `task.md`: Copy of the target task.
   - `worktree_context.md`: Details about the worktree path, branch, and HEAD.
   - `agent_prompt.md`: The theoretical prompt that would be sent to the AI agent.
   - `allowed_files.md`: Explicit list of files authorized for mutation.
   - `metadata.json`: Machine-readable execution context.
   - `dry_run_report.md`: Comprehensive human-readable preflight summary.

## Validation Run
- **Syntax Check**: `bash -n` confirmed script integrity.
- **Worktree Review**: Confirmed worktree `001_20260516_135830` is `READY`.
- **Dry-Run Execution**: Executed against the `stabilize-ws-command-documentation` task.
  - Successfully parsed "Allowed Files" (using an improved regex supporting multiple styles).
  - Correctly identified clean repo states.
  - Successfully generated the dry-run packet with `WORKTREE_AGENT_DRY_RUN_READY` classification.
- **System Stability**: `ws ready` and `ws agent-hygiene` remain passing.

## Limitations
- **Dry-Run Only**: This implementation strictly prevents any mutation or AI provider invocation.
- **Allowed Files Resolution**: While the files are listed, this phase does not verify if the files actually exist inside the worktree (this will be part of the actual apply lane).

## Next Step
Implement the supervised `ws agent-run-worktree --apply` lane, which will consume these verified packets and delegate to the underlying Windows-native agent execution logic.