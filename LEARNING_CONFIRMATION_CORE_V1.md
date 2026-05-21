# Learning Confirmation Core v1

## Purpose
The Learning Confirmation Core v1 provides a guarded confirmation layer for the Learning Stronghold. It allows human operators to transition proposed dry-run actions into auditable confirmed records, ensuring that learning progress is intentional and documented.

## Safety Model
- **Guarded Confirmation**: Real durable writes require the `--confirm` flag.
- **Dry-Run Preview**: The `--dry-run` flag allows previewing the confirmation effect and the proposed audit record without making any changes.
- **Audit Ledger**: All confirmed actions are appended to a JSONL ledger within the stronghold.
- **Artifact Generation**: Confirmation creates a human-readable markdown artifact for each action.
- **Isolation**: Confirmation does NOT mutate core learning state (like `state.json`) or advance the learner automatically.
- **Validation**: Confirmation fails if the action ID is unknown, if the action is not in a confirmable state, or if mode flags are ambiguous.

## Commands
### Preview Confirmation
**WSL / Bash:**
```bash
ws learning-confirm <stronghold_id> --action-id <ACTION_ID> --dry-run
```

**Windows / PowerShell:**
```powershell
.\scripts\ws.ps1 learning-confirm <stronghold_id> --action-id <ACTION_ID> --dry-run
```

### Apply Confirmation
**WSL / Bash:**
```bash
ws learning-confirm <stronghold_id> --action-id <ACTION_ID> --confirm
```

**Windows / PowerShell:**
```powershell
.\scripts\ws.ps1 learning-confirm <stronghold_id> --action-id <ACTION_ID> --confirm
```

## Durable Output Paths
- **Audit Ledger**: `strongholds/learning/<stronghold_id>/learning_confirmations.jsonl`
- **Confirmed Artifacts**: `strongholds/learning/<stronghold_id>/confirmed_actions/YYYYMMDDTHHMMSSZ_<action_id>_<action_type>.md`

## Action Type Conversion
| Dry-Run Type | Confirmed Type |
|---|---|
| CREATE_STUDY_TASK_DRY_RUN | CREATE_STUDY_TASK_CONFIRMED |
| SUMMARIZE_SESSION_DRY_RUN | SUMMARIZE_SESSION_CONFIRMED |
| PROPOSE_NEXT_LESSON_DRY_RUN | PROPOSE_NEXT_LESSON_CONFIRMED |
| MARK_REVIEW_NEEDED_DRY_RUN | MARK_REVIEW_NEEDED_CONFIRMED |
| ASSESS_ADVANCEMENT_READINESS_DRY_RUN | ASSESS_ADVANCEMENT_READINESS_CONFIRMED |
| DETECT_STALE_LEARNING_ARTIFACTS_DRY_RUN | DETECT_STALE_LEARNING_ARTIFACTS_CONFIRMED |

## Validation Results
- **Dry-Run Preview**: PASS
- **Invalid Action ID**: PASS
- **Missing Mode Refusal**: PASS
- **Confirmation Apply**: PASS (Verified ledger append and artifact creation)

## Known Limitations
- **No Automatic Advancement**: Confirmed actions do not automatically update `state.json` or trigger next steps.
- **Manual Command Entry**: Confirmation must be performed via the CLI; no TUI buttons exist yet.
- **v1 Scope**: Focuses on auditability and record-keeping rather than execution.

## Next Recommended Task
Implement **Learning Confirmation TUI Integration** to allow operators to select and confirm actions directly from the Learning Cockpit using the confirmation core.
