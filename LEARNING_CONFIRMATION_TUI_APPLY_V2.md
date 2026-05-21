# Guarded Learning Confirmation TUI Apply v2

## Purpose
The Guarded Learning Confirmation TUI Apply v2 enables operators to apply confirmed learning actions directly from the Learning Cockpit (plain mode) after reviewing a dry-run preview. This implementation follows a strict safety model to ensure all writes are auditable, intentional, and non-destructive to core learning state.

## Workflow
1. **Action Selection**: Operator enters the index of a proposed action in the Action Pack Previewer.
2. **Mandatory Preview**: The TUI automatically runs and displays a `learning-confirm --dry-run` result.
3. **Apply Option**: If the preview is successful and the action is not a duplicate, an `[a] Apply` option is presented.
4. **Typed Confirmation**: Operator must type exactly `APPLY <ACTION_ID>` (e.g., `APPLY LT-20260521-01`).
5. **Guarded Execution**: The TUI calls `learning_confirmation_core.py --confirm` using a subprocess list and strict character guards.
6. **Post-Write Verification**: The TUI verifies that exactly one ledger entry was appended and one artifact was created, while ensuring `state.json` remains untouched.

## Safety Model
- **Two-Step Confirmation**: Prevents accidental triggers via single keypress or mis-typed "yes".
- **Duplicate Protection**: Refuses to apply an action if it already appears as `CONFIRMED_APPLIED` in the stronghold ledger.
- **Hard Command Guards**:
    - Reject shell metacharacters: `; & | > < ` $ ( ) [ ] { } * ? ~` in all arguments.
    - Mode enforcement: Preview mode explicitly blocks `--confirm`; Apply mode explicitly blocks `--dry-run`.
- **Non-Mutation of Core State**: Verification logic ensures `state.json` modification time does not change.
- **Audit Trail**: Every TUI apply results in a permanent entry in `learning_confirmations.jsonl` and a markdown file in `confirmed_actions/`.

## Internal Command
The TUI builds and executes the following command list:
```python
[sys.executable, "scripts/learning_confirmation_core.py", stronghold_id, "--action-id", action_id, "--confirm", "--json"]
```

## Validation Results
- **Safety Guards**: PASS (Injections and mode mismatches blocked).
- **Typed Phrase Enforcement**: PASS (Rejected mismatched phrases).
- **Duplicate Blocking**: PASS (Identified and blocked already-confirmed actions).
- **Durable Write**: PASS (Verified ledger append and artifact creation).
- **Non-Mutation**: PASS (Verified `state.json` was not touched).

## Known Limitations
- **v2 Scope**: Focuses on the "Apply" event only. Automatic advancement or real state mutation (updating `state.json`) is still deferred to future phases.
- **Plain Mode Only**: This interactive flow is currently implemented for the line-based plain TUI.

## Next Recommended Task
Implement **Learning State Synchronization (Phase 7)**, which would allow the Learning Stronghold to selectively ingest confirmed actions from the ledger to update `state.json` and advance the learner stage in a controlled manner.
