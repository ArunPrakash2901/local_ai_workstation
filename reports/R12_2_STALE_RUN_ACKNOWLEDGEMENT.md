# R12.2: Stale Run Acknowledgement Workflow

## Root Cause
The `ws apply-ready` command properly implemented a safety blocker (`BLOCKED_STALE_RUNNING_RUN`) to prevent parallel, concurrent loops from stomping on each other when a `CODEX_RUNNING` lock exists. However, earlier test runs that failed ungracefully left behind historical, unresolved `CODEX_RUNNING` folders. Because we strictly follow a non-destructive data-retention policy, auto-deleting these folders is unsafe. The system lacked a mechanism to explicitly acknowledge a run as historical/stale without destroying its diagnostic value.

## Files Changed
- `scripts/ws_agent_mark_stale_reviewed.sh`: Created a new script that drops a `stale_reviewed.md` artifact into a stuck `CODEX_RUNNING` folder.
- `scripts/ws`: Exposed `agent-mark-stale-reviewed` in the command dispatcher and help menu.
- `scripts/ws_apply_ready.sh`: Updated the active-run scanner to ignore folders containing a `stale_reviewed.md` artifact, effectively unblocking the workspace.
- `scripts/ws_agent_hygiene.sh`: Updated to parse and display counts for both unresolved and reviewed stale `CODEX_RUNNING` folders in its summary and markdown reports.

## Marker Design
The `stale_reviewed.md` file is a simple, timestamped text file written directly inside the target run folder (`auto_runs/<run>/stale_reviewed.md`). This guarantees that the acknowledgement metadata is coupled to the run itself, preventing registry desynchronization if folders are manually archived later.

## Safety Rules
- The script strictly targets `auto_runs`.
- The script strictly targets only folders explicitly holding `status.txt` == `CODEX_RUNNING`.
- No run folders, artifacts, or data are moved or deleted. The workflow is purely additive acknowledgement.

## Validation Result
- `ws agent-hygiene` correctly reported 4 unresolved stale folders.
- Running `ws agent-mark-stale-reviewed 20260514_191435_...` successfully created the marker.
- Running `ws agent-hygiene` correctly adjusted the counts (3 unresolved, 1 reviewed).
- Re-running `ws apply-ready` confirmed that the specific marked run no longer triggered `BLOCKED_STALE_RUNNING_RUN`. Instead, the system successfully progressed to the expected `BLOCKED_DIRTY_REPO` preflight failure.
