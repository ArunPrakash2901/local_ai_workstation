# Auto Runner Grounded Patch Repair

## Latest Run
- Run Folder: `/mnt/d/_ai_brain/auto_runs/20260514_144746_workstation_control_plane_001_stabilize_ws_command_documentation`
- Final Status: `BLOCKED_LOCAL_WITH_CHANGES`

## Exact Root Cause
The patch generation stage is now grounded on real inputs:
- actual allowed file contents are read from disk
- docs tasks use an anchored edit mode rather than invented diff context
- `ws help` output is included in the prompt

The remaining failure is model behavior, not patch extraction or patch validation:
- the coder model returned `NO_PATCH` on both attempts
- no valid anchored edits were produced
- therefore no patch was generated for apply

## What Was Fixed
- The auto runner now reads the actual allowed documentation files before asking for edits.
- The docs path uses anchored edit operations instead of freeform invented diffs.
- The prompt includes the current `ws help` output.
- The runner still validates allowed files and rejects edits that are outside the allowlist.

## Current Status
- Grounded patch generation: implemented
- Patch extraction/validation: implemented
- Local apply result for this task: still blocked because the coder produced `NO_PATCH`

## Files Changed
- `scripts/ws_auto.sh`
- `scripts/ws_auto_report.sh`

## Validation Run
- `bash -n scripts/ws_auto.sh`
- `bash -n scripts/ws_auto_report.sh`
- `bash -n scripts/ws_auto_state.sh`
- `bash -n scripts/ws_auto_model_router.sh`
- `ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --plan-only --max-tasks 1 --max-minutes 5`
- `ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --apply --branch --max-tasks 1 --max-attempts 2 --max-files 5 --max-minutes 10 --stop-on-fail`

## Recommendation
The next fix is not another patch parser change. The task/spec path needs either:
- a deterministic docs patcher for this docs-only task, or
- a stronger task definition / model prompt that results in actual anchored edits instead of `NO_PATCH`.

