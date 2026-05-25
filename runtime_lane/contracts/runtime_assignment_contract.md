# Runtime Assignment Contract

Runtime Session Lane assignments connect a manually operated runtime session to a specific task source. An assignment is ownership metadata only. It does not execute the task, start terminals, approve prompts, or perform git actions.

Required fields:
- `assignment_id`
- `session_id`
- `adapter_id`
- `assignment_label`
- `task_source_type`
- `task_source_path`
- `task_source_checksum`
- `lane`
- `intended_worker`
- `assigned_at`
- `last_updated`
- `assignment_status`
- `priority`
- `expected_outputs`
- `allowed_write_roots`
- `forbidden_paths`
- `human_approval_required`
- `depends_on_assignments`
- `blocker_ids`
- `quota_notes`
- `operator_notes`
- `execution_allowed`
- `commit_allowed`
- `push_allowed`
- `merge_allowed`

Allowed assignment statuses:
- `PLANNED`
- `ASSIGNED_NOT_STARTED`
- `IN_PROGRESS`
- `WAITING_FOR_OPERATOR_APPROVAL`
- `BLOCKED_SESSION`
- `BLOCKED_QUOTA`
- `BLOCKED_DEPENDENCY`
- `BLOCKED_MISSING_CONTEXT`
- `COMPLETED_PENDING_REVIEW`
- `CLOSED`
- `ABANDONED`

Allowed task source types:
- `discovery_execution_queue`
- `discovery_handoff_bundle`
- `product_development_manifest`
- `product_development_implementation_plan`
- `product_review_artifact`
- `product_design_run_packet`
- `manual_operator_task`
- `other_metadata_artifact`

Conservative defaults:
- `execution_allowed`: `false`
- `commit_allowed`: `false`
- `push_allowed`: `false`
- `merge_allowed`: `false`
- `human_approval_required`: `true`

Assignment means "this session owns this task source."
Assignment does not mean "execute this task source."
