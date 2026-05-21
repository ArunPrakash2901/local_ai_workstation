# Learning Dry-Run Action Pack v1

## Overview
The Learning Dry-Run Action Pack v1 enables the Learning Application to generate safe, preview-only learning actions. These actions are designed to be inspectable and non-destructive, adhering to the "Dry-run first" safety mandate of the Local AI Workstation.

## Supported Actions
1. **CREATE_STUDY_TASK_DRY_RUN**: Proposes a study task from the current learning context.
2. **SUMMARIZE_SESSION_DRY_RUN**: Proposes a session summary artifact for the last completed session.
3. **PROPOSE_NEXT_LESSON_DRY_RUN**: Suggests the next learning step based on current progress.
4. **MARK_REVIEW_NEEDED_DRY_RUN**: Proposes that a topic should be flagged for review.
5. **ASSESS_ADVANCEMENT_READINESS_DRY_RUN**: Generates an evidence checklist for advancement readiness.
6. **DETECT_STALE_LEARNING_ARTIFACTS_DRY_RUN**: Identifies stale learning artifacts (older than 7 days).

## Commands
### Generate Action Pack (Dry-Run)
**WSL / Bash:**
```bash
ws learning-action-pack <stronghold_id> --dry-run
```

**Windows / PowerShell:**
```powershell
.\scripts\ws.ps1 learning-action-pack <stronghold_id> --dry-run
```

### JSON Output (for TUI/Tooling)
**WSL / Bash:**
```bash
ws learning-action-pack <stronghold_id> --dry-run --json
```

**Windows / PowerShell:**
```powershell
.\scripts\ws.ps1 learning-action-pack <stronghold_id> --dry-run --json
```

## Windows / PowerShell Invocation Notes
A native PowerShell wrapper `scripts/ws.ps1` is provided to bridge the gap between Windows and the WSL-based `ws` command. It handles path conversion and ensures the correct environment is set up before delegating to the bash-based dispatcher.

## TUI Integration
The Learning Cockpit displays the Action Pack v1 section when a learning stronghold is active. It shows:
- The count of proposed dry-run actions.
- The title and status (e.g., `[DRY_RUN_ONLY]`) of each action.
- Any associated warnings.

The TUI integration is read-only and relies on the `--json` output of the action pack script.

## Safety Assumptions
- **No Mutation**: The action pack logic is read-only and does not mutate `state.json` or any project files.
- **Dry-Run Mandatory**: The command refuses to run without the `--dry-run` flag.
- **Explicit Confirmation Required**: These actions are for preview only. A future confirmation layer is required to execute the real counterparts.

## Validation Results
- **Refusal Test**: Verified that calling the command without `--dry-run` fails safely.
- **Action Generation**: Verified all 6 dry-run action types are generated with `status="DRY_RUN_ONLY"` and `requires_confirmation=true`.
- **JSON Purity**: Verified that `--json` returns valid JSON without mixed human-readable text.
- **Path Robustness**: Verified that `ws` dispatcher and `ws_learning_action_pack.sh` correctly resolve their location even when called via different shell environments (WSL, Git Bash, PowerShell).
- **Line Endings**: Verified that bash scripts use LF line endings for compatibility.

## Known Limitations
- **Read-Only**: No apply/confirmation layer exists yet. Proposed effects are descriptive only.
- **Dry-Run Mandatory**: The implementation strictly refuses non-dry-run calls to prevent accidental state mutation until a confirmation layer is implemented.

## Next Recommended Step
Implement the **Learning Action Confirmation UI** to allow operators to selectively "apply" the proposed actions from the action pack.
