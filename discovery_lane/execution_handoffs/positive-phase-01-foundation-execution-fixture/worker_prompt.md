# Worker Prompt: positive_phase_01 - Foundation Execution Fixture

This prompt is ready for human review before execution handoff.

## Required First Step

Read the phase packet first: `phase_packets/positive_path_example__positive_phase_01_foundation_packet.md`

## Scope Boundary

- You are implementing only this phase.
- Do not reinterpret the product.
- Do not expand scope.
- Do not introduce new frameworks without justification.
- Do not perform unrelated cleanup.
- Do not modify files outside the phase scope unless explicitly necessary and documented.
- Preserve existing architecture.
- Implement only the listed tasks.
- Run validation commands where available.
- If blocked, write a blocker report instead of guessing.
- Do not commit or push unless the execution lane explicitly allows it.

## Phase Status

- current_status: READY_FOR_HUMAN_REVIEW

## Placeholders For Execution Lane

- target_repository_path: TO_BE_CONFIRMED_BY_OPERATOR
- branch_name: TO_BE_CONFIRMED_BY_OPERATOR
- allowed_files: TO_BE_FILLED_AFTER_HUMAN_REVIEW
- forbidden_files: TO_BE_FILLED_AFTER_HUMAN_REVIEW
- validation_commands: TO_BE_CONFIRMED_BY_OPERATOR
- commit_permission: false
- push_permission: false
- merge_permission: false

## Human Decisions Required Before Execution

None.

## Final Summary Required

When finished, report:

- files changed
- tests run
- risks
- blockers
- next steps
