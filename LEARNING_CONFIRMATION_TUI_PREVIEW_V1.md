# Learning Confirmation TUI Preview Interactivity v1

## Purpose
The Learning Confirmation TUI Preview Interactivity v1 enables the Learning Cockpit to trigger and display guarded dry-run confirmation previews for selected actions. This allows operators to inspect the proposed effects and audit records of an action directly within the TUI before manually applying it via the CLI.

## TUI Enhancements
### 1. Action Pack Previewer Menu
- A new menu accessible from the LEARNING screen by pressing `[p]`.
- Displays all currently proposed actions with index numbers (1, 2, 3...).
- Allows the operator to select an action by number to trigger a preview.

### 2. Guarded Preview Display
- Displays a detailed breakdown of the selected action's preview result.
- Shows:
    - Action ID and Types (Original vs. Confirmed)
    - Title and Rationale
    - Proposed Effect vs. Confirmed Effect
    - Safety Class and Status Preview
    - Target Ledger and Artifact Paths
    - Warnings (if any)
- **Safety Note**: Includes a mandatory notice that the TUI preview is read-only.

## Safety Model
- **Hard Guard**: The TUI includes a programmatic guard that explicitly blocks any command string containing `--confirm` before execution.
- **Dry-Run Only**: The TUI only triggers the `learning-confirm --dry-run --json` command.
- **No Durable Writes**: The preview process does not append to the ledger or create markdown artifacts.
- **Subprocess Isolation**: Commands are run with a 10-second timeout to prevent UI hangs.
- **Read-Only**: No learning state mutation or automatic advancement occurs.

## Internal Command Construction
The TUI builds the following command list (no `shell=True`) to run the preview:
```python
[sys.executable, "scripts/learning_confirmation_core.py", stronghold_id, "--action-id", action_id, "--dry-run", "--json"]
```

## Validation Results
- **Safety Guard**: PASS (Attempted injections of `--confirm` in Action ID or Stronghold ID are blocked).
- **Preview Execution**: PASS (Successfully retrieved and displayed preview JSON from the core script).
- **No State Mutation**: Verified (No files were written during TUI preview testing).

## Known Limitations
- **CLI Still Required for Apply**: Operators must manually run the `--confirm` version of the command in their terminal to apply changes.
- **Plain Mode Only**: Interactivity is implemented for the stdlib-only `plain` mode; Textual mode remains read-only for now.

## Next Recommended Task
Implement **Guarded TUI Confirmation Apply** (v2), which would allow the operator to apply a confirmation directly from the TUI after reviewing a preview, using a two-step "Are you sure?" confirmation pattern.
