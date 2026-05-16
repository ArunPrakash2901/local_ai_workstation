# R21: Actual Worktree Create Design

Date: 2026-05-16  
Scope: design only. No branch creation, no worktree creation, no cleanup, no loop execution.

## Current Baseline

- `ws worktree-plan` is live and read-only.
- `ws worktree-status` is live and read-only.
- `ws worktree-create <project_key> <task_file> --dry-run` is live and preview-only.
- Dry-run validation on a clean tree returns `WORKTREE_CREATE_DRY_RUN_READY`.
- Future root `D:\_ai_brain\worktrees` does not exist yet.
- Active worktrees: `1`.
- `ws ready`: pass.
- `ws agent-hygiene`: pass.
- Unresolved `CODEX_RUNNING`: `0`.
- Reviewed `CODEX_RUNNING`: `4`.

## Design Decision

Actual creation should reuse the existing command family:

```bash
ws worktree-create <project_key> <task_file> --apply --from-report <dry_run_report>
```

Use the same command, not a separate command, because:

- dry-run and apply are the same operation at different safety levels
- one command keeps parsing, naming, collision checks, and reporting aligned
- the operator can learn one workflow instead of reconciling two similar tools
- reports remain comparable across preview and apply phases

`--dry-run` and `--apply` must remain mutually exclusive. Bare `ws worktree-create ...` must continue to block.

## Mandatory Gates Before Actual Creation

Actual creation must require all of the following:

1. valid `project_key` resolved from the registry
2. valid `task_file`
3. parsed task ID and title
4. explicit `Allowed Files`
5. supported Git repository state with a named current branch
6. clean repository
7. successful `ws ready`
8. successful `ws agent-hygiene`
9. no existing branch conflict
10. no existing target worktree-path conflict
11. a recent matching dry-run report that was reviewed by the operator
12. explicit `--apply`

Recommended additional gate for the first real implementation:

- require current branch `main` unless an explicit future `--base <branch>` design is approved

## Matching Dry-Run Requirement

Actual creation should require a recent matching dry-run report.

Matching keys:

- project key
- task file path
- task ID
- proposed branch name
- proposed worktree path
- base branch
- classification `WORKTREE_CREATE_DRY_RUN_READY`

The apply command must not silently recompute a different branch/path than the reviewed preview. It should load the approved report and execute only the exact reviewed values.

Recommended freshness window:

- maximum age: `15 minutes`

Reasoning:

- short enough that branch/path collisions and repo health are unlikely to drift unnoticed
- long enough for a human review without forcing immediate command chaining
- if the report is older than 15 minutes, require a new dry run

Recommended future syntax:

```bash
ws worktree-create <project_key> <task_file> --apply --from-report reports/WORKTREE_CREATE_DRY_RUN_<timestamp>.md
```

Do not infer "latest report" for the first implementation. The operator should pass the reviewed report explicitly.

## Safe Root Creation

Future root handling should be limited and deterministic:

1. derive the exact approved target path from the dry-run report
2. verify the parent root is exactly `D:\_ai_brain\worktrees`
3. create only the missing parent directories needed for the approved target path
4. use `mkdir -p` only after the resolved path is verified under `WS_HOME/worktrees`
5. record whether each parent existed before creation

The command must never create arbitrary paths outside the approved root.

## Branch Creation Strategy

The first actual implementation should use two explicit Git steps:

```bash
git -C "<repo>" branch "<branch>" "<base_branch>"
git -C "<repo>" worktree add "<worktree_path>" "<branch>"
```

Why not `git worktree add -b` initially:

- separate steps make partial failure easier to report
- the report can record exactly whether the branch exists before `worktree add`
- rollback logic is clearer when branch creation and worktree registration are separate facts

The base branch should come from the reviewed dry-run report and be revalidated before creation.

## Partial Failure Handling

If branch creation succeeds but `git worktree add` fails:

1. stop immediately
2. emit a partial-failure terminal state
3. write a report with:
   - created branch name
   - attempted worktree path
   - failing command
   - stderr
   - root directories created during the attempt
4. run read-only verification:
   - `git branch --list <branch>`
   - `git worktree list --porcelain`
   - path existence check
5. do not continue into any loop execution

## Safe Rollback Policy

Automatic rollback should be conservative.

Safe automatic rollback is allowed only when all are true:

- branch was created by this invocation
- `git worktree add` failed
- the branch still points at the exact expected base commit
- no worktree was registered for that branch
- the target worktree path does not exist

In that narrow case, the command may offer or perform a single automatic rollback step:

