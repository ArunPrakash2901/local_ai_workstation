# Execution Run Contract

This contract describes future Execution Lane run records. It is documentation only; no execution run writer exists yet.

## Purpose

An execution run record will capture what happened when a future guarded execution lane consumes one approved phase handoff from a `READY_FOR_EXECUTION_LANE` queue.

## Required Fields

- `run_id`
- `set_id`
- `phase_id`
- `queue_manifest`
- `handoff_bundle`
- `branch_name`
- `worker_prompt`
- `started_at`
- `completed_at`
- `execution_status`
- `files_changed`
- `commands_run`
- `tests_run`
- `validation_result`
- `blockers`
- `risks`
- `human_review_required`
- `commit_created`
- `push_performed`
- `merge_performed`

## Conservative Defaults

- `commit_created: false`
- `push_performed: false`
- `merge_performed: false`
- `human_review_required: true`

## Planned Execution Status Values

Future slices may define exact transitions. Initial expected values:

- `NOT_STARTED`
- `RUNNING`
- `COMPLETED_PENDING_REVIEW`
- `BLOCKED`
- `FAILED`

## Required Safety Properties

- Worker output must be treated as untrusted until reviewed.
- Commands run must be recorded explicitly.
- File changes must be listed.
- Validation must be recorded.
- Human review must remain required before commit, push, or merge unless explicitly allowed by a later guarded policy.

## Not Implemented

No command currently creates execution run records.

No command currently runs worker prompts.

No command currently modifies branches, commits, pushes, or merges.
