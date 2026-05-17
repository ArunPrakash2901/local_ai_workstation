# Phase 4.4: Supervised Worktree Sync Apply Design

## Executive Summary
Phase 4.3 successfully introduced the `ws worktree-sync <worktree_path> --dry-run` command, which allows operators to safely preview the Git operations required to synchronize a drifted worktree with the `main` branch. This document designs the actual apply execution lane for syncing, which will ensure worktrees can be consistently and deterministically brought to a `READY` state before they are used for automated agent execution (`ws feature-run --apply`).

Currently, the known worktree `001_20260516_135830` is clean but behind `main` and qualifies for a `git merge --ff-only main` operation.

## Architectural Questions & Answers

### 1. Should actual sync use --apply --from-report?
**Yes.** The actual sync command should be invoked as `ws worktree-sync <worktree_path> --apply --from-report <dry_run_report>`. This mirrors the pattern of other safe workstation operations (like `cleanup` and `worktree-create`). It forces human validation of the dry-run output prior to mutation.

### 2. Should a recent WORKTREE_SYNC_DRY_RUN_READY report be mandatory?
**Yes.** An explicit `--from-report` reference pointing to a report with the `WORKTREE_SYNC_DRY_RUN_READY` classification must be strictly enforced.

### 3. How recent should the dry-run report be?
The dry-run report should be considered valid only if the target worktree's `HEAD` and the `main` branch's `HEAD` still match the commit hashes recorded in the report. Timestamp age is a secondary guard (e.g., < 30 minutes), but strict commit hash validation is mandatory to prevent race conditions.

### 4. Should sync use git merge --ff-only main?
**Yes.** The primary sync mechanism for isolated feature worktrees that have not yet had apply-runs should be `git merge --ff-only main`. This guarantees a linear history. If the worktree has diverged (ahead > 0 and behind > 0), a fast-forward is impossible, and the system should block the sync, delegating resolution (e.g., manual rebase or worktree recreation) to the operator.

### 5. What preflight checks must be rerun immediately before mutation?
Before executing the sync operation, the command must rerun the core read-only checks from the dry-run:
- Worktree path validation (exists, approved root, listed worktree).
- Uncommitted changes check (must be completely clean).
- Commit hash validation (ensure current `HEAD` and `main` exactly match the referenced dry-run report).
- System checks: `ws ready` and `ws agent-hygiene` should be passing.

### 6. What should happen if the worktree becomes dirty after dry-run?
The sync must **immediately abort**. Syncing a dirty worktree risks silent data loss or complex merge states. The operator must manually stash, commit, or clean the worktree before retrying.

### 7. What should happen if the branch becomes ahead or diverged?
If the worktree is ahead of `main` (but behind = 0), a sync is not needed (`WORKTREE_SYNC_NOT_NEEDED`). If it is diverged (ahead > 0 AND behind > 0), the fast-forward merge will fail. The `worktree-sync` command must explicitly block on diverged branches to avoid autonomous non-linear merges or interactive rebase states.

### 8. What report should be written after actual sync?
A timestamped execution report (`reports/WORKTREE_SYNC_APPLY_<timestamp>.md`) must be written detailing:
- The target worktree.
- The referenced dry-run report.
- The exact git command executed (`git merge --ff-only main`).
- The `stdout`/`stderr` of the git operation.
- The final commit hash of the worktree `HEAD`.
- The final terminal state (`WORKTREE_SYNC_APPLY_SUCCESS` or `WORKTREE_SYNC_APPLY_FAILED`).

### 9. Should the feature loop_log be updated if the worktree is linked to a feature?
**Yes.** If the `feature_id` can be cleanly derived from the worktree name and the corresponding feature stronghold exists under `features/`, the sync apply script should append an entry to the feature's `loop_log.md` (e.g., `Worktree Synced to main`).

### 10. What terminal states should exist?
- `WORKTREE_SYNC_APPLY_SUCCESS`
- `WORKTREE_SYNC_APPLY_FAILED` (e.g., Git error during the merge)
- `WORKTREE_SYNC_BLOCKED_DIRTY`
- `WORKTREE_SYNC_BLOCKED_DIVERGED`
- `WORKTREE_SYNC_BLOCKED_STALE_REPORT` (The branch heads no longer match the dry-run report)
- `WORKTREE_SYNC_NOT_NEEDED`

### 11. What rollback behavior is safe?
No automated rollback should be attempted. Since the only supported sync mechanism is a fast-forward merge (`--ff-only`) on a strictly clean worktree, failures will typically occur before any mutation happens. If the Git command fails unexpectedly, the worktree remains isolated, and the operator can investigate.

### 12. How should ws worktree-review confirm READY after sync?
After a successful sync, the worktree's `HEAD` will match `main`. A subsequent run of `ws worktree-review <worktree_path>` will detect that the worktree is no longer `BEHIND_MAIN`. As long as it is clean, approved, and matches `main`, `worktree-review` will return the `READY` classification, fulfilling the requirement for execution.

### 13. Why feature-run --apply should remain blocked until sync apply is proven.
The execution gatekeeper (`ws feature-run --apply`) strictly requires the target worktree to be `READY`. It currently cannot achieve this state because the worktree is `BEHIND_MAIN`. Only once the `worktree-sync --apply` workflow is implemented and proven can a worktree be deterministically transitioned from `BEHIND_MAIN` to `READY`, thereby unlocking the supervised `feature-run` execution lane.

## Next Steps
- Implement `ws worktree-sync <path> --apply` in Phase 4.5.
- Prove the sync works on the drifted `001_20260516_135830` worktree.
- Validate that `ws worktree-review` subsequently returns `READY`.
- Proceed with `ws feature-run --apply` implementation.