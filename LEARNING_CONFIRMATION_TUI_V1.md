# Learning Confirmation TUI Integration v1

## Purpose
The Learning Confirmation TUI Integration v1 enhances the Learning Cockpit by providing visibility into confirmable actions and the history of applied confirmations. It bridges the gap between the Action Pack and the Confirmation Core by displaying the exact CLI commands needed to transition actions from dry-run to confirmed status.

## TUI Enhancements
The Learning Cockpit now includes several new sections and details when a learning stronghold is selected:

### 1. Detailed Action Pack Display
The "ACTION PACK V1 (DRY-RUN)" section now shows:
- **Title and Status**: e.g., `[DRY_RUN_ONLY]`
- **Action ID and Type**: e.g., `LT-20260520-01 (CREATE_STUDY_TASK_DRY_RUN)`
- **Safety Class**: e.g., `DRY_RUN_ONLY` or `PURE_READ`
- **Warnings**: Integrated warning messages if any.

### 2. Guarded Confirmation Commands
For each confirmable action, the TUI displays the exact commands to be run in the CLI:
- **Preview Command**: `ws learning-confirm <id> --action-id <aid> --dry-run`
- **Apply Command**: `ws learning-confirm <id> --action-id <aid> --confirm`
- **Note**: A clear label indicates that "Confirmation is CLI-only in v1."

### 3. Recent Confirmations (Ledger v1)
A new section that displays the last 5 entries from the `learning_confirmations.jsonl` ledger.
- Shows timestamp, confirmed action type, and confirmation ID.

### 4. Confirmed Artifacts
A list of the 5 most recent markdown artifacts generated under the `confirmed_actions/` directory.

## Safety Model
- **Read-Only Integration**: The TUI only reads data from the action pack script and the filesystem (ledger/artifacts).
- **No State Mutation**: The TUI does not write to `state.json`, `learning_confirmations.jsonl`, or any other durable files.
- **CLI-Only Confirmation**: The actual application of a confirmation remains restricted to the guarded CLI commands displayed in the TUI.
- **Graceful Degradation**: If the ledger is missing or the action pack command fails, the TUI shows informational warnings instead of crashing.

## Commands Displayed
**Preview Confirmation (WSL/Bash):**
```bash
ws learning-confirm <stronghold_id> --action-id <ACTION_ID> --dry-run
```

**Apply Confirmation (WSL/Bash):**
```bash
ws learning-confirm <stronghold_id> --action-id <ACTION_ID> --confirm
```

## Validation Results
- **Ledger Read**: PASS (Successfully parsed sample JSONL ledger)
- **Artifact Visibility**: PASS (Successfully listed confirmed action markdown files)
- **Action Pack Integration**: PASS (Successfully consumed JSON output from `learning_action_pack.py`)
- **TUI Rendering**: Verified via code inspection and validation helper.

## Known Limitations
- **No Direct Apply**: Operators must manually copy and run confirmation commands in their terminal.
- **Limited History**: Only shows the last 5-10 entries to maintain dashboard readability.

## Next Recommended Task
Implement **Learning Action Confirmation TUI Interactivity** to allow operators to trigger the preview command directly from the TUI with a single keypress, maintaining the `--confirm` step as a CLI-only guarded action for now.
