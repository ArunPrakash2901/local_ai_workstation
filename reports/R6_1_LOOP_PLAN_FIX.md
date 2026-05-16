# R6.1: Loop Plan Path and Noise Fix

## Root Cause
1. **Path Handling Bug:** When `wslpath -u` was passed a path that was *already* a valid absolute WSL path (e.g., `/mnt/d/...`), it incorrectly stripped the leading slash, resulting in a relative path like `mnt/d/...`. Because the script executed from the root directory, the file existence check `[ ! -f "$WSL_TASK_FILE" ]` evaluated against a non-existent relative path and incorrectly threw `BLOCKED_MISSING_ALLOWED_FILES`.
2. **Git Noise:** The read-only planner generated `LOOP_PLAN_<timestamp>.md` artifacts in the `reports/` directory. Because these were not included in `.gitignore`, they cluttered the git working directory as untracked files on every execution.

## Files Changed
- `scripts/ws_loop_plan.sh`: Introduced a `to_wsl_path` wrapper function that checks if a path already begins with `/` before attempting to pass it through `wslpath -u`.
- `.gitignore`: Appended `reports/LOOP_PLAN_*.md` to ensure these transient planning reports are safely ignored.

## Diagnosis Details
- **Did the task path exist?** Yes, the canonical generated task path `/mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md` definitely existed. The failure was strictly an artifact of the WSL path translation bug.
- **Handling Generated Reports:** The `LOOP_PLAN_*.md` reports are transient planning artifacts (similar to `AGENT_HYGIENE_*.md`). By adding them to `.gitignore`, we preserve the ability to read the latest plan output without polluting the git working tree or requiring manual cleanup. Existing reports are now safely ignored.

## Validation Results
1. **Command:** `ws loop-plan workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md`
2. **Outcome:** Successfully located the file, parsed the explicit `Allowed Files` boundary, and accurately evaluated the Git repository state, correctly returning `BLOCKED_DIRTY_REPO` due to the uncommitted fixes.
3. **Workstation State:** `git status --short` confirms the repository is free of untracked report noise.
