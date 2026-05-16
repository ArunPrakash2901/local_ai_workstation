# R22: Worktree Create Apply Implementation

Date: 2026-05-16

## Summary

R22 extends `ws worktree-create` with a supervised apply mode:

```bash
ws worktree-create <project_key> <task_file> --apply --from-report <dry_run_report>
```

The command can now create isolation metadata only: one new branch and one new Git worktree after report validation and fresh preflight checks. It does not run tasks, start loops, invoke Codex, or modify project source files.

## Files Changed

- `.gitignore`
- `WORKSTATION_MANUAL.md`
- `scripts/ws_worktree_create.sh`
- `scripts/ws_worktree_status.sh`
- `reports/R22_WORKTREE_CREATE_APPLY_IMPLEMENTATION.md`

## Behavior Implemented

- supports mutually exclusive `--dry-run` and `--apply --from-report <report>` modes
- rejects:
  - missing mode
  - `--apply` without `--from-report`
  - `--from-report` without `--apply`
  - combined `--dry-run` and `--apply`
- validates supplied dry-run report:
  - file exists
  - classification is `WORKTREE_CREATE_DRY_RUN_READY`
  - project and task file match
  - timestamp is no older than `15` minutes
  - branch stays inside `loop/<project>/<task>/...`
  - worktree path stays under `D:\_ai_brain\worktrees\<project_key>`
- reruns current project/task/repo/path/branch checks before creation
- creates the approved worktree parent root only when needed
- creates the branch from `main`
- adds the worktree as a second explicit Git step
- attempts safe rollback only for a newly created branch when `worktree add` fails and rollback safety is provable
- writes generated `WORKTREE_CREATE_*.md` apply reports
- makes `ws worktree-status` print active worktree paths in the terminal summary

## Terminal States

- `WORKTREE_CREATED`
- `BLOCKED_MISSING_FROM_REPORT`
- `BLOCKED_STALE_DRY_RUN_REPORT`
- `BLOCKED_REPORT_MISMATCH`
- `BLOCKED_PROJECT_NOT_FOUND`
- `BLOCKED_TASK_NOT_FOUND`
- `BLOCKED_MISSING_ALLOWED_FILES`
- `BLOCKED_DIRTY_REPO`
- `BLOCKED_WORKTREE_EXISTS`
- `BLOCKED_BRANCH_EXISTS`
- `FAILED_BRANCH_CREATE`
- `FAILED_WORKTREE_ADD`
- `FAILED_ROLLBACK_REQUIRED`

## Validation Run

Required validation for R22:

- `ws worktree-create workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --dry-run`
- `ws worktree-create workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --apply --from-report <fresh_report>`
- `ws worktree-status`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Additional implementation checks:

- `bash -n scripts/ws_worktree_create.sh`
- `bash -n scripts/ws_worktree_status.sh`
- `git check-ignore -v reports/WORKTREE_CREATE_<timestamp>.md`

Observed result during implementation:

- `ws worktree-create ... --dry-run` returned `BLOCKED_DIRTY_REPO` because the control-plane repo contains the in-progress R22 changes.
- `ws worktree-create ... --apply --from-report <fresh_blocked_report>` returned `BLOCKED_REPORT_MISMATCH` because the supplied report was not `WORKTREE_CREATE_DRY_RUN_READY`.
- no branch or worktree was created during validation; `git worktree list --porcelain` still showed only the main worktree.
- rejection checks passed:
  - missing mode -> `BLOCKED_MISSING_DRY_RUN`
  - `--apply` without `--from-report` -> `BLOCKED_MISSING_FROM_REPORT`
  - `--from-report` without `--apply` -> `BLOCKED_REPORT_MISMATCH`
  - `--dry-run` combined with `--apply` -> `BLOCKED_REPORT_MISMATCH`
- `ws worktree-status` passed and printed active worktree paths.
- `ws ready` passed.
- `ws agent-hygiene` passed.
- generated `WORKTREE_CREATE_*.md` reports are ignored by Git.
- exact success-path validation that ends in `WORKTREE_CREATED` remains pending until R22 is committed and the same repository is clean again.

## Limitations

- apply mode intentionally does not run any task or loop
- branch creation is fixed to `main`
- cleanup and pruning remain out of scope
- a clean repository is still mandatory immediately before apply
- because `workstation_control_plane` is the same repository being edited for R22, success-path validation of actual creation requires the R22 implementation to be committed first; otherwise the correct result is `BLOCKED_DIRTY_REPO`

## Next Step After R22

After the supervised creation path is exercised from a clean committed baseline, design the next safety layer:

- linking created worktrees back to run folders and task locks before any worktree-aware execution is enabled
