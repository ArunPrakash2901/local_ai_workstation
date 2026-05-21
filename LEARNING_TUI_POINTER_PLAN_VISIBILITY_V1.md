# Learning TUI Pointer Plan Visibility v1

## Purpose
This document (Phase 9B-Prep) defines the implementation of read-only pointer plan visibility within the Learning Cockpit / TUI. This ensures that operators can see proposed updates to the `next_learning_task` based on confirmed actions, while strictly maintaining the "manual mutation" boundary for this phase.

## TUI Displays
The Learning Cockpit now includes a **POINTER PLAN STATUS** section that displays:
- **Current Task**: The value of `next_learning_task` currently in `state.json`.
- **Candidate Task**: The proposed new task extracted by the pointer update planner.
- **Status**: The classification of the candidate (e.g., `eligible`, `already_synchronized`, `conflict`).
- **Evidence**: The quality of the evidence supporting the candidate (`strong`, `partial`).
- **Eligible 9B**: Whether the candidate meets the safety criteria for automated synchronization in the next phase.
- **Source**: The action type and confirmation ID that provided the candidate.

## Already Synchronized Behavior
If the strongest candidate matches the current task, the TUI displays:
`Pointer already synchronized; no pointer apply is needed.`

## Hard Safety Guards
The TUI's internal command runner `run_learning_confirmation_command` has been extended to block all pointer-related mutation flags:
- `--apply`
- `--confirm-pointer`
- `--confirm-sync`
- `--repair-ledger`

The TUI is restricted to calling `learning_pointer_update_planner.py` only with the `--dry-run --json` flags.

## Live Status Snapshot (`fine-tuning-small-open-source-models`)
As of Phase 9A.5/9B:
- **Current Next Task**: `**Intern**: Format dataset as JSONL.`
- **Candidate Task**: `**Intern**: Format dataset as JSONL.`
- **Candidate Status**: `already_synchronized`
- **State.json Mtime**: `2026-05-21 12:43 PM` (Verified unchanged since Phase 7D sync).

## Validation Results
- **Pointer Helper**: PASS (Verified to call dry-run JSON only).
- **Hard Guard**: PASS (Verified to block all mutation flags).
- **UI Integration**: PASS (Section added to `active_stronghold_lines`).
- **No Mutation**: PASS (Verified `state.json` mtime remained unchanged during implementation).

## Known Limitations
- Pointer apply remains manual (CLI-only or manual JSON edit).
- Conflict resolution requires manual intervention if multiple high-priority tasks are found.

## Next Recommended Task
- **Phase 9B**: Implement supervised pointer update apply for `next_learning_task`.
