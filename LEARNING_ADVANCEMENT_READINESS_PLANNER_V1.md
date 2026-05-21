# Learning Advancement Readiness Planner v1

## Purpose
This document defines the Learning Advancement Readiness Planner (Phase 10A). This planner evaluates whether a learner is ready to transition to a future state by inspecting confirmed evidence, synchronization status, and audit records.

## Phase Boundary
Phase 10A is strictly **planning-only**. No state mutations are allowed. Implementation of any advancement apply layer is reserved for future phases.

## Command Shape
The primary interface is through the `ws` unified command.

### Dry-Run Plan
```bash
ws learning-advancement-plan <stronghold_id> --dry-run
ws learning-advancement-plan <stronghold_id> --dry-run --json
```

## Output Structure
The planner generates a structured report containing:
- `advancement_plan_id`: Unique identifier for the plan.
- `readiness_status`: Current readiness classification (`ready_for_human_review`, `partially_ready`, etc.).
- `readiness_score`: Numeric score (0-100) reflecting evidence strength.
- `proposed_future_state`: Advisory text indicating the potential next state.
- `blockers`: List of issues preventing advancement.
- `warnings`: Important notes for the operator.
- `required_human_checks`: Manual verification steps for the operator.

## Readiness Statuses
- `ready_for_human_review`: Strong evidence exists, and no blockers are present.
- `partially_ready`: Some evidence exists, but more work or synchronization is needed.
- `blocked`: Critical issues or missing dependencies prevent advancement.
- `insufficient_evidence`: Not enough data to make an assessment.
- `not_ready`: Deliberate state indicating advancement is not yet appropriate.

## Evidence Sources
1.  **State Sync Audit**: Verifies that `state.json` is synchronized with confirmed actions.
2.  **Pointer Plan Status**: Verifies that `next_learning_task` is current and unambiguous.
3.  **Confirmation Ledger**: Ensures all learning actions are confirmed and traceable.
4.  **Artifact Verification**: Confirms that referenced evidence files exist on disk within the stronghold.

## Blocker Rules
Advancement is blocked if:
- `state.json` or the confirmation ledger is missing.
- `next_learning_task` requires a pointer update (must be synchronized first).
- Confirmation entries are malformed or missing artifact paths.
- Confirmed artifact files are missing from disk.
- Conflicting candidates exist for the next task.

## Why Advancement Remains Manual
Advancement is classified as **HIGH risk** because it triggers lifecycle transitions that affect syllabus progression and review schedules. In Phase 10A, the system provides only an advisory assessment to assist the human operator in making a manual decision.

## Validation Results
- **Isolation Fixture**: PASS (Correctly identified partial/ready states without mutation).
- **Hard Guard**: PASS (Confirmed `apply_allowed_in_phase_10b` and `can_apply_now` are always false).
- **Live Stronghold Test**: PASS (`fine-tuning-small-open-source-models` evaluated as `READY_FOR_HUMAN_REVIEW`).

## Known Limitations
- Score logic is basic in v1 (0/20/50).
- Only supports `MANUAL_REVIEW_REQUIRED` as the proposed future state.
- Does not yet inspect deep content of tutor sessions or assessments.

## Readiness for Phase 10B
The planner is **READY** to provide the data required for a future supervised advancement apply layer.
