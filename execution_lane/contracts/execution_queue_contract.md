# Execution Queue Contract

This contract defines the future Execution Lane input produced by Discovery Lane.

## Required Input

Execution Lane may only consume a Discovery Lane queue manifest:

```text
discovery_lane/execution_queues/<set_id>_execution_queue.json
```

Required top-level condition:

```text
queue_status: READY_FOR_EXECUTION_LANE
```

If `queue_status` is anything else, Execution Lane must refuse.

## Required Queue Fields

- `set_id`
- `source_research_set_ingest_manifest`
- `generated_timestamp`
- `queue_status`
- `queued_phase_count`
- `excluded_phase_count`
- `queued_phases`
- `excluded_phases`
- `errors`
- `warnings`
- `generated_by`

## Required Queued Phase Fields

Each queued phase must include:

- `phase_id`
- `phase_title`
- `phase_packet`
- `worker_prompt`
- `phase_manifest`
- `approval_record`
- `handoff_bundle`
- `branch_plan`
- `proposed_branch_name`
- `branch_status`
- `execution_status`
- `commit_allowed`
- `push_allowed`
- `merge_allowed`
- `dependencies`
- `risk_notes`
- `recommended_execution_order`

## Initial State Requirements

- `branch_status` must initially be `PLANNED_NOT_CREATED`.
- `execution_status` must initially be `NOT_STARTED`.
- `handoff_bundle` must exist.
- `worker_prompt` must exist.
- `branch_plan` must exist.
- `approval_record` must exist.

## Permission Fields

- `commit_allowed`
- `push_allowed`
- `merge_allowed`

These fields record permission intent only. Future execution slices must still enforce explicit human confirmation before commit, push, or merge unless a later policy says otherwise.

## Validation Expectations

Before any future execution starts, Execution Lane must verify:

- queue manifest exists and parses as JSON
- `queue_status` is `READY_FOR_EXECUTION_LANE`
- every queued phase references existing handoff, prompt, branch plan, approval record, and manifest files
- branch status remains `PLANNED_NOT_CREATED`
- execution status remains `NOT_STARTED`
- permissions are explicit booleans
- excluded phases are not executed

## Refusal Cases

Execution Lane must refuse if:

- queue status is not `READY_FOR_EXECUTION_LANE`
- any queued phase is missing handoff or approval artifacts
- branch status has already changed unexpectedly
- execution status is not `NOT_STARTED`
- the queue includes unresolved errors
- a worker prompt path points outside the approved handoff context without explanation
