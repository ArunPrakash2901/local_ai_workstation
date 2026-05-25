# Branch Execution Contract

This contract defines planned future branch behavior for Execution Lane. It is documentation only.

## Principles

- Branch creation must be explicit.
- Branch name must come from the Discovery Lane branch plan unless overridden by a human.
- Branch status transitions must be recorded.
- No push without permission.
- No merge without permission.
- Merge planning must be separate from merge execution.
- Conflicts must produce a blocker report, not blind fixes.

## Allowed Future Branch Statuses

- `PLANNED_NOT_CREATED`
- `CREATED_NOT_STARTED`
- `EXECUTION_IN_PROGRESS`
- `EXECUTION_COMPLETE_PENDING_REVIEW`
- `READY_FOR_MERGE_REVIEW`
- `MERGED`
- `BLOCKED`
- `ABANDONED`

## Initial Requirement

Execution Lane must begin with Discovery Lane branch plans in:

```text
PLANNED_NOT_CREATED
```

If a queue manifest claims a branch already exists before Execution Lane has explicitly created or adopted it, the future execution system must block and request human review.

## Future Push And Merge Rules

- `push_allowed` must be true before push can even be considered.
- `merge_allowed` must be true before merge can even be considered.
- A human review step must validate the final branch state before push or merge.
- Merge conflicts must not be silently resolved.

## Not Implemented

No branch creation, checkout, push, merge, deletion, or status transition command exists in Execution Lane v0.1.
