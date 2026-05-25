# Runtime Session Contract

Runtime Session Lane sessions are manually operated terminal or CLI sessions. They are registry records only; the lane does not start terminals, run CLIs, approve prompts, execute worker prompts, or perform git actions.

Required fields:
- `session_id`
- `session_label`
- `adapter_type`
- `terminal_type`
- `cwd`
- `lane`
- `assigned_task`
- `status`
- `auth_mode`
- `quota_policy`
- `quota_status`
- `approval_mode`
- `blocked_reason`
- `current_prompt_packet`
- `allowed_write_roots`
- `forbidden_paths`
- `started_at`
- `last_updated`
- `operator_notes`
- `safety_class`
- `commit_allowed`
- `push_allowed`
- `merge_allowed`

Allowed session statuses:
- `PLANNED`
- `READY`
- `RUNNING`
- `WAITING_FOR_OPERATOR_APPROVAL`
- `BLOCKED_QUOTA`
- `BLOCKED_ERROR`
- `BLOCKED_MISSING_CONTEXT`
- `COMPLETED_PENDING_REVIEW`
- `CLOSED`

Conservative defaults:
- `commit_allowed`: `false`
- `push_allowed`: `false`
- `merge_allowed`: `false`
- `approval_mode`: `MANUAL_OPERATOR`
- `safety_class`: `METADATA_ONLY`

