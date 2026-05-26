# Execution Run Contract

Execution Lane MVP Slice 1 run manifests are preparation-only artifacts derived
from a Discovery queue manifest in `READY_FOR_EXECUTION_LANE`.

## Required Fields

- `run_id`
- `source_queue_manifest`
- `source_queue_checksum`
- `set_id`
- `queue_status`
- `created_at`
- `created_by`
- `run_status`
- `queued_phase_count`
- `prepared_task_count`
- `source_discovery_handoffs`
- `source_phase_packets`
- `source_worker_prompts`
- `source_branch_plans`
- `linked_product_development_manifest`
- `linked_product_development_artifacts`
- `branch_creation_allowed`
- `execution_allowed`
- `commit_allowed`
- `push_allowed`
- `merge_allowed`
- `worker_task_packets`
- `exchange_handoff_previews`
- `validation_summary`
- `human_review_required`
- `safety_notes`

## Allowed `run_status` Values

- `PLANNED_DRY_RUN`
- `PREPARED_NOT_EXECUTED`
- `BLOCKED_QUEUE_NOT_READY`
- `BLOCKED_INVALID_QUEUE`
- `BLOCKED_MISSING_ARTIFACTS`
- `BLOCKED_PRODUCT_DEV_VALIDATION`
- `CLOSED`

## Required Conservative Values

- `branch_creation_allowed: false`
- `execution_allowed: false`
- `commit_allowed: false`
- `push_allowed: false`
- `merge_allowed: false`
- `human_review_required: true`

## Safety Boundary

- Run manifests are preparation metadata only.
- Run manifests are not execution approval.
- Run manifests do not execute worker prompts.
- Run manifests do not start terminals or model providers.
- Run manifests do not create branches, commits, pushes, or merges.
