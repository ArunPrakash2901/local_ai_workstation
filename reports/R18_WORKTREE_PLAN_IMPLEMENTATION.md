# R18: Worktree Plan Implementation

Date: 2026-05-16

## Summary

R18 adds the first executable piece of the R17 design: a read-only `ws worktree-plan <project_key> <task_file>` command. It reports what a future isolated worktree would look like without creating a branch or worktree.

## Files Changed

- `.gitignore`
- `WORKSTATION_MANUAL.md`
- `scripts/ws`
- `scripts/ws_worktree_plan.sh`
- `reports/R18_WORKTREE_PLAN_IMPLEMENTATION.md`

## Checks Implemented

- project lookup from `registry/projects.yaml`
- project path existence
- task file existence
- task ID/title extraction
- explicit `Allowed Files` entries
- current project-repo branch
- clean/dirty repo status
- valid supported git repository state
- existing git worktrees
- proposed future worktree path
- proposed future branch name
- proposed path collision
- proposed branch collision

## Classifications

- `WORKTREE_PLAN_READY`
- `BLOCKED_PROJECT_NOT_FOUND`
- `BLOCKED_TASK_NOT_FOUND`
- `BLOCKED_MISSING_ALLOWED_FILES`
- `BLOCKED_DIRTY_REPO`
- `BLOCKED_WORKTREE_EXISTS`
- `BLOCKED_BRANCH_EXISTS`
- `BLOCKED_UNSUPPORTED_REPO_STATE`

## Validation Run

Validation commands required for R18:

- `ws worktree-plan workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Additional implementation checks:

- `bash -n scripts/ws`
- `bash -n scripts/ws_worktree_plan.sh`
- `ws help`
- `git check-ignore -v reports/WORKTREE_PLAN_<timestamp>.md`

Observed result during implementation:

- `ws worktree-plan` ran read-only and returned `BLOCKED_DIRTY_REPO` while the control-plane repo contained the in-progress R18 changes.
- `ws ready` passed.
- `ws agent-hygiene` passed.
- shell syntax checks passed.
- `ws help` exposes `worktree-plan`.
- generated `WORKTREE_PLAN_*.md` reports are ignored by Git.
- `git status --short` showed only the expected R18 implementation files.
- `git diff --stat` showed the tracked R18 edits; the new script and implementation report remain untracked until staged.

## Limitations

- no worktree creation
- no branch creation
- no loop locking yet
- no `worktree-status`
- no cleanup planner or cleanup apply flow
- proposed names are timestamp-based only; future work should add explicit lock/registry coordination before enabling concurrent loops

## Next Step After R18

Implement the next read-only surface from R17:

- `ws worktree-status`

After planner/status outputs are stable across supervised runs, a later phase can add a dry-run `worktree-create` planner. Actual worktree creation should remain disabled until those read-only surfaces are proven.
