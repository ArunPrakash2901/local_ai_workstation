# Auto Runner Patch Validation Repair

## Run Inspected
- Run Folder: `/mnt/d/_ai_brain/auto_runs/20260514_142427_workstation_control_plane_001_stabilize_ws_command_documentation`
- Result: `BLOCKED_LOCAL`

## Root Cause
The apply guard passed, but the patch itself was invalid.

Evidence from the run:
- `apply_guard.md` says `SAFE`
- `git apply --check` failed with `error: corrupt patch`
- the generated diff contained malformed hunk headers such as `@@ -1,5 +1,6 *`
- the diff also carried markdown/code-fence artifacts instead of a clean git-style patch

This is a patch extraction / patch validation problem, not an Allowed Files problem.

## Smallest Safe Fix Applied
Updated `scripts/ws_auto.sh` to:
- strip and normalize extracted diffs
- validate patch syntax before `git apply`
- reject malformed hunk headers early
- save rejected patches to `rejected_patch.diff`
- attempt one local patch repair with the coder model using the git apply error and rejected patch
- stop with `PATCH_INVALID` / `BLOCKED_PATCH_INVALID` if the repair still fails

Updated reporting helpers:
- `scripts/ws_auto_report.sh`
- `scripts/ws_auto_state.sh`

## Files Changed
- `scripts/ws_auto.sh`
- `scripts/ws_auto_report.sh`
- `scripts/ws_auto_state.sh`
- `reports/AUTO_RUNNER_PATCH_VALIDATION_REPAIR.md`

## Tests Run
- `bash -n scripts/ws_auto.sh`
- `bash -n scripts/ws_auto_report.sh`
- `bash -n scripts/ws_auto_state.sh`
- `bash -n scripts/ws_auto_codex_bridge.sh`
- `bash -n scripts/ws_auto_model_router.sh`
- `ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --plan-only --max-tasks 1 --max-minutes 5`

## Validation Result
The plan-only smoke run completed successfully:
- `/mnt/d/_ai_brain/auto_runs/20260514_143111_workstation_control_plane_001_stabilize_ws_command_documentation`

## Next Safe Command
Re-run the bounded apply command for the same docs task.
