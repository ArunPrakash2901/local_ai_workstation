# Dispatch Plan Contract

A dispatch plan is metadata that links an exchange packet to a runtime assignment/session for future execution.

A dispatch plan is not execution approval.

A dispatch plan does not:
- start terminals
- start sessions
- run CLIs
- run models
- call APIs
- automate browsers
- approve permission prompts
- create branches
- commit
- push
- merge

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

## Safety Boundary

Dispatch planning stops before execution.

- A dispatch plan records intent only.
- A dispatch plan may link a packet to a runtime session and assignment.
- A dispatch plan may record compatibility and checksum validation results.
- A dispatch plan does not dispatch the packet.
- A dispatch plan does not start terminals.
- A dispatch plan does not run CLIs.
- A dispatch plan does not approve permission prompts.
- A dispatch plan does not create branches.
- A dispatch plan does not commit, push, or merge.
