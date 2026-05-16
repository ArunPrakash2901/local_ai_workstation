# R6: Loop Plan Implementation

## Summary
The read-only independent loop planner has been successfully implemented and integrated into the workstation control plane as `ws loop-plan`.

## Files Changed
- `scripts/ws`: Added `loop-plan` to the help menu and command dispatcher.
- `scripts/ws_loop_plan.sh`: New script containing the core read-only planning logic.
- `WORKSTATION_MANUAL.md`: Updated to instruct operators on using `ws loop-plan` to check independent loop eligibility safely without starting unsupervised runs.

## Checks Implemented
The script strictly evaluates the preconditions for independent execution:
1.  **Project Path**: Resolves the project key against `projects.yaml`.
2.  **Repo Path Exists**: Confirms the target directory is available.
3.  **Task File**: Checks for the existence of the task file and the required `Allowed Files:` bounded boundary.
4.  **Dirty Repo**: Ensures the git working tree is completely clean before allowing an automated agent to begin work.
5.  **Canary Status**: Parses `reports/agent_canary_status.json` to verify cloud access.

## Validation Run
Running `ws loop-plan workstation_control_plane <task_file>` correctly identifies the current blocked state (due to the previously diagnosed `CODEX_FAILED` canary limit) and classifies the loop strategy as `BLOCKED_CLOUD_QUOTA`. The next safe fallback command (`ws agent-run ... --mode detect`) is appropriately recommended for a manual handoff.

The script creates a markdown report under `D:\_ai_brain\reports\LOOP_PLAN_<timestamp>.md` and safely exits without modifying any project repositories, creating worktrees, or invoking external AI models.

## Limitations
- This is a `v1` read-only planner. It explicitly notes that it does not dynamically lock or check for stale active runs yet (it notes "unchecked in v1 read-only planner" in the report).
- It only performs diagnosis and classification; the actual implementation of worktrees and concurrent detached execution remains deferred.

## Next Steps
Now that the read-only planner is active, the foundation for R7 (Task Splitting) or further independent loop execution mechanics is safely prepared. 
