# Auto Runner Second Block Diagnosis

## Run Inspected
- Run Folder: `/mnt/d/_ai_brain/auto_runs/20260514_140727_workstation_control_plane_001_stabilize_ws_command_documentation`
- Command: `ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --apply --branch --max-tasks 1 --max-attempts 2 --max-files 5 --max-minutes 10 --stop-on-fail`

## Exact Root Cause
The task did not carry a real `Allowed Files` list. The generated task stored the placeholder text `not specified`, and `ws_auto.sh` treated that placeholder as an actual allowlist entry instead of normalizing it away.

Because of that:
- `allowed_files.txt` in the run stayed effectively empty of real paths
- docs-only inference never reached the guard input for the apply path
- `ws_apply_guard.sh` saw `START_HERE.md` as outside Allowed Files
- the run blocked locally before tests

## Why This Was Still Blocking
This was not a branch problem, max-files problem, or patch-generation problem.

It was the allowlist source-of-truth bug:
- task metadata contained `Allowed Files: not specified`
- `ws_auto.sh` used that placeholder as if it were a valid list
- the guard therefore rejected the docs patch

## Smallest Safe Fix Applied
Updated `scripts/ws_auto.sh` so `not specified` is normalized away before:
- building the context pack
- building the planner/coder prompts
- writing `allowed_files.txt` for apply runs

If the task has no explicit allowlist, the runner now infers a narrow docs allowlist from the task text before guard time.

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
The plan-only smoke run completed successfully and created:
- `/mnt/d/_ai_brain/auto_runs/20260514_141142_workstation_control_plane_001_stabilize_ws_command_documentation`

## Next Safe Command
Re-run the bounded apply command for the same task.
