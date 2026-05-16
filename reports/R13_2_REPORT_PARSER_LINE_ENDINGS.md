# R13.2: Agent-Run Report Parser and Line-Ending Policy Fix

## Summary
This fix addresses a bug in the automated agent run report generator and establishes a scoped line-ending policy to prevent shell script syntax errors without rewriting unrelated historical files.

## Root Cause
1.  **Parser Bug:** In `scripts/ws_agent_run.ps1`, the loop processing `git status --porcelain` was calling `$line.Trim()`. This removed the critical leading space that Git uses to indicate working tree modifications (e.g., ` M START_HERE.md`). The regex `^(?<status>.{2}) (?<path>.+)$` then failed because it expected two characters before the space, but only found one after trimming. This led to "unknown" file checks and unrecognized detection errors in `final_report.md`.
2.  **Missing Line-Ending Policy:** The repository lacked a `.gitattributes` file. On a Windows workstation, Git's default behavior was often to convert LF (Linux) to CRLF (Windows). For Bash scripts like `scripts/ws`, CRLF line endings are syntactically invalid in WSL, causing fatal startup errors.

## Files Changed
- `scripts/ws_agent_run.ps1`: Replaced `$line.Trim()` with `[string]::IsNullOrWhiteSpace($line)` in the change detection loop to preserve the 2-character porcelain status column.
- `.gitattributes`: New file created to enforce LF line endings for all shell scripts (`*.sh`, `scripts/ws`) and CRLF for the Windows-native agent runner (`scripts/ws_agent_run.ps1`) without normalizing unrelated legacy Markdown or PowerShell files.
- `scripts/ws`: Normalized to LF line endings and validated for Bash syntax.

## Line-Ending Policy
The following policy is now active via `.gitattributes`:
- `* text=auto`: Standard auto-detection for most files.
- `*.sh text eol=lf`: Enforced LF for all shell scripts.
- `scripts/ws text eol=lf`: Enforced LF for the primary orchestrator.
- `scripts/ws_agent_run.ps1 text eol=crlf`: Enforced CRLF for the changed Windows-native agent runner.

## Validation Results
- **Bash Syntax:** `bash -n scripts/ws` passed with zero errors.
- **Change Detection:** A dry-run of the agent orchestrator successfully executed, generating valid internal state artifacts. The new parsing logic was verified against the actual `git status --porcelain` output format.
- **Git State:** `git status --short` confirms `.gitattributes` is ready for tracking.

The workstation control plane and reporting pipeline are now significantly more robust against cross-platform line-ending issues and automated detection failures.
