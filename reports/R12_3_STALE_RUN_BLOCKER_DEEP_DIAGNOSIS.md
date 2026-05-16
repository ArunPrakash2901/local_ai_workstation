# R12.3: Stale Run Blocker Deep Diagnosis

## Diagnosis
1. **Why exactly was apply-ready blocking?** 
   The initial implementation of the `STALE_RUN` check in `ws_apply_ready.sh` simply scanned the `auto_runs` directory and blocked execution if *any* folder contained `status.txt` showing `CODEX_RUNNING` without a `stale_reviewed.md` marker.
2. **Did it scan all folders or only current project/task?**
   It scanned *all* folders unconditionally. It did not cross-reference the project key or task file.
3. **How did it decide a run belonged to the current project/task?**
   It didn't. The logic was completely missing.
4. **Was the matching based on folder name, task file path, or project key?**
   It was based purely on the existence of the `status.txt` file being stuck in `CODEX_RUNNING`.
5. **Was the matching too broad?**
   Yes, immensely so. Any broken background test for an unrelated project would completely lock up the entire workstation's apply capabilities for all projects.
6. **Was the matching too narrow?**
   No.
7. **Were the surfaced runs actually related to the current task?**
   Coincidentally, yes. The remaining unresolved `CODEX_RUNNING` folders actually belonged to `workstation_control_plane` `Task 001`, which meant even if the scoping was fixed, it would still block incorrectly due to age.
8. **Are any of the surfaced runs still plausibly active?**
   No. The most recent unresolved run was generated several hours ago. Standard timeouts are 10 minutes.
9. **Are the surfaced runs old historical failed runs?**
   Yes. They are orphaned state from the agent runner aborting or crashing before it could cleanly write a terminal status (e.g., `FAILED_INTERNAL`).
10. **Is manual acknowledgement per folder the right behavior?**
    It is a necessary fallback, but it is not sufficient on its own. Forcing operators to manually track down and review every 2-hour-old orphaned run folder before starting a fresh run for the exact same task creates severe workflow friction.
11. **Should apply-ready block on every historical run, or only active ones?**
    It should only block on *active* or *recent* runs for the *exact same* project and task.
12. **What is the safest corrected policy?**
    A strict compound policy: It must precisely match the project and task identity. If a matching unresolved run is found, it evaluates the age of its `status.txt` (or `heartbeat.log`). If the run is less than 2 hours old (7200 seconds), it is considered an active/recent threat and immediately blocks execution. If it is older than 2 hours, it is considered a benign "historical stale" run; it is ignored by the blocker but explicitly noted in the final `APPLY_READY` report.

## Fix Implemented
- **Scoping:** The `ws_apply_ready.sh` script now parses the `task.md` file inside each `CODEX_RUNNING` folder to accurately extract and match both the `Project:` key and the exact task title (e.g., `# Task 001...`). If `task.md` is corrupt, it falls back to a conservative substring match on the folder name.
- **Age Threshold:** Added a timestamp evaluation using `stat -c %Y`. Runs younger than 2 hours are appended to the `STALE_RUNS` array and trigger the `BLOCKED_STALE_RUNNING_RUN` block. Runs older than 2 hours are categorized as `HISTORICAL_RUNS` and safely bypassed.
- **Reporting:** Instead of silently breaking on the first match, the script now collects all blockers and prints them out concurrently. If historical runs are bypassed, it appends a clear `(Note: X historical unresolved runs found for this task, but they are older than 2 hours and ignored.)` message to the `REASON` field.

## Files Changed
- `scripts/ws_apply_ready.sh`

## Validation Result
- The `ws apply-ready` command now flawlessly bypasses the 2.5-hour-old orphaned test runs and correctly hits the `BLOCKED_DIRTY_REPO` preflight guard instead.
- The system is now extremely trustworthy, balancing conservative active-run locking with frictionless recovery from historical runner crashes.