```bash
git -C "<repo>" branch -d "<branch>"
```

If any condition is ambiguous, do not rollback automatically. Report `PARTIAL_FAILURE_REQUIRES_REVIEW` and preserve evidence.

Do not auto-delete created directories on first implementation unless they are provably empty and were created by the same invocation. The safer default is to leave them and report them.

## Reports To Write

Future actual creation should write:

1. existing dry-run report:
   - `reports/WORKTREE_CREATE_DRY_RUN_<timestamp>.md`
2. apply report:
   - `reports/WORKTREE_CREATE_APPLY_<timestamp>.md`
3. optional failure evidence report when needed:
   - `reports/WORKTREE_CREATE_APPLY_FAILURE_<timestamp>.md`

The apply report should include:

- linked dry-run report path
- project key
- task file
- task ID/title
- allowed files
- base branch and base commit
- target branch
- worktree path in Windows and WSL forms
- all preflight results
- exact commands executed
- command exit codes
- directories created
- final verification from `git worktree list --porcelain`
- next safe action

Generated apply/failure reports should be ignored by Git unless later policy says to curate selected reports.

## Proposed Terminal States

Ready / success:

- `WORKTREE_CREATE_APPLY_READY`
- `WORKTREE_CREATED`

Input / gate blockers:

- `BLOCKED_MISSING_APPLY`
- `BLOCKED_MISSING_DRY_RUN_REPORT`
- `BLOCKED_STALE_DRY_RUN_REPORT`
- `BLOCKED_DRY_RUN_REPORT_MISMATCH`
- `BLOCKED_PROJECT_NOT_FOUND`
- `BLOCKED_TASK_NOT_FOUND`
- `BLOCKED_MISSING_ALLOWED_FILES`
- `BLOCKED_DIRTY_REPO`
- `BLOCKED_READY_FAILED`
- `BLOCKED_AGENT_HYGIENE_FAILED`
- `BLOCKED_WORKTREE_EXISTS`
- `BLOCKED_BRANCH_EXISTS`
- `BLOCKED_UNSUPPORTED_REPO_STATE`
- `BLOCKED_UNSUPPORTED_BASE_BRANCH`

Execution failures:

- `FAILED_ROOT_CREATE`
- `FAILED_BRANCH_CREATE`
- `FAILED_WORKTREE_ADD`
- `ROLLED_BACK_BRANCH_AFTER_WORKTREE_ADD_FAILURE`
- `PARTIAL_FAILURE_REQUIRES_REVIEW`

The implementation should use one final terminal state per run and write that same state to the report and terminal output.

## How `worktree-status` Should Detect Creation

After creation, `ws worktree-status` should continue to rely on:

- `git worktree list --porcelain` for authoritative active worktrees
- filesystem scan under `D:\_ai_brain\worktrees`

The new worktree should appear as:

- a second active worktree in Git output
- a leaf directory under the configured worktree root
- not a stale-looking directory, because the leaf path matches an active Git worktree

Future status improvements can optionally parse `WORKTREE_CREATE_APPLY_*.md` reports, but active Git metadata should remain the source of truth.

## Operator Workflow After Creation

The first safe operator flow should remain manual and supervised:

1. run and review `ws worktree-create ... --dry-run`
2. run future `ws worktree-create ... --apply --from-report <reviewed_report>`
3. run `ws worktree-status`
4. inspect the new worktree path
5. manually enter the worktree:

```bash
cd /mnt/d/_ai_brain/worktrees/<project_key>/<task_id>_<timestamp>
git status --short
```

6. continue only with an explicitly supervised task workflow

No loop should start automatically just because a worktree exists.

## Why Loop Execution Remains Out Of Scope

Actual worktree creation solves only filesystem and branch isolation. It does not yet solve:

- task locking
- run-folder linkage
- worktree-aware `loop-start`
- worktree-aware `apply-ready`
- worktree-aware `agent-run`
- cleanup lifecycle
- stale/dirty worktree handling
- independent loop scheduling

Those are separate safety problems. Enabling execution before those contracts exist would reintroduce ambiguity even with isolated directories.

## Recommended Implementation Sequence After R21

1. add apply-report schema and dry-run-report matching logic
2. add apply mode behind explicit `--apply --from-report`
3. add root creation plus branch/worktree execution with conservative rollback
4. extend `worktree-status` to summarize apply reports if useful
5. only after creation is stable, design task locking and run-folder linkage

## Manual Status Note

Actual creation is designed but still disabled. The live command remains:

```bash
ws worktree-create <project_key> <task_file> --dry-run
```
