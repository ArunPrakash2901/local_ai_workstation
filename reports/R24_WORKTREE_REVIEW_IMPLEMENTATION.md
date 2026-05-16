# R24: Worktree Review Implementation

Date: 2026-05-17

## Summary

R24 adds `ws worktree-review <worktree_path>` as a read-only lifecycle check for existing worktrees. It inspects validity, approved-path placement, branch drift against `main`, and dirty state without creating, syncing, removing, or otherwise changing any worktree.

## Files Changed

- `.gitignore`
- `WORKSTATION_MANUAL.md`
- `scripts/ws`
- `scripts/ws_worktree_review.sh`
- `reports/R24_WORKTREE_REVIEW_IMPLEMENTATION.md`

## Behavior Implemented

- requires a worktree path argument
- verifies path existence
- verifies the path is a Git worktree
- verifies the path appears in `git worktree list`
- records branch, `HEAD`, and `main` commits
- computes ahead/behind counts against `main`
- checks whether the worktree is dirty
- verifies the path is either the main worktree or under `D:\_ai_brain\worktrees`
- writes `reports/WORKTREE_REVIEW_<timestamp>.md`

## Classifications

- `READY`
- `BEHIND_MAIN`
- `DIRTY`
- `AHEAD_OF_MAIN`
- `DIVERGED`
- `INVALID_WORKTREE`
- `OUTSIDE_APPROVED_ROOT`
- `REVIEW_NEEDED`

## Validation Run

Required validation for R24:

- `ws worktree-review /mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830`
- `ws worktree-status`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Additional implementation checks:

- `bash -n scripts/ws`
- `bash -n scripts/ws_worktree_review.sh`
- `ws help`
- `git check-ignore -v reports/WORKTREE_REVIEW_<timestamp>.md`

Observed result during implementation:

- `ws worktree-review /mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830` returned `BEHIND_MAIN`.
- The review report recorded:
  - branch `loop/workstation_control_plane/001/20260516_135830`
  - worktree `HEAD` `2e74c9ea671bdb6a9546c0ae4a4dd5e3a4bd5ffa`
  - `main` `765a56de02e94c888f28ed67c744fc02e5a6b301`
  - behind count `2`
  - ahead count `0`
  - dirty `No`
- `ws worktree-status` passed after a sequential rerun.
- `ws ready` passed after a sequential rerun.
- `ws agent-hygiene` passed after a sequential rerun.
- shell syntax checks passed.
- `ws help` exposes `worktree-review`.
- generated `WORKTREE_REVIEW_*.md` reports are ignored by Git.
- one parallel WSL validation batch hit a transient WSL service failure; the required checks were rerun sequentially and passed.

## Limitations

- no sync, rebase, merge, remove, or execution behavior
- no lock awareness yet
- no report linkage back to a specific `WORKTREE_CREATE` report yet
- path approval is structural only: main worktree or descendants of the configured worktree root

## Next Step After R24

Design the next read-only lifecycle surface:

- `ws worktree-sync --dry-run`

It should consume `worktree-review` results and preview the allowed synchronization action without changing the worktree.
