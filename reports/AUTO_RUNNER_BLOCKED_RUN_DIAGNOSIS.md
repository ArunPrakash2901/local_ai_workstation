# Auto Runner Blocked Run Diagnosis

## Blocked Run
- Run folder: `D:\_ai_brain\auto_runs\20260514_135757_workstation_control_plane_001_stabilize_ws_command_documentation`
- Current branch at the time: `auto/workstation_control_plane/001-20260514_135819`

## Why BLOCKED_LOCAL Happened
- The task asked for documentation consistency across `ws help`, `START_HERE.md`, and `WORKSTATION_MANUAL.md`.
- The task file did not define `Allowed Files`.
- `ws_auto` wrote a fallback `allowed_files.txt` containing `not specified`.
- `ws_apply_guard.sh` treated that as a real allowlist and rejected the patch because it touched `START_HERE.md`.
- The first local diff was therefore blocked before apply, test, or completion.

## Why BLOCKED_CODEX Happened
- Codex escalation was sent after the local block.
- Codex returned advice, but not an applyable patch.
- The retry path correctly avoided unsafe application, but the run still had no patch to apply.
- With no safe Codex patch and the earlier local block unresolved, the run remained blocked.

## What This Is
- Primary issue: task spec / Allowed Files mismatch.
- Secondary issue: docs task was correctly touching `START_HERE.md` and `WORKSTATION_MANUAL.md`, but the runner had no way to infer a conservative docs allowlist.
- Not the primary issue: patch application logic.
- Not the primary issue: Codex escalation transport.

## Smallest Safe Fix
- When a task omits `Allowed Files`, synthesize a conservative allowlist from explicit documentation files named in the task body, goal, or acceptance criteria.
- Keep the allowlist narrow to the files the task actually references.
- Do not broaden apply guard rules globally.

## Files Changed
- `D:\_ai_brain\scripts\ws_auto.sh`
- `D:\_ai_brain\reports\AUTO_RUNNER_BLOCKED_RUN_DIAGNOSIS.md`

## Validation
- `bash -n /mnt/d/_ai_brain/scripts/ws_auto.sh`
- `bash -n /mnt/d/_ai_brain/scripts/ws_auto_report.sh`
- `bash -n /mnt/d/_ai_brain/scripts/ws_auto_state.sh`
- `bash -n /mnt/d/_ai_brain/scripts/ws_auto_codex_bridge.sh`
- `bash -n /mnt/d/_ai_brain/scripts/ws_auto_model_router.sh`
- `ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --plan-only --max-tasks 1 --max-minutes 5`

## Result
- Plan-only smoke completed cleanly.
- The runner now infers `START_HERE.md` and related docs when the task explicitly names them, while keeping the guard narrow.

## Next Safe Command
```bash
bash /mnt/d/_ai_brain/scripts/ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --apply --branch --max-tasks 1 --max-attempts 2 --max-files 5 --max-minutes 10 --stop-on-fail
```
