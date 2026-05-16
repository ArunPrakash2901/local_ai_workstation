# R17: Worktree Isolation Design for Future Independent Loops

Date: 2026-05-16  
Scope: design only. No worktree creation, no branch cleanup, no run-folder mutation.

## Current Context

- `ws ready`: pass
- `ws agent-hygiene`: pass
- `ws loop-status`: pass
- Agent branches: 12
- Unresolved stale `CODEX_RUNNING`: 0
- Reviewed stale `CODEX_RUNNING`: 4
- `night-run`: design-only

## 1) Why Same-Repo Parallel Loops Need Worktree Isolation

Parallel loops against one checkout are unsafe because they can collide on:

- index/working tree state
- branch checkout state (`HEAD` moves)
- uncommitted local files
- run artifact attribution (which loop changed what)

Worktree isolation gives each loop:

- independent working directory
- independent branch checkout
- deterministic cleanup boundary
- auditable mapping from loop run -> path -> branch

## 2) Proposed Worktree Location

Primary layout:

- `D:\_ai_brain\worktrees\<project_key>\<task_id>_<timestamp>`

Example:

- `D:\_ai_brain\worktrees\workstation_control_plane\001_20260516_233000`

Constraints:

- never inside project repo root
- never under `auto_runs/`
- one worktree directory per loop execution

## 3) Branch Naming Scheme

Worktree loop branch naming should be deterministic and grep-friendly:

- `loop/<project_key>/<task_id>/<timestamp>`

Example:

- `loop/workstation_control_plane/001/20260516_233000`

Rules:

- timestamp must be UTC
- branch must be created from validated base (default `main`)
- branch name must be unique before worktree creation

## 4) WSL/Windows Path Mapping

Canonical storage should keep both forms:

- Windows: `D:\_ai_brain\worktrees\...`
- WSL: `/mnt/d/_ai_brain/worktrees/...`

Design contract:

- orchestration state files store both paths explicitly
- no runtime inference from string replacement only
- `wslpath` conversion should be validated during preflight

## 5) Preflight Checks Before Creating a Worktree

Required checks:

1. root and registry paths resolve
2. base branch exists and is clean (`main` by default)
3. `main` and `origin/main` policy gate passes (or explicit override policy)
4. target branch does not already exist unless reuse mode is explicit
5. target worktree directory does not already exist
6. project repo is accessible and not locked
7. loop lock for `<project_key>/<task_id>` is not already held
8. disk space threshold passes
9. `ws agent-hygiene` and `ws ready` minimum health policy passes

If any check fails, creation is blocked with a structured reason.

## 6) Preventing Duplicate Loop Use (Project/Task/Branch Collisions)

Use a lockfile registry under workstation control plane, for example:

- `D:\_ai_brain\state\worktree_locks\<project_key>__<task_id>.lock`

Lock contents:

- run id
- branch name
- worktree path (Windows + WSL)
- owner command (`loop-start`, `agent-run`, etc.)
- created timestamp

Creation must be atomic:

- fail if lock exists and points to active or unresolved run
- require explicit release step on terminal state

## 7) Future Worktree Cleanup Model

Cleanup phases should be separate from loop execution:

1. discover (`ws worktree-status`)
2. classify (`active`, `clean-closed`, `dirty-closed`, `orphaned`)
3. plan (`ws worktree-plan`)
4. apply with explicit confirmation (`ws worktree-cleanup --apply`)

No implicit deletion:

- never auto-delete dirty worktrees
- never delete branch and worktree in one hidden step

## 8) What to Do if a Worktree Is Dirty

Dirty worktree policy:

- mark status `DIRTY_CLOSED`
- block automatic removal
- require human action:
  - commit
  - export patch
  - explicitly abandon with documented reason

Suggested output:

- diff summary path
- untracked file list
- recommendation to review before any cleanup

## 9) Linking Run Folders to Worktree Paths

Every run folder should include immutable references:

- `worktree_info.json`
- fields:
  - `worktree_path_windows`
  - `worktree_path_wsl`
  - `loop_branch`
  - `base_branch`
  - `base_commit`
  - `worktree_created_at_utc`

This ensures stale-run/hygiene/audit reports can trace filesystem context precisely.

## 10) Future Interaction Model for Existing Commands

### `ws loop-plan`

- remains read-only
- validates whether worktree creation would be allowed
- outputs planned branch/path/lock decisions

### `ws loop-start`

- in future worktree mode:
  - acquires lock
  - creates branch + worktree
  - runs loop in isolated path
  - records worktree metadata in run folder

### `ws apply-ready`

- should verify:
  - worktree lock status
  - branch/worktree consistency
  - no unresolved stale-run conflicts for same task

### `ws agent-run`

- should support optional isolated execution target:
  - default current behavior (no forced worktree)
  - opt-in `--worktree` mode after design hardening

## 11) Why First Implementation Must Be Dry-Run Planner

Dry-run first is required because it validates safety contracts before mutation:

- naming collisions
- lock behavior
- path conversions
- health gating
- report/audit linkage

This reduces risk of:

- orphaned worktrees
- branch confusion
- duplicate parallel loop corruption

## 12) Proposed Future Commands (Not Implemented)

- `ws worktree-plan <project_key> <task_file> [--base main]`
- `ws worktree-create --dry-run <project_key> <task_file> [--base main]`
- `ws worktree-status [--project <project_key>] [--all]`

Optional later:

- `ws worktree-cleanup-plan`
- `ws worktree-cleanup --apply`

## Rollout Recommendation

R17 output should be followed by a narrow implementation sequence:

1. planner only (`worktree-plan` and `worktree-create --dry-run`)
2. status surfaces and lock registry
3. controlled create path behind explicit flag
4. cleanup plan command
5. cleanup apply command with hard safety gates

No worktree creation should be enabled until planner outputs are stable across multiple supervised runs.

