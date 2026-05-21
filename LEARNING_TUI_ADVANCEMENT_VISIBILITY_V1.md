# Learning TUI Advancement Plan Visibility v1

## Purpose
This document (Phase 10B) defines the implementation of read-only advancement readiness visibility within the Learning Cockpit / TUI. This ensures that operators can evaluate the current learner's readiness for lifecycle transitions based on confirmed evidence, while strictly maintaining the manual advancement boundary.

## TUI Displays
The Learning Cockpit now includes an **ADVANCEMENT READINESS STATUS** section that displays:
- **Status**: The current readiness classification (e.g., `READY_FOR_HUMAN_REVIEW`).
- **Score**: A numeric score (0-100) reflecting evidence strength.
- **Future State**: The advisory next state (e.g., `MANUAL_REVIEW_REQUIRED`).
- **Risk Level**: Defaults to `HIGH` for all advancement assessments.
- **Evidence**: The overall quality of the data supporting the status.
- **Eligible 10B**: Whether the assessment meets criteria for a future apply phase (currently always `False`).
- **Blockers/Warnings**: Summaries of issues preventing or warning against advancement.
- **Human Checks**: Specific verification steps required by the operator.

## Readiness Behavior
For `READY_FOR_HUMAN_REVIEW`, the TUI explicitly displays:
`Ready for human review does not mean automatic advancement.`

## Hard Safety Guards
The TUI's internal command runner has been extended to block all advancement-related mutation flags:
- `--advance`
- `--apply`
- `--confirm-advancement`

The TUI is restricted to calling `learning_advancement_readiness_planner.py` only with the `--dry-run --json` flags.

## Live Status Snapshot (`fine-tuning-small-open-source-models`)
As of Phase 10A/B:
- **Current State**: `LOCAL_CHECKLIST_READY`
- **Readiness Status**: `READY_FOR_HUMAN_REVIEW`
- **Readiness Score**: 50/100
- **Proposed Future State**: `MANUAL_REVIEW_REQUIRED` (Advisory)
- **State.json Mtime**: `2026-05-21 12:43 PM` (Verified unchanged).

## Validation Results
- **Advancement Helper**: PASS (Verified to call dry-run JSON only).
- **Hard Guard**: PASS (Verified to block mutation flags).
- **UI Integration**: PASS (Section added to cockpit display).
- **No Mutation**: PASS (Verified `state.json` mtime remained unchanged during implementation).

## Known Limitations
- Advancement apply remains manual (operator CLI command or manual JSON edit).
- Readiness score is a basic heuristic.
- The TUI does not currently display the specific audit trail entries supporting the score.

## Next Recommended Task
- **Phase 10C**: Stabilize advancement readiness logic and transition to a "Ready for Apply" state in future versions.
