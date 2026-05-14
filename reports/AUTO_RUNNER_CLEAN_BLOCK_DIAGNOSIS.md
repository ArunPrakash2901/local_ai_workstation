# Auto Runner Clean Block Diagnosis

## Run Inspected
- Run Folder: `/mnt/d/_ai_brain/auto_runs/20260514_141637_workstation_control_plane_001_stabilize_ws_command_documentation`
- Status: `BLOCKED_LOCAL`

## Exact Root Cause
The local coder produced a plain unified diff that used `--- START_HERE.md` / `+++ START_HERE.md` style headers instead of git-style `--- a/START_HERE.md` / `+++ b/START_HERE.md`.

`ws_apply_guard.sh` only recognizes changed file paths from git-style headers. Because of that, the guard saw:
- `patch contains no changed file paths`

That is why the run blocked without changing any files.

## Why No Files Changed
- The patch was parsed as present, but the guard could not extract any valid changed paths.
- `git apply --check` never got a usable patch to validate because the guard rejected it first.
- `test_output.md` stayed empty because tests never ran.

## Smallest Safe Fix Applied
Updated `scripts/ws_auto.sh` so extracted diffs are normalized before guard time:
- `--- FILE` becomes `--- a/FILE`
- `+++ FILE` becomes `+++ b/FILE`
- the coder prompt now explicitly asks for git-style unified diffs with `a/` and `b/` prefixes

This keeps the change narrow and only affects the auto-run patch path.

## Files Changed
- `scripts/ws_auto.sh`

## Tests Run
- `bash -n scripts/ws_auto.sh`
- `bash -n scripts/ws_auto_report.sh`
- `bash -n scripts/ws_auto_state.sh`
- `bash -n scripts/ws_auto_codex_bridge.sh`
- `bash -n scripts/ws_auto_model_router.sh`
- `ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --plan-only --max-tasks 1 --max-minutes 5`

## Validation Result
- Plan-only smoke completed successfully.
- New run folder:
  `/mnt/d/_ai_brain/auto_runs/20260514_142136_workstation_control_plane_001_stabilize_ws_command_documentation`

## Next Safe Command
Re-run the bounded apply command for the same docs task.
