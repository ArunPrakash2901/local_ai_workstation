# Phase 4.11: Worktree Agent Execution Implementation

## Overview
Phase 4.11 completes the supervised execution lane for AI agents targeting isolated worktrees. This implementation extends the `ws agent-run-worktree` command to support actual codebase mutation using the `--apply --from-dry-run` syntax. It ensures all executions are anchored to a verified, clean, and synced worktree, strictly maintaining the integrity of the main repository.

## Files Changed
- **`scripts/ws_agent_run.ps1`**: Enhanced the Windows-native agent runner to support a `-RepoOverride` parameter. This allows the runner to target an arbitrary worktree path instead of the default project path defined in the registry.
- **`scripts/ws_agent_run_worktree.sh`**: Extended to support the `--apply` mode. Implemented exhaustive preflight gatekeeping (including dry-run packet verification, worktree alignment, and cleanliness checks) and orchestrated the delegation to the enhanced PowerShell runner. Added post-execution artifact normalization and strict "Allowed Files" enforcement logic.

## Command Behavior
The command `ws agent-run-worktree <key> <task> --worktree <path> --apply --from-dry-run <packet>`:
1. **Verifies Dry-Run Packet**: Ensures the provided packet was generated within 15 minutes and matches the current project, task, worktree, branch, and HEAD commit.
2. **Strict Preflight**: Confirms both the main repository and the target worktree are perfectly clean. Validates that `ws worktree-review` for the target environment returns `READY`.
3. **Isolated Execution**: Invokes the agent runner targeting the isolated worktree root. Main repo working copy remains untouched.
4. **Artifact Capture**: Generates a new `auto_runs` folder with comprehensive execution evidence, including normalized Markdown logs for `stdout`, `stderr`, and `git status`.
5. **Differential Validation**: Performs a post-run analysis to ensure all mutations occurred strictly within the "Allowed Files" boundary defined in the task.
6. **Classification**:
   - `CODEX_COMPLETED_SAFE_DIFF`: Success, changes within bounds.
   - `CODEX_COMPLETED_UNSAFE_DIFF`: Success, but one or more changes violated the allowlist.
   - `CODEX_FAILED_PROVIDER`: Failure due to quota, auth, or timeout.
   - `CODEX_COMPLETED_NO_DIFF`: Completed without any file changes.

## Validation Run
- **Worktree Sync & Review**: Verified the target worktree `001_20260516_135830` is `READY`.
- **Dry-Run**: Generated a `WORKTREE_AGENT_DRY_RUN_READY` packet.
- **Apply Execution**: Ran the command with `--apply`. 
  - Preflight checks passed successfully.
  - Successfully delegated to `ws_agent_run.ps1` with the worktree override.
  - Captured the `CODEX_FAILED_PROVIDER` state (expected in this environment due to missing provider credentials).
  - Confirmed the main repository remained perfectly clean.
  - Verified all run artifacts were correctly stored and categorized in the new `auto_runs/` folder.

## Limitations
- **Merge-Back**: This implementation does not automatically merge changes from the worktree back to `main`. All changes remain uncommitted in the isolated environment for manual review.
- **Commit/Push**: Automatic Git commit and push operations are intentionally omitted to maintain strict human supervision.

## Next Step
Implement the `ws feature-run --apply` integration to fully close the loop between feature strongholds and these verified execution lanes.