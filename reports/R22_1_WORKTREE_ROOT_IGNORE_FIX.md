# R22.1: Worktree Root Ignore And Hygiene Fix

Date: 2026-05-17

## What Happened

R22 created a supervised isolation worktree inside the control-plane repository tree:

- Worktree path: `D:\_ai_brain\worktrees\workstation_control_plane\001_20260516_135830`
- Branch: `loop/workstation_control_plane/001/20260516_135830`

Because `D:\_ai_brain\worktrees` was not ignored, the main repository detected the runtime worktree root as untracked content.

## Why `git status` Showed `?? worktrees/`

`git status --short` scans the main repo working tree. The new worktree folder sits under that tree (`D:\_ai_brain\worktrees\...`), so Git treated it like any other untracked directory until an ignore rule was added.

## Files Changed

- `.gitignore`
- `WORKSTATION_MANUAL.md`
- `reports/R22_1_WORKTREE_ROOT_IGNORE_FIX.md`

## Fix Applied

1. Added `worktrees/` to `.gitignore`.
2. Confirmed generated worktree reports remain ignored:
   - `reports/WORKTREE_PLAN_*.md`
   - `reports/WORKTREE_STATUS_*.md`
   - `reports/WORKTREE_CREATE_DRY_RUN_*.md`
   - `reports/WORKTREE_CREATE_*.md`
3. Added a short manual note that `worktrees/` is generated runtime workspace and must stay ignored.

## Validation Result

Pre-fix:

- `git status --short` -> `?? worktrees/`

Post-fix:

- `git status --short` -> no untracked `worktrees/` entry
- `git worktree list` -> main + the created loop worktree both present
- `ws worktree-status` -> `Active worktrees: 2`
- `ws ready` -> pass
- `ws agent-hygiene` -> pass
- `git diff --stat` -> only expected R22.1 doc/ignore changes

## Keep Or Remove The Created Worktree

Recommendation: keep it for R23 testing.

Reason:

- It is the first supervised-created isolation worktree.
- It provides a live artifact to validate follow-up status, report, and cleanup behavior.
- R22.1 resolves the Git hygiene issue without requiring deletion or movement.
