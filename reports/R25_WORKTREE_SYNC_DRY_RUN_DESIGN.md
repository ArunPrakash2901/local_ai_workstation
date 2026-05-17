# R25: Worktree Sync Dry-Run Design

Date: 2026-05-17

## Current Observed State

- Worktree: `/mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830`
- Branch: `loop/workstation_control_plane/001/20260516_135830`
- `ws worktree-review` classification: `BEHIND_MAIN`
- Worktree `HEAD`: `2e74c9ea671bdb6a9546c0ae4a4dd5e3a4bd5ffa`
- Current `main`: `629660351e887a2315380068166333002656170b`
- Behind `main`: `3`
- Ahead of `main`: `0`
- Dirty: `No`

The earlier R24 snapshot recorded the same worktree as behind by `2`. The live validation for R25 shows behind by `3`, which means `main` advanced again after that snapshot. This is expected lifecycle drift and reinforces why sync planning must re-read current state immediately before any future apply path.

## 1) Sync Policy For Loop Branches

The first sync policy should be **fast-forward-only**, not merge or rebase.

- A clean loop branch that is behind `main` and ahead by `0` does not need history rewriting.
- `merge` would add no value when a fast-forward is available.
- `rebase` is unnecessary and creates avoidable policy complexity for a branch with no unique commits.
- `recreate-from-main` remains a valid separate operator choice for unused worktrees, but it should not be the default behavior of a `sync` command.

For future implementation, `ws worktree-sync` should preview the equivalent of a fast-forward-only update and refuse any state that cannot be updated without interpretation.

## 2) Safest Policy For Clean Behind-Only Worktrees

For a clean worktree with:

- `behind main > 0`
- `ahead main = 0`
- no uncommitted changes

the safest policy is:

1. classify it as eligible for sync preview
2. propose a fast-forward-only update to the current `main`
3. require a fresh review again before any later actual sync command

This preserves branch identity, avoids destructive recreation, and keeps the operator's mental model simple.

## 3) Dirty Worktrees

Dirty worktrees should be blocked from sync preview and any future actual sync.

Reason:

- uncommitted changes make the intended synchronization boundary ambiguous
- even a clean fast-forward target can interact with local files in ways that deserve an explicit operator decision first

Expected dry-run state:

- `BLOCKED_DIRTY`

## 4) Ahead-Of-Main Or Diverged Worktrees

Ahead-of-main and diverged worktrees should both be blocked.

- `ahead > 0, behind = 0` means the branch contains unique commits and needs review, not blind sync
- `ahead > 0, behind > 0` means histories diverged and requires a human choice between integration strategies

Expected dry-run states:

- `BLOCKED_AHEAD_OF_MAIN`
- `BLOCKED_DIVERGED`

## 5) First Implementation Scope

Yes. The first implementation should be dry-run only:

```bash
ws worktree-sync <worktree_path> --dry-run
```

Rationale:

- the workstation only just gained reliable review state
- the current loop worktree already demonstrates normal base drift
- a dry-run surface lets the policy harden before branch mutation is enabled

No actual sync, merge, rebase, reset, checkout, or branch mutation should be enabled in the first implementation.

## 6) Exact Dry-Run Output

The command should print:

- terminal state
- report path
- resolved worktree path
- branch name
- worktree `HEAD`
- current `main`
- ahead/behind counts against `main`
- dirty status
- approved-root status
- selected policy: `FAST_FORWARD_ONLY`
- exact command that would be run later if actual sync is ever enabled
- next safe action

For the current worktree, the eventual preview would look conceptually like:

```bash
git -C /mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830 merge --ff-only main
```

The dry-run command must print that command only. It must not run it.

## 7) Terminal States

Recommended terminal states for the future dry-run command:

- `WORKTREE_SYNC_DRY_RUN_READY`
- `WORKTREE_SYNC_NOT_NEEDED`
- `BLOCKED_MISSING_DRY_RUN`
- `BLOCKED_INVALID_WORKTREE`
- `BLOCKED_OUTSIDE_APPROVED_ROOT`
- `BLOCKED_DIRTY`
- `BLOCKED_AHEAD_OF_MAIN`
- `BLOCKED_DIVERGED`
- `BLOCKED_REVIEW_NEEDED`
- `BLOCKED_UNSUPPORTED_STATE`

Suggested mapping:

- clean + behind-only -> `WORKTREE_SYNC_DRY_RUN_READY`
- already aligned with `main` -> `WORKTREE_SYNC_NOT_NEEDED`
- any ambiguous or unsafe condition -> one of the explicit blocked states

## 8) Report Artifact

The dry-run command should write:

- `reports/WORKTREE_SYNC_DRY_RUN_<timestamp>.md`

The report should include:

- input and resolved worktree paths
- branch
- `HEAD` and `main` commits
- ahead/behind counts
- dirty status
- approved-root result
- selected policy
- preview-only command
- blockers, if any
- next safe action
- a clear statement that no sync action was executed

It should be added to `.gitignore` when implementation begins.

## 9) Validation Required Before Any Future Actual Sync

Before a later real sync mode is ever enabled, require all of the following:

1. fresh `ws worktree-review <worktree_path>`
2. `ws ready`
3. `ws agent-hygiene`
4. worktree still exists and is still listed by `git worktree list`
5. path still passes approved-root checks
6. worktree is still clean
7. branch is still behind-only (`behind > 0`, `ahead = 0`)
8. current `main` and branch commits are re-read immediately before mutation
9. the operator has reviewed a matching recent dry-run report
10. no active loop/execution lock exists for that worktree once lock tracking is available

## 10) Why Task Execution Remains Out Of Scope

Sync only restores the base branch relationship to `main`. It does not prove that:

- the task is still valid
- the allowed-file boundary is still appropriate
- the worktree is safe for agent execution
- run-folder linkage and locking are correct
- supervised apply gates have passed

Task execution must remain separate until sync policy, execution gating, and cleanup behavior are all explicit.

## Recommended Next Step

Implement the read-only planner:

- `ws worktree-sync <worktree_path> --dry-run`

Keep actual sync disabled until the dry-run command has been exercised against:

- behind-only worktrees
- already-aligned worktrees
- dirty worktrees
- ahead-of-main branches
- diverged branches

## Validation Run

- `ws worktree-review /mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830`
- `ws worktree-status`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Observed validation result:

- `ws worktree-review` returned `BEHIND_MAIN`
- live drift was `behind 3`, `ahead 0`, `dirty No`
- `ws worktree-status` reported `2` active worktrees and `0` stale-looking directories
- `ws ready` passed
- `ws agent-hygiene` passed
- working tree was clean before this report was created

