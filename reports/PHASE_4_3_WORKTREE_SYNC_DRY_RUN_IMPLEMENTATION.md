# Phase 4.3: Worktree Sync Dry-Run Implementation

## Overview
Phase 4.3 introduces the `ws worktree-sync <worktree_path> --dry-run` command. This read-only utility allows the operator to inspect an existing isolated worktree to determine what Git operations are necessary to bring it up to date with the `main` branch. This provides safety and transparency before any automated worktree sync or mutation is actually performed.

## Files Changed
- **`scripts/ws`**: Added `worktree-sync` to the help output and the dispatcher.
- **`scripts/ws_worktree_sync.sh`** (New): Created the shell script that enforces `--dry-run`, handles robust worktree validation (existence, approved root, git status), and outputs the theoretical sync operations.
- **`.gitignore`**: Added the `reports/WORKTREE_SYNC_DRY_RUN_*.md` glob to exclude these dynamically generated diagnostic reports from source control.
- **`WORKSTATION_MANUAL.md`**: Documented `ws worktree-sync <worktree_path> --dry-run` and clarified that it only inspects theoretical git operations without changing repository state.

## Command Behavior
The command `ws worktree-sync <path> --dry-run`:
1. Requires the `--dry-run` flag explicitly.
2. Validates that the target path:
   - Exists and is within the approved `D:\_ai_brain\worktrees` root.
   - Contains a `.git` identifier and is properly listed by `git worktree list`.
3. Assesses the repository state:
   - Ensures the worktree branch has no uncommitted changes (`DIRTY_STATUS`).
   - Retrieves the `HEAD` commit of the worktree and compares it against the `main` branch to derive `AHEAD` and `BEHIND` counts.
4. Outputs an actionable classification:
   - `WORKTREE_SYNC_DRY_RUN_READY`: If the worktree is completely clean, behind main (`>0`), but not ahead (`=0`), indicating a clean fast-forward merge is possible.
   - `WORKTREE_SYNC_NOT_NEEDED`: If the worktree is completely clean and matches `main` exactly (`ahead=0, behind=0`).
   - Various block states (`BLOCKED_DIRTY`, `BLOCKED_DIVERGED`, `BLOCKED_INVALID_WORKTREE`, etc.) otherwise.
5. Saves a comprehensive markdown diagnostic report in `reports/`.

## Validation Run
The following checks were executed successfully:
- `bash -n` confirmed syntax correctness.
- The command `ws worktree-sync /mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830 --dry-run` correctly analyzed the existing drift. It correctly identified the behind-main worktree as `WORKTREE_SYNC_DRY_RUN_READY` and proposed the preview command: `git -C D:\_ai_brain\worktrees\workstation_control_plane\001_20260516_135830 merge --ff-only main`.
- Subsequent `ws worktree-review`, `ws ready`, `ws agent-hygiene`, and general git status commands confirmed no system corruption, no side effects, and that all files appropriately tracked.

## Limitations
- **Actual Sync Deferred**: This phase does not implement actual worktree synchronization. The proposed merge or reset commands remain preview-only.

## Next Step
- Finalize the actual worktree sync execution lane (`ws worktree-sync <path> --apply`) in a subsequent phase based on the stable constraints verified by this dry-run.