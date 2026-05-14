# Task Splitter Hardening Report

Generated: 2026-05-14

## Files Updated

- `D:\_ai_brain\scripts\ws_task_split.sh`
- `D:\_ai_brain\scripts\ws_task_next.sh`
- `D:\_ai_brain\scripts\ws`
- `D:\_ai_brain\WORKSTATION_MANUAL.md`
- `D:\_ai_brain\START_HERE.md`

## Validation Summary

Structured PRD parsing works deterministically without using the local model.

Dry run:

```text
Detected 7 structured task(s).
Would generate 7 task file(s) under /mnt/d/_ai_brain/tasks/generated.
Project key: workstation_control_plane
No files written.
```

Write run:

```text
Detected 7 structured task(s).
Generated 7 task file(s) under /mnt/d/_ai_brain/tasks/generated.
```

## Tasks Detected

- 7

## Tasks Generated

- 7

## Missing-Field Warnings

- None for the workstation PRD validation run

All required fields were present for the structured PRD queue:

- Goal
- Acceptance Criteria
- Risk

## task-next Result

`ws task-next workstation_control_plane` selected a generated task and now prints the source folder explicitly:

```text
Selected task from generated:
/mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md
```

## Generated Task Location

Generated files are written directly under:

`/mnt/d/_ai_brain/tasks/generated`

Example filenames:

- `workstation_control_plane_task_001_stabilize_ws_command_documentation.md`
- `workstation_control_plane_task_002_create_daily_workflow_command.md`
- `workstation_control_plane_task_003_improve_build_loop_reporting.md`
- `workstation_control_plane_task_004_add_prd_to_task_splitter.md`
- `workstation_control_plane_task_005_strengthen_frontier_packet_workflow.md`
- `workstation_control_plane_task_006_add_workstation_self_audit.md`
- `workstation_control_plane_task_007_create_night_run_design_not_implementation.md`

## Remaining Limitations

- Freeform PRD splitting is not implemented yet; `--llm` is only a placeholder.
- Legacy generated split folders from earlier runs still exist under `tasks/generated` and remain counted by `ws task-status`.
- `ws task-next` now prefers the deterministic generated files, but older split artifacts are still present on disk.

## Recommended Next Step

Use the deterministic queue directly:

```bash
ws task-next workstation_control_plane
ws build workstation_control_plane <task_file> --plan-only --max-tasks 1
```

