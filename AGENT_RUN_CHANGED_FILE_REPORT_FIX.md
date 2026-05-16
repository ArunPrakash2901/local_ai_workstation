# Agent Run Changed File Report Fix

## Root Cause
- `Invoke-Git` used a parameter named `$Args`.
- In PowerShell, `$args` is an automatic variable. The parameter binding path resolved to an empty argument array instead of the intended `status --porcelain` values.
- The helper therefore ran `git -C <repo>` with no Git subcommand.
- Git printed its help page to stdout, and `Get-ChangedFiles` treated each help line as if it were a changed file path.

## Bad Path
- Intended command: `git -C <repo> status --porcelain`
- Actual broken command path: `git -C <repo>`
- Broken parser input: Git usage/help text
- Result in the May 16 report: Git help lines appeared under both `Changed Files` and `Unsafe Files`.

## Correct Source Of Changed Files
- The canonical changed-file source is `git status --porcelain`.
- Only valid porcelain records are accepted as paths.
- Renames keep the destination path after `old -> new`.

## Fix
- Renamed the Git helper parameter from `$Args` to `$GitArgs`.
- `Get-ChangedFiles` now:
  - checks for Git timeout and non-zero exit status before parsing
  - accepts only lines that match porcelain output shape
  - records malformed output under change-detection errors instead of treating it as a path
- `final_report.md` generation now includes:
  - `Allowed Files Check`
  - `Change Detection Errors`
- Future reports can now say whether detected changes stayed within the task allowlist, failed the allowlist, or could not be determined because change detection itself failed.

## Existing May 16 Report
- The already-written report at `auto_runs\20260516_144735_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run\final_report.md` remains a historical bad artifact from before this fix.
- Independent inspection of the live diff shows only:
  - `START_HERE.md`
  - `WORKSTATION_MANUAL.md`
- Both are inside the task allowlist.

## Validation Performed
- PowerShell parse check for `scripts/ws_agent_run.ps1`: passed.
- Direct reproduction of the old `$Args` failure: passed, confirming the empty-argument root cause.
- Live `git status --porcelain` inspection now returns actual paths rather than Git help text:
  - `START_HERE.md`
  - `WORKSTATION_MANUAL.md`
  - `scripts/ws_agent_run.ps1`
  - `AGENT_RUN_CHANGED_FILE_REPORT_FIX.md`
- Safe dry-run only for `ws agent-run`: passed.
  - Run folder: `auto_runs\20260516_150312_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`
  - Status: `PLAN_ONLY`
  - The dry-run report includes `Allowed Files Check` and `Change Detection Errors` sections.

## Remaining Note
- Dry-run validates terminal behavior and report creation without running Codex.
- A future bounded real apply is still required to produce a fresh post-fix real-run report.
