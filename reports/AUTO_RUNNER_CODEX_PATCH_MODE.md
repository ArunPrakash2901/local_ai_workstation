# Auto Runner Codex Patch Mode Report

## Root Cause
- Codex escalation was still treated as an advice-only loop.
- The runner retried the local coder after Codex instead of treating Codex output as a patch candidate.
- That made read-only Codex sessions fail to progress even when the model had enough context to produce a diff.

## Files Changed
- `D:\_ai_brain\scripts\ws_auto.sh`
- `D:\_ai_brain\scripts\ws_auto_report.sh`
- `D:\_ai_brain\scripts\ws_auto_state.sh`

## What Changed
- Codex escalation now requests patch-only output.
- The packet includes actual allowed file contents when they are small and safe to load.
- Codex output is parsed as a patch candidate, saved to `codex_patch.diff`, and validated locally.
- Local validation artifacts are written to:
  - `codex_patch_validation.md`
  - `codex_patch_apply.md`
- Advice-only Codex replies now end as `BLOCKED_CODEX_ADVICE_ONLY`.
- Invalid Codex patches now end as `BLOCKED_CODEX_PATCH_INVALID`.
- Valid Codex patches are validated with the apply guard, `git apply --check`, and local apply before tests continue.

## Validation
- `bash --noprofile --norc -n /mnt/d/_ai_brain/scripts/ws_auto.sh`
- `bash --noprofile --norc -n /mnt/d/_ai_brain/scripts/ws_auto_report.sh`
- `bash --noprofile --norc -n /mnt/d/_ai_brain/scripts/ws_auto_state.sh`
- `bash --noprofile --norc -n /mnt/d/_ai_brain/scripts/ws_auto_codex_bridge.sh`
- `ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --plan-only --max-tasks 1 --max-minutes 5`

## Smoke Result
- Run folder: `/mnt/d/_ai_brain/auto_runs/20260514_150330_workstation_control_plane_001_stabilize_ws_command_documentation`
- Status: `PLAN_ONLY`
- Files changed: no
- Codex used: no

## Notes
- The bridge remains a transport layer.
- The patch-mode behavior is now enforced in the local auto runner.
