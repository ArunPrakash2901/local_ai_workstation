# R9: Supervised Loop Start (Local Plan) Implementation

## Summary
The supervised `ws loop-start` command has been successfully implemented in its initial MVP state. To enforce maximum safety during this phase, it strictly supports `--mode local-plan`, which delegates execution to the read-only local planner (`ws build --plan-only`). Cloud apply paths and unsupervised concurrency (worktrees, parallel execution, night loops) are actively blocked.

## Files Changed
- `scripts/ws`: Added `loop-start` to the command dispatcher.
- `scripts/ws_loop_start.sh`: A new script that parses arguments, enforces the `--mode local-plan` constraint, consumes the read-only `ws loop-plan` diagnostic, and orchestrates the local planning phase.
- `.gitignore`: Updated to ignore transient `reports/LOOP_START_*.md` logs.
- `WORKSTATION_MANUAL.md`: Documented the new command, explicitly noting that it does not currently apply codebase mutations or invoke Codex.

## Behavior Implemented
1. **Mode Enforcement:** `ws loop-start` rejects any mode other than `local-plan`. Flags like `--parallel` or `--night` result in an immediate `BLOCKED_UNSUPPORTED_MODE` terminal state.
2. **Preflight Checks:** It dynamically executes `ws loop-plan` to verify the project, task boundary (`Allowed Files`), repository cleanliness, and canary status.
3. **Execution:** If preflight passes, it executes `ws build <project> <task> --plan-only`.
4. **State Reporting:** It writes a timestamped execution log to `reports/LOOP_START_<timestamp>.md` and outputs a clean terminal summary identifying the terminal state and the path to the resulting build artifact.

## Validation Run
Executing `ws loop-start` against the currently dirty `workstation_control_plane` repository accurately triggered the preflight safeguards. The planner identified uncommitted changes, classifying the run as `BLOCKED_DIRTY_REPO`. `loop-start` respected this classification, aborted execution, printed the correct terminal state, and instructed the operator to resolve the blockers.

## Limitations
- Cloud apply mutations are strictly deferred.
- No worktree orchestration or detached parallel background execution exists yet.
- Active run tracking relies on folder scanning rather than a synchronized locking database.

## Next Steps
With safe, supervised local-planning orchestration proven, the next phase can focus on integrating worktree isolation or unlocking supervised cloud-apply modes when the canary is fully stable.
