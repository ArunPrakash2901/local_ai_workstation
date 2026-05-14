# Auto Runner Recovery Report

## Summary
- WSL recovered: yes
- Smoke test status: `PLAN_ONLY`
- Smoke run folder: `D:\_ai_brain\auto_runs\20260514_131726_workstation_control_plane_001_stabilize_ws_command_documentation`
- Auto status count: `PLAN_ONLY = 1`
- No project files changed during the smoke test: yes

## Root Cause
- `ws auto` initially created the run folder too late, after long preflight and model-routing work.
- The early run path also referenced helpers before they were defined, which caused immediate `NameError` failures during smoke tests.
- Several long-running calls were still opaque and did not write heartbeat updates while waiting.

## Fixes Made
- Created the auto run folder immediately for each task.
- Wrote `status.txt` as `STARTED` immediately.
- Added `heartbeat.log` and heartbeat writes after major steps and during long waits.
- Moved task parsing and run initialization ahead of model routing.
- Wrapped long external calls with timeout-aware polling and heartbeat logging.
- Routed local model calls through `ollama_call.py` as watched subprocesses.
- Added timeouts to graphify, test, apply-guard, report, and Codex bridge calls.
- Patched `ws_auto_report.sh` so plan-only runs report `Files Changed: no`.

## Files Updated
- `D:\_ai_brain\scripts\ws_auto.sh`
- `D:\_ai_brain\scripts\ws_auto_state.sh`
- `D:\_ai_brain\scripts\ws_auto_report.sh`
- `D:\_ai_brain\scripts\ws_auto_codex_bridge.sh`
- `D:\_ai_brain\WORKSTATION_MANUAL.md`
- `D:\_ai_brain\START_HERE.md`
- `D:\_ai_brain\LOCAL_AI_STACK_STATUS.md`

## Smoke Artifacts
- `status.txt`
- `heartbeat.log`
- `run_config.md`
- `model_roles.md`
- `context_pack.md`
- `local_plan.md`
- `final_report.md`

## Validation
- `bash -n` passed for the touched auto scripts.
- `bash /mnt/d/_ai_brain/scripts/ws auto-status` works.
- `bash /mnt/d/_ai_brain/scripts/ws auto-runs` works.
- `ws auto ... --plan-only --max-tasks 1 --max-minutes 5` completed cleanly in about 22 seconds.

## Next Safe Command
```bash
bash /mnt/d/_ai_brain/scripts/ws open-auto latest
```
