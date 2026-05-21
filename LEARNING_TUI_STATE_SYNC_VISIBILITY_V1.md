# Learning TUI State Sync Visibility v1

## Purpose
This document defines the Learning TUI State Sync Visibility (Phase 8). This phase adds read-only visibility into the state synchronization status, audit records, and backup history within the Learning Cockpit.

## TUI Displays
The Learning Cockpit now includes a **STATE SYNC STATUS** section that displays:
- **Latest Sync ID**: The unique identifier for the last synchronization event.
- **Timestamp UTC**: When the sync occurred.
- **Status**: The outcome of the sync (e.g., `STATE_SYNC_APPLIED`).
- **Changes Summary**: Number of applied, skipped, and blocked changes.
- **Backup**: The filename of the `state.json` backup created during the sync.
- **Total Backups**: The total number of backups stored in `state_backups/`.

## Latest Live Sync Summary
As of Phase 7D, the live stronghold `fine-tuning-small-open-source-models` has the following sync status:
- **Sync ID**: `SYNC-20260521T124320Z`
- **Applied Changes**: 1 (`state.learning_session_status`)
- **Blocked Changes**: 0
- **Warnings**: 1 (State mismatch for redundant update)

## Manual Boundaries
The TUI explicitly warns the operator about remaining manual tasks:
- **Advancement**: `current_state` mutation to `READY_FOR_ADVANCEMENT` remains a manual operator task (HIGH RISK).
- **Pointer Updates**: `next_learning_task` updates are currently blocked (MEDIUM RISK).

## Safety Guards
- **Read-Only**: The TUI remains strictly read-only for state synchronization. No "Apply Sync" button or command is exposed.
- **Hard Guard**: Any internal helper designed for state sync is guarded against write-mode flags (`--confirm-sync`, `--repair-ledger`, etc.).
- **No Mutation**: Verified that TUI data collection does not modify `state.json` or append to audit records.

## Validation Results
- **Audit Reading**: PASS (Verified that the helper correctly identifies and parses the latest JSONL record).
- **Backup Detection**: PASS (Verified count and latest file detection).
- **UI Integration**: PASS (Section is integrated into `active_stronghold_lines`).
- **Live Safety**: PASS (Verified no writes occurred to the live stronghold during TUI development).

## Known Limitations
- TUI does not currently show the specific field-level diffs from the audit record (summary counts only).
- TUI does not trigger real-time dry-runs; it relies on the persistent audit ledger.

## Next Recommended Task
- **Phase 9**: Implement TUI-driven controlled pointer updates for `next_learning_task`.
