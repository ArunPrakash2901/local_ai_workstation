# R20: Worktree Create Dry Run Implementation

Date: 2026-05-16

## Summary

R20 adds `ws worktree-create <project_key> <task_file> --dry-run` as a preview-only command. It mirrors the worktree planning checks and prints the future Git commands without creating a branch or worktree.

## Files Changed

- `.gitignore`
- `WORKSTATION_MANUAL.md`
- `scripts/ws`
- `scripts/ws_worktree_create.sh`
- `reports/R20_WORKTREE_CREATE_DRY_RUN_IMPLEMENTATION.md`

## Behavior Implemented

- rejects use without `--dry-run`
- verifies project lookup from `registry/projects.yaml`
- verifies task file existence
- extracts task ID/title
- requires explicit `Allowed Files`
- checks for a supported Git repo state
- checks for a clean project repo
- computes the future worktree path and branch name
- checks for existing path and branch collisions
- prints preview-only branch/worktree commands
- writes `reports/WORKTREE_CREATE_DRY_RUN_<timestamp>.md`

## Classifications

- `WORKTREE_CREATE_DRY_RUN_READY`
- `BLOCKED_MISSING_DRY_RUN`
- `BLOCKED_PROJECT_NOT_FOUND`
- `BLOCKED_TASK_NOT_FOUND`
- `BLOCKED_MISSING_ALLOWED_FILES`
- `BLOCKED_DIRTY_REPO`
- `BLOCKED_WORKTREE_EXISTS`
- `BLOCKED_BRANCH_EXISTS`
- `BLOCKED_UNSUPPORTED_REPO_STATE`

## Validation Run

Required validation for R20:

- `ws worktree-create workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md`
- `ws worktree-create workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --dry-run`
- `ws worktree-status`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Additional implementation checks:

- `bash -n scripts/ws`
- `bash -n scripts/ws_worktree_create.sh`
- `ws help`
- `git check-ignore -v reports/WORKTREE_CREATE_DRY_RUN_<timestamp>.md`

Observed result during implementation:

- `ws worktree-create ...` without `--dry-run` returned `BLOCKED_MISSING_DRY_RUN` and withheld preview commands.
- `ws worktree-create ... --dry-run` stayed read-only and returned `BLOCKED_DIRTY_REPO` while the control-plane repo contained the in-progress R20 changes.
- `ws worktree-status` passed and reported 1 active worktree, no future worktree root yet, 7 recent planner reports, 2 ready plans, 5 blocked plans, and 0 stale-looking directories.
- `ws ready` passed.
- `ws agent-hygiene` passed.
- shell syntax checks passed.
- `ws help` exposes `worktree-create`.
- generated `WORKTREE_CREATE_DRY_RUN_*.md` reports are ignored by Git.
- `git status --short` showed only the expected R20 implementation files.
- `git diff --stat` showed the tracked R20 edits; the new script and implementation report remain untracked until staged.
- one earlier parallel validation batch hit a transient WSL service timeout; the required commands were rerun sequentially and passed.

## Limitations

- no actual branch creation
- no actual worktree creation
- no cleanup or pruning
- no concurrent-loop locking
- dry-run uses timestamp-based names only
- actual creation remains disabled

## Next Step After R20

Keep creation disabled and decide whether the next increment should be:

- a cross-command consistency audit for `worktree-plan`, `worktree-status`, and `worktree-create --dry-run`, or
- a separate reviewed design for the first real creation command.
