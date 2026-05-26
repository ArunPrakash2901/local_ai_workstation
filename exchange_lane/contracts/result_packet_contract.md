# Result Packet Contract

A result packet is a future imported output record from CLI/local model sessions.

## Required Fields

- `result_id`
- `capture_id`
- `source_packet_id`
- `source_dispatch_plan_id`
- `source_capture_manifest`
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
- `trusted`
- `fake_execution`
- `real_cli_execution`
- `execution_occurred`
- `model_or_provider_called`
- `terminal_started`
- `branch_created`
- `commit_performed`
- `push_performed`
- `merge_performed`
- `app_source_modified`
- `imported_at`
- `operator_notes`

## Allowed `result_status`

- `DRAFT`
- `IMPORTED_PENDING_REVIEW`
- `IMPORTED_PENDING_VALIDATION`
- `ACCEPTED_BY_HUMAN`
- `REJECTED_BY_HUMAN`
- `BLOCKED`
- `ARCHIVED`

## Conservative Defaults

- `execution_occurred: false`
- `model_or_provider_called: false`
- `terminal_started: false`
- `branch_created: false`
- `commit_performed: false`
- `push_performed: false`
- `merge_performed: false`
- `app_source_modified: false`
- `trusted: false`
- `human_review_required: true` at import time until automated validation and loop decision metadata decide whether immediate operator escalation is required.

`human_review_required` on the imported packet is a conservative import flag. It
does not mean every result must be manually accepted or rejected before the loop
can continue; that decision belongs to automated validation and loop-decision
records.
