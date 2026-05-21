# Learning State Synchronization Planner v1

## Purpose
The Learning State Synchronization Planner v1 is a dry-run only layer that bridges the gap between confirmed learning actions (in the ledger) and the durable `state.json`. It identifies which actions are eligible to affect the workstation's state and proposes auditable changes without performing any actual writes.

## Phase Boundary
- **Phase 6 completed**: TUI can apply confirmed records to the ledger.
- **Phase 7A (Current)**: Planner generates dry-run-only state synchronization plans.
- **Phase 7B (Future)**: State synchronization apply (updating `state.json`).

## Command Shape
**WSL / Bash:**
```bash
ws learning-state-sync-plan <stronghold_id> --dry-run
ws learning-state-sync-plan <stronghold_id> --dry-run --json
```

**Windows / PowerShell:**
```powershell
.\scripts\ws.ps1 learning-state-sync-plan <stronghold_id> --dry-run
.\scripts\ws.ps1 learning-state-sync-plan <stronghold_id> --dry-run --json
```

## State Sync Plan Structure
The planner outputs a JSON object containing:
- `eligible_confirmations`: Actions with `CONFIRMED_APPLIED` status and valid evidence.
- `proposed_state_changes`: Patch-like descriptions of changes (e.g., `state.next_learning_task`).
- `blockers`: Issues preventing state sync (e.g., missing artifacts, malformed ledger).
- `can_apply_now`: Always `false` in v1.

## Confirmation Classification
- **Eligible**: `CREATE_STUDY_TASK`, `SUMMARIZE_SESSION`, `PROPOSE_NEXT_LESSON`, `MARK_REVIEW_NEEDED`, `ASSESS_ADVANCEMENT_READINESS`.
- **Informational**: `DETECT_STALE_LEARNING_ARTIFACTS`.
- **Blocked**: Actions missing artifact evidence, duplicate action IDs, or unknown types.

## Safety Model
- **No Mutation**: The planner strictly refuses to modify `state.json`.
- **Evidence Verification**: Proposes changes only if the referenced artifact exists and is within the stronghold.
- **Duplicate Protection**: Detects and warns about duplicate action IDs in the ledger.
- **Dry-Run Mandatory**: The command fails safely if called without `--dry-run`.

## Validation Results
- **Refusal Test**: PASS (Fails without --dry-run)
- **JSON Purity**: PASS (Returns valid, unadulterated JSON)
- **Non-Mutation**: PASS (Verified `state.json` mtime remains unchanged)
- **Isolation**: PASS (All tests use `_test_isolation_fixture`)

## Known Limitations
- **Read-Only**: Proposes changes but cannot apply them.
- **Manual Sync**: Operators must still manually update `state.json` if they wish to advance.
- **TUI Integration**: Minimal read-only display (Phase 7A focus is the CLI planner).

## Readiness for Phase 7B
The pipeline is **READY** for Phase 7B (State Sync Apply) once human review of the planner's proposed logic for each confirmation type is complete.
