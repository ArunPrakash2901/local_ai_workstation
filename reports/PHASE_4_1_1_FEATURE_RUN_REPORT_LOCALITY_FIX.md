# Phase 4.1.1: Feature Run Dry-Run Report Locality Fix

## Root Cause
In the initial implementation of the `ws feature-run` command, the `runs_dir` was incorrectly configured to write the generated markdown report to the global `D:\_ai_brain\runs` directory instead of the correct feature stronghold directory (`D:\_ai_brain\features\<project_key>\<feature_id>\runs`). The `runs_dir = ws_home / "runs"` path was incorrectly copied from general run paths. The Feature Stronghold design enforces that a feature owns its run evidence.

## Files Changed
- **`scripts/ws_feature_run.sh`**: Modified the `runs_dir` resolution variable to point to `feature_dir / "runs"` instead of `ws_home / "runs"`. Ensure that this runs directory is created inside the specific feature folder.

## Validation Result
- `bash -n scripts/ws_feature_run.sh` succeeded without syntax errors.
- Running `ws feature-run /mnt/d/_ai_brain/features/workstation_control_plane/stabilize-ws-command-documentation --dry-run` successfully produced the report inside the designated feature stronghold `runs/` directory.
- The `loop_log.md` inside the feature stronghold correctly recorded the absolute path referencing the internal `runs/` folder.
- Validation checks like `ws feature-status`, `ws ready`, and `ws agent-hygiene` ran correctly without any regressions.

## Historical Runtime Evidence
The previous top-level reports stored in `D:\_ai_brain\runs` should be retained. They serve as valid historical runtime evidence reflecting the initial test execution iterations. They do not pollute the core repository state and can be ignored or eventually archived via standard cleanup scripts if needed.