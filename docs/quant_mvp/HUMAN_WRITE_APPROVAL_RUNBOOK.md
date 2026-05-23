# Human Write Approval Runbook (Q46)

## 1. Purpose
This runbook describes the procedure for authorizing a future "guarded write" operation in the Quant research lane. Currently, write mode is designed but blocked. This process ensures that when write mode is eventually enabled, every mutation is human-reviewed and signed.

## 2. How Future Write Approval Works
1. **Operator performs a dry-run:** The operator runs the dry-run version of a command (e.g., `ws quant idea-intake-dry-run`).
2. **Review output:** The operator reviews the dry-run output and artifacts.
3. **author Approval Form:** If satisfied, the operator authors a Human Approval Form (HAF) in `scratch/quant_approvals/`.
4. **Sign HAF:** The operator includes their name, the input file hash, and explicit confirmation.
5. **Execute with Approval:** The operator eventually runs the write command, passing the path to the approval file.
6. **Validator Check:** The system validates the HAF against the schema, verifies hashes, checks for expiry, and ensures all safety flags are `false`.

## 3. Why Approval is Per-Run
To prevent "replay attacks" or accidental reuse of approvals, every approval is tied to:
- A specific command string.
- A specific input file hash.
- A short expiry window.

## 4. Why Approval is NOT Strategy Approval
Approving a "write" operation only authorizes the workstation to create a local JSON/Markdown artifact. It does NOT authorize:
- The validity of the underlying trading strategy.
- The promotion of the candidate to a real backtest.
- Any form of paper or live trading.

## 5. Required Fields in HAF
- `approval_id`: Deterministic unique identifier.
- `target_command`: The exact command to be run.
- `source_input_hash`: SHA256 of the input file.
- `operator_confirmation`: Explicit statement of review.
- `expires_at`: ISO timestamp (usually 1 hour from creation).
- `forbidden_actions`: Explicit list of blocked actions (e.g., `run_backtest`).

## 6. Current Status: Write Mode Blocked
**As of milestone Q45-Q47, all write-mode commands remain strictly blocked.** 
Even if a valid `approved_for_single_local_write` HAF is provided, the `human_write_approval.py` validator will return a `BLOCKED` status because `future_write_enabled` is set to `False`.

## 7. Future Enablement Requirements
Enabling write mode will require:
1. Updating `human_write_approval.py` to allow `future_write_enabled=True`.
2. Registering the first `GUARDED_WRITE` command in `ws_command_safety.yaml`.
3. Implementing the actual write logic in the underlying CLI (e.g., `idea_cli.py`).
