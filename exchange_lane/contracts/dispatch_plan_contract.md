# Dispatch Plan Contract

A dispatch plan is metadata that links an exchange packet to a runtime assignment/session for future execution.

It is not execution approval.

It does not:
- start terminals
- run CLIs
- run models
- approve permission prompts
- create branches
- commit, push, or merge

## Required Fields

- `dispatch_plan_id`
- `packet_id`
- `packet_path`
- `packet_checksum`
- `source_artifact_path`
- `source_artifact_checksum`
- `target_adapter`
- `target_session_id`
- `target_assignment_id`
- `runtime_session_path`
- `runtime_assignment_path`
- `planned_status`
- `generated_at`
- `generated_by`
- `compatibility_status`
- `compatibility_notes`
- `quota_notes`
- `approval_notes`
- `operator_notes`
- `execution_allowed`
- `commit_allowed`
- `push_allowed`
- `merge_allowed`
- `blocked_reasons`
- `next_operator_action`

## Allowed `planned_status`

- `PLANNED_NOT_DISPATCHED`
- `BLOCKED_NO_SESSION`
- `BLOCKED_SESSION_NOT_READY`
- `BLOCKED_ADAPTER_MISMATCH`
- `BLOCKED_ASSIGNMENT_MISSING`
- `BLOCKED_SOURCE_CHANGED`
- `BLOCKED_PACKET_NOT_READY`
- `BLOCKED_OPERATOR_DECISION_REQUIRED`

## Conservative Defaults

- `execution_allowed: false`
- `commit_allowed: false`
- `push_allowed: false`
- `merge_allowed: false`
