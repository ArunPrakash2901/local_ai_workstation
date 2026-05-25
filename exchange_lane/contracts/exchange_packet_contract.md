# Exchange Packet Contract

An exchange packet is a structured, non-executing handoff request.

## Required Fields

- `packet_id`
- `packet_version`
- `created_at`
- `created_by`
- `source_lane`
- `source_artifact_type`
- `source_artifact_path`
- `source_artifact_checksum`
- `target_adapter`
- `target_session_id`
- `target_assignment_id`
- `task_type`
- `objective`
- `input_artifacts`
- `expected_outputs`
- `allowed_write_roots`
- `forbidden_paths`
- `forbidden_actions`
- `human_approval_required`
- `execution_allowed`
- `commit_allowed`
- `push_allowed`
- `merge_allowed`
- `safety_class`
- `packet_status`
- `blocker_ids`
- `quota_notes`
- `operator_notes`
- `lineage`

## Allowed `packet_status`

- `DRAFT`
- `READY_FOR_REVIEW`
- `APPROVED_FOR_DISPATCH_PLANNING`
- `DISPATCH_PLANNED`
- `BLOCKED`
- `REJECTED`
- `RESULT_IMPORTED`
- `CLOSED`

## Conservative Defaults

- `execution_allowed: false`
- `commit_allowed: false`
- `push_allowed: false`
- `merge_allowed: false`
- `human_approval_required: true`

## Safety Rule

`APPROVED_FOR_DISPATCH_PLANNING` does not authorize execution. It only marks packet readiness for future dispatch planning workflows.
