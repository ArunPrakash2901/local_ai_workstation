# Learning Review Packet Checklist State Layer v1

## Purpose
This document (Phase 12A) defines the local-only checklist state layer for tracking human review progress against an advancement review packet. This layer provides a structured way for operators to verify required human checks before manual advancement, without mutating the core `state.json` or the archival review packet markdown files.

## Phase Boundary
- **Input**: An existing advancement review packet (`.md`).
- **Output**: A local checklist state JSON file and an append-only audit entry.
- **Interactivity**: Read-only display and initialization (Phase 12A). Item toggling and completion are reserved for Phase 12B.
- **Safety**: Strictly non-mutating for core state and packets.

## Command Shapes
The primary interface is through the `ws` unified command.

### Dry-Run Initialization Preview
```bash
ws learning-review-checklist <stronghold_id> --packet-id <PACKET_ID> --dry-run-init
ws learning-review-checklist <stronghold_id> --packet-id <PACKET_ID> --dry-run-init --json
```

### Initialize Checklist State
```bash
ws learning-review-checklist <stronghold_id> --packet-id <PACKET_ID> --init-checklist
ws learning-review-checklist <stronghold_id> --packet-id <PACKET_ID> --init-checklist --json
```

### Show Checklist State
```bash
ws learning-review-checklist <stronghold_id> --packet-id <PACKET_ID> --show
ws learning-review-checklist <stronghold_id> --packet-id <PACKET_ID> --show --json
```

## Checklist State Location
Checklist state is stored in a dedicated folder within the stronghold:
`strongholds/learning/<stronghold_id>/review_checklists/`

- **Checklist JSON**: `<packet_id>_checklist.json`
- **Audit Ledger**: `checklist_audit.jsonl`

## Safety Boundaries
- Review packet markdown files are **NOT** modified.
- `state.json` is **NOT** modified.
- `current_state` and `next_learning_task` are **NOT** modified.
- Advancement remains **MANUAL**.
- Audit records are **APPEND-ONLY**.

## Checklist Item Extraction
The system attempts to extract required human checks from the `## 6. Required Human Checks` section of the review packet. If no items are found (e.g., malformed packet), it falls back to conservative default items:
1. Verify the learner has completed the current task.
2. Verify the [next_task] task is actually done.
3. Verify outputs or artifacts exist.
4. Verify no unresolved blockers remain.
5. Decide whether current_state should remain [current_state].
6. Decide whether a future advancement phase is appropriate.

## Validation Results
- **Refusal (No Mode)**: PASS
- **Refusal (Multiple Modes)**: PASS
- **Dry-Run (No Writes)**: PASS
- **Init (Creation/Audit)**: PASS
- **Init (Duplicate Refusal)**: PASS
- **Show (Read-Only)**: PASS
- **JSON Mode (Pure JSON)**: PASS
- **Extraction (Regex/Fallback)**: PASS
- **Non-Mutation (State/Packet)**: PASS

## Live Stronghold Dry-Run
Performed against `fine-tuning-small-open-source-models` with packet `ADV-PACKET-20260521T143413Z`:
- **Result**: Success (Verified correct item extraction and path resolution).

## Remaining Limitations
- Checklist item toggling is not yet implemented.
- TUI interactivity is not yet implemented.
- Automatic advancement is strictly forbidden.

## Next Recommended Task
- **Phase 12B**: Implement checklist item toggle/completion logic (local state only).
- **Phase 12C**: Integrate checklist progress into the TUI.
