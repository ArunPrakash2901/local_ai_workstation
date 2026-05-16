# R23: Worktree Lifecycle Review And Synchronization Design

Date: 2026-05-17

## Current Observed State

- Main worktree: `/mnt/d/_ai_brain` at `6e1c61f` on `main`
- Loop worktree: `/mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830` at `2e74c9e` on `loop/workstation_control_plane/001/20260516_135830`
- `ws worktree-status`: `Active worktrees: 2`, `Stale-looking directories: 0`
- Loop worktree path exists and is clean (`git status --short` empty inside that worktree)
- Creation reports confirm a successful supervised creation:
  - dry-run ready report: `WORKTREE_CREATE_DRY_RUN_20260516_135830_636223626.md`
  - apply success report: `WORKTREE_CREATE_20260516_135906_536353642.md` (`WORKTREE_CREATED`)

## 1) Is The Created Worktree Valid?

Yes. It is valid as a created isolation artifact:

- branch exists
- worktree path exists
- `git worktree list` includes it
- creation report shows `WORKTREE_CREATED`
- no stale marker in `ws worktree-status`

## 2) Is The Worktree Branch Behind Main?

Yes.

- `main`: `6e1c61f`
- loop branch: `2e74c9e`
- `git rev-list --left-right --count main...loop/...` -> `1 0`
  - meaning `main` is ahead by `1`, loop branch is ahead by `0`

## 3) What Caused The Base Drift?

`main` advanced after the worktree was created.

- loop worktree/branch were created from `2e74c9e`
- later commit on `main`: `6e1c61f Ignore generated worktree root`

This is normal lifecycle drift, not a creation failure.

## 4) Should Worktrees Be Updated/Rebased Before Use?

Yes, before task execution begins.

Minimum rule:

- if worktree branch is behind `main`, mark as `BEHIND_MAIN` and require review/sync first

Rationale:

- prevents applying work in stale isolation against a newer control-plane baseline
- reduces merge/rebase surprise during later integration

## 5) Older-Main Worktree: Recreate Or Fast-Forward?

Default policy should be:

- if worktree is clean and has no task execution artifacts: prefer **recreate** (new dry-run/apply) for deterministic lineage
- if worktree is already prepared with meaningful review context: allow **sync** path first (`--dry-run` preview, then explicit operator action)

For this current case:

- worktree is clean and unused for execution
- recommended action: recreate is simplest and lowest risk

## 6) What Should `ws worktree-status` Report When Behind Main?

It should explicitly show drift per active worktree:

- `Ahead/Behind vs main` counts
- lifecycle state (`READY` or `BEHIND_MAIN`)
- base commit used at creation (from `WORKTREE_CREATE` report when available)

Suggested status line example:

- `loop/... -> BEHIND_MAIN (behind 1, ahead 0)`

## 7) Lifecycle States

Proposed state model:

- `CREATED`
  - worktree exists and branch exists; no readiness assessment yet
- `READY`
  - clean worktree, branch aligned with `main`, not in use, review checks passed
- `BEHIND_MAIN`
  - branch is behind `main` by at least one commit
- `DIRTY`
  - uncommitted changes present in that worktree
- `IN_USE`
  - an explicit run lock/session is active for that worktree
- `REVIEW_NEEDED`
  - metadata mismatch, unknown provenance, or stale checks requiring human review
- `SAFE_TO_REMOVE`
  - clean, no active lock, no pending review, and explicitly marked removable

## 8) What Should Operator Inspect Before Use?

Before any task execution in a worktree:

1. `git status --short` in that worktree
2. branch name and HEAD commit
3. ahead/behind vs `main`
4. creation report lineage (project/task/report freshness)
5. allowed-files scope for the task
6. no active conflicting lock/run for the same task
7. latest `ws ready` and `ws agent-hygiene` pass

## 9) Cleanup Rules For Later

Do not remove by default. Later cleanup should require:

1. not `IN_USE`
2. clean worktree (`DIRTY` disqualifies auto cleanup)
3. no unresolved review flags
4. explicit operator confirmation
5. dry-run cleanup preview first

`BEHIND_MAIN` alone must not auto-delete; it should route to review/sync decision first.

## 10) What Command Should Come Next?

Recommended next command to design first:

- `ws worktree-review`

Reason:

- review must exist before sync/remove decisions are safe and consistent
- it can compute lifecycle state (`READY`, `BEHIND_MAIN`, `DIRTY`, etc.) and produce actionable next-step hints

Follow-up sequence:

1. `ws worktree-review`
2. `ws worktree-sync --dry-run`
3. `ws worktree-remove --dry-run`

## 11) Why Execution In Worktrees Is Still Out Of Scope

Execution inside worktrees should remain out of scope until review/sync is designed because:

- branch drift is already present and not yet governed by command policy
- no formal worktree state gate currently blocks stale execution
- cleanup/sync semantics are not codified yet
- lock coordination for multi-run safety is still incomplete

Enabling execution before lifecycle gating would allow stale or ambiguous state to enter the task pipeline.

## Manual Update Decision

No manual edit was required for R23.

Current manual already states:

- `worktree-create --apply` creates isolation only
- tasks are not run by creation
- operator should inspect with `ws worktree-status`
