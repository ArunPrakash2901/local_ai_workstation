# Phase 4.10: Real Worktree Agent Execution Design

## Executive Summary
Following the implementation of the dry-run worktree agent adapter (Phase 4.9), this document outlines the design for actual, supervised agent execution within isolated worktrees. The core goal is to enable AI agents (Codex/Gemini) to safely mutate code inside a verified worktree environment while keeping the main repository pristine and ensuring all changes are strictly bounded by "Allowed Files" relative to the worktree root.

## Architectural Questions & Answers

### 1. Should real execution extend ws agent-run-worktree with --apply --from-dry-run?
**Yes.** The execution command should follow the established pattern:
`ws agent-run-worktree <project_key> <task_file> --worktree <path> --apply --from-dry-run <packet_path>`
This ensures that real execution is always preceded by a successful, manual review of a dry-run packet.

### 2. Should a recent WORKTREE_AGENT_DRY_RUN_READY packet be mandatory?
**Yes.** The `--apply` lane must strictly require a valid packet where `status.txt` is `WORKTREE_AGENT_DRY_RUN_READY`.

### 3. How recent should the dry-run packet be?
The packet should be considered "fresh" if it was generated within the last 15-30 minutes. More critically, the `main_head` and `wt_head` commit hashes stored in `metadata.json` must exactly match the current state of the main repo and the target worktree to prevent race conditions.

### 4. How should the command invoke Codex from the worktree root rather than main?
The `ws_agent_run_worktree.sh` script (or its delegates) must explicitly change the working directory (`cd`) to the target worktree path before invoking the underlying runner. It must also ensure all file paths passed to the runner are adjusted to be relative to the worktree root.

### 5. Should implementation reuse ws_agent_run.ps1 or create a separate worktree-native runner?
**It should reuse `ws_agent_run.ps1` with enhancements.** Creating a separate runner would lead to logic duplication and maintenance debt. `ws_agent_run.ps1` should be updated to accept an optional `-RepoRoot` or `-WorktreePath` parameter, allowing it to anchor its Git operations and file mutations to a specific directory instead of assuming the default workstation root.

### 6. What changes are needed so stdout/stderr/final reports are captured safely?
The runner's logging and report-writing logic must be made relative to the `auto_runs/` folder of the workspace that *initiated* the run (usually the main `_ai_brain` folder), but the *content* of those reports must reflect the worktree context. Terminal output redirection must be carefully handled to ensure the parent orchestrator captures the full execution transcript.

### 7. How should allowed files be enforced relative to the worktree root?
The "Allowed Files" list must be treated as relative paths from the worktree root. The runner must prepend the worktree path to these entries before performing any security checks or mutation attempts. Any attempt to write to a path that resolves outside the worktree's filesystem boundary must be blocked.

### 8. How should post-run validation check only the worktree diff, not main?
Post-run validation should use `git -C <worktree_path> diff` and `git -C <worktree_path> status`. It must ignore the state of the main repository entirely during this check, focusing solely on the mutations accrued within the isolated environment.

### 9. How should the run folder link back?
The `metadata.json` in the resulting run folder should include:
- `feature_id`: Extracted from the worktree name or dry-run packet.
- `worktree_path`: The absolute path to the execution environment.
- `branch`: The isolated branch name.
- `dry_run_packet`: The path to the referenced preflight artifact.
- `task_file`: The original implementation plan.

### 10. What terminal states should exist?
- `WORKTREE_AGENT_APPLY_SUCCESS`
- `WORKTREE_AGENT_APPLY_FAILED`
- `WORKTREE_AGENT_BLOCKED_STALE_PACKET`
- `WORKTREE_AGENT_BLOCKED_DIRTY_WORKTREE`
- `WORKTREE_AGENT_BLOCKED_BY_READY_CHECK`
- `WORKTREE_AGENT_PROVIDER_ERROR` (Quota/Timeout)

### 11. What should happen if Codex quota fails?
The execution must immediately halt with `WORKTREE_AGENT_PROVIDER_ERROR`. The worktree state is preserved, allowing the operator to manually resume, reset, or wait for quota reset. No automatic retries should occur in this supervised lane.

### 12. What should happen if Codex modifies files outside Allowed Files?
The runner's internal guardrails must prevent the mutation from ever being written to disk. If a violation is detected post-facto (e.g., via `git status`), the run must be flagged as `FAILED` and `BLOCKED`, and the operator must be notified to manually revert or fix the scope.

### 13. What should happen if Codex exits 0 but leaves no diff?
The run should be classified as `SUCCESS` (technically no errors occurred), but the report should explicitly note "No mutations detected," advising the operator that the agent may have hallucinated completion or found no work to do.

### 14. How should the operator review and merge worktree changes later?
The operator should use `ws worktree-review <path>` to see the final diff. If satisfied, they can manually merge the branch into `main` using standard Git commands, or use a future `ws worktree-merge` utility.

### 15. Why merge-back to main must remain a separate later phase.
Keeping merge-back separate enforces a "Review-Before-Commit" workflow. Isolated execution ensures that AI-generated code is proven in a "sandbox" (the worktree) before it ever touches the canonical codebase. Automatically merging back would bypass the workstation's core safety philosophy of supervised integration.

## Next Steps
1. Enhance `ws_agent_run.ps1` to support a `-WorktreePath` override.
2. Implement the `--apply` logic in `ws_agent_run_worktree.sh` to consume dry-run packets and invoke the enhanced runner.
3. Validate a real mutation (e.g., a documentation update) inside an isolated worktree.