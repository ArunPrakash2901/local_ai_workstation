# Result Packet Contract

A result packet is a future imported output record from CLI/local model sessions.

## Required Fields

- `result_id`
- `source_packet_id`
- `source_session_id`
- `source_assignment_id`
- `adapter_id`
- `result_status`
- `summary`
- `files_created`
- `files_modified`
- `commands_run`
- `validation_run`
- `output_artifacts`
- `errors`
- `warnings`
- `blockers`
- `human_review_required`
- `execution_occurred`
- `branch_created`
- `commit_performed`
- `push_performed`
- `merge_performed`
- `imported_at`
- `operator_notes`

## Allowed `result_status`

- `DRAFT`
- `IMPORTED_PENDING_REVIEW`
- `ACCEPTED_BY_HUMAN`
- `REJECTED_BY_HUMAN`
- `BLOCKED`
- `ARCHIVED`

## Conservative Defaults

- `execution_occurred: false`
- `branch_created: false`
- `commit_performed: false`
- `push_performed: false`
- `merge_performed: false`
- `human_review_required: true`
