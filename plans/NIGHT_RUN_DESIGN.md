# Design: Night-Run Autonomous Workflow

This document outlines the design for a future `ws night-run` command, enabling bounded autonomous execution of multiple tasks during overnight or idle periods.

## Goal
To allow the workstation to process a queue of engineering tasks independently while maintaining strict safety boundaries and resource constraints.

## Command Interface
```bash
ws night-run <project_key> <task_queue_file> [flags]
```

### Core Parameters
- `--max-tasks <n>`: Stop after successfully completing or failing N tasks (default: 5).
- `--max-total-files <n>`: Stop if the total number of modified files across all tasks exceeds N (default: 20).
- `--max-attempts-per-task <n>`: Maximum retries for a single task if tests fail (default: 3).
- `--mode <plan|apply>`: Default is `plan` (autonomous planning only). `apply` mode requires a `--i-am-safe` acknowledgement flag.

## Stop Conditions (Immediate Termination)
The night-run orchestrator will monitor and terminate immediately if:
1.  **Consecutive Failures**: 3 consecutive tasks fail their test suites.
2.  **Redaction Failure**: Any generated patch or packet fails the `ws redact` check.
3.  **Resource Limits**:
    - Disk space on `$WS_HOME` or project drive falls below 5GB.
    - GPU Temperature exceeds 85°C.
    - System RAM usage exceeds 90% for more than 5 minutes.
4.  **Security**: Any `.env` or credential file is detected in the working diff.

## Safety & Security Boundaries
- **No Secrets**: The `ws redact` script must pass on every patch before it is applied.
- **No Deployment**: Commands such as `npm publish`, `git push`, `docker push`, or any cloud deployment CLI are strictly forbidden in night-run mode.
- **Restricted Network**: Outbound network calls are restricted to Ollama API and registered Frontier provider endpoints (Codex/Gemini). No general web scraping or unverified API calls.
- **Read-Only Fallback**: If a task is ambiguous (determined by local Hermes), it is marked as `blocked` and skipped, rather than attempting speculative fixes.

## Reporting
- A single `NIGHT_RUN_REPORT_<timestamp>.md` is generated under `D:\_ai_brain\reports`.
- Each task run is archived in a sub-folder under `D:\_ai_brain\runs\night_runs`.
- The report includes a high-level summary: `Tasks Processed`, `Passed`, `Failed`, `Blocked`, `Total Files Modified`.

## Workflow Logic
1.  **Initialize**: Check disk space, GPU temp, and registry health.
2.  **Pick Task**: Use `ws task-next` to identify the first candidate from the queue.
3.  **Plan**: Run `ws build --plan-only`.
4.  **Apply (if enabled)**:
    - Run `ws redact` on the proposed plan.
    - Create a git branch.
    - Apply patch.
    - Run tests.
    - If tests fail, retry up to `--max-attempts-per-task`.
5.  **Log & Repeat**: Update the report and move to the next task if limits have not been reached.
6.  **Finalize**: Unload all models from VRAM and write the final summary.

## Future Phases
- **Unattended Apply**: Integration with a local "Canary" service to verify system stability between tasks.
- **Self-Healing**: Ability for the night-run to attempt a `ws cleanup-apply` if disk space is low (limited to high-confidence archives).
