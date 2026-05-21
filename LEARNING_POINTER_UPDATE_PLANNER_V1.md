# Learning next_learning_task Pointer Update Planner v1

## Purpose
This document defines the dry-run planner for supervised `next_learning_task` pointer updates (Phase 9A). The planner is designed to identify the intended next step in the learning process by inspecting confirmed actions and artifacts, ensuring the state remains synchronized with recent operator decisions.

## Phase Boundary
Phase 9A is strictly **planning-only**. No state mutations are allowed. Implementation of the apply layer follows in Phase 9B.

## Command Shape
The primary interface is through the `ws` unified command.

### Dry-Run Plan
```bash
ws learning-pointer-plan <stronghold_id> --dry-run
ws learning-pointer-plan <stronghold_id> --dry-run --json
```

## Planner Output Structure
The planner generates a JSON report containing:
- `pointer_plan_id`: Unique identifier for the plan.
- `candidate_next_learning_task`: The proposed new value for the pointer.
- `candidate_source`: The confirmation type that provided the candidate.
- `evidence_quality`: Rating of the data supporting the change (`strong`, `partial`, `insufficient`).
- `risk_level`: Defaults to `MEDIUM` for pointer updates.
- `apply_allowed_in_phase_9b`: Boolean indicating if the plan meets safety criteria for future application.

## Source Action Rules
The planner prioritizes confirmed actions in the following order:
1. `PROPOSE_NEXT_LESSON_CONFIRMED`: Primary source for lesson-level tasks.
2. `CREATE_STUDY_TASK_CONFIRMED`: Secondary source for session-specific tasks.
3. `MARK_REVIEW_NEEDED_CONFIRMED`: Source for review-cycle tasks.

## Risk Model
All `next_learning_task` updates are classified as **MEDIUM** risk. They are more complex than simple status toggles (LOW) but safer than lifecycle transitions (HIGH).

## Evidence Quality Rules
- **Strong**: Valid ledger entry, matching artifact exists on disk, and clear task text extracted.
- **Partial**: Task text inferred from titles or secondary evidence.
- **Insufficient**: Missing artifacts or conflicting candidates.

## Blockers and Warnings
### Blockers (Prevent Apply)
- Missing `state.json` or ledger.
- Missing or invalid source artifacts.
- Candidate matches current `next_learning_task` (idempotency).
- Candidate contains unsafe shell commands (e.g., `rm`, `sudo`, `format c:`).
- Conflicting candidates with equal priority.

### Warnings
- Candidate mentions "advancement" (requires human vigilance).
- Candidate derived from secondary source.

## Why next_learning_task is not modified
In accordance with Phase 9A requirements, this tool is restricted to dry-run analysis. State mutations require explicit operator authorization and an atomic write implementation which is reserved for Phase 9B.

## Validation Results
- **Refusal without mode**: PASS.
- **JSON Purity**: PASS.
- **Conflict Detection**: PASS (Latest high-priority candidate selected).
- **Unsafe Pattern Guard**: PASS (Regex-based word boundary checks implemented).
- **Live Stronghold Test**: PASS (Correctly identified current state and blocked on match).

## Known Limitations
- Does not yet inspect the *content* of the artifact, only its metadata and evidence string.
- Limited set of supported action types for derivation.

## Readiness for Phase 9B
The planner is **READY**. It provides the necessary safety checks and evidence traceability required to implement the guarded apply layer.
