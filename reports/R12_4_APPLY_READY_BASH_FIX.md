# R12.4: Apply-Ready Bash Fix

## Root Cause
Following the R12.3 refinement of the `ws apply-ready` stale-run matching logic, an unbound variable error was triggered: `/mnt/d/_ai_brain/scripts/ws_apply_ready.sh: line 118: PROJECT_KEY_: unbound variable`.

The script runs with `set -u` (strict mode), which treats any reference to an unset variable as an immediate fatal error. On line 118, a string interpolation to conservatively match folder names was written as:
`elif [[ "$d_base" == *"_$PROJECT_KEY_"* ]] && [ -z "$run_project" ]; then`

Because bash interprets `$PROJECT_KEY_` as a reference to a variable named `PROJECT_KEY_` (since underscores are valid in identifiers), it threw the unbound variable error and halted the script.

## Files Changed
- `scripts/ws_apply_ready.sh`: Updated the variable interpolation on line 118 to explicitly encapsulate the variable name in braces (`${PROJECT_KEY}`).

## Exact Line Fixed
**Before:**
```bash
elif [[ "$d_base" == *"_$PROJECT_KEY_"* ]] && [ -z "$run_project" ]; then
```
**After:**
```bash
elif [[ "$d_base" == *"_${PROJECT_KEY}_"* ]] && [ -z "$run_project" ]; then
```

## Validation Result
- `bash -n scripts/ws_apply_ready.sh` returned zero syntax errors.
- Running `ws apply-ready workstation_control_plane <task_file>` successfully executed past the strict mode constraint and correctly hit the `BLOCKED_DIRTY_REPO` preflight rule.
- `ws agent-hygiene` confirmed the overall orchestration logic remains healthy. 

The command is now perfectly stable and robust.
