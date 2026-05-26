# Exchange Loop Decision Contract

A loop decision is the workstation control-plane decision after automated result
validation. It decides whether the loop can continue, needs bounded repair, is
blocked, or is ready for a human gate.

Loop decisions do not execute anything. `AUTO_CONTINUE` does not mean commit,
push, merge, provider dispatch, or source application. Repair decisions are
bounded by retry budget and remain metadata-only until a later guarded slice.

## Required Fields

- loop_decision_id
- result_id
- validation_id
- source_packet_id
- dispatch_plan_id
- decision
- decision_reasons
- retry_count
- retry_budget
- next_action
- auto_continue_allowed
- auto_repair_allowed
- human_escalation_required
- followup_packet_planned
- followup_packet_path
- runtime_assignment_update_planned
- safety_notes
- created_at
- generated_by

## Allowed decision Values

- AUTO_CONTINUE
- AUTO_REPAIR_ONCE
- AUTO_REPAIR_RETRY_AVAILABLE
- BLOCKED_NEEDS_OPERATOR
- BLOCKED_QUOTA_OR_AUTH
- BLOCKED_PERMISSION_PROMPT
- BLOCKED_FORBIDDEN_ACTION
- BLOCKED_VALIDATION_FAILED
- COMPLETED_PENDING_DAILY_REVIEW
- READY_FOR_FINAL_HUMAN_REVIEW

## Retry Defaults

The MVP fake-dispatch flow uses a default retry budget of `1`. Future real
dispatch loops may make this configurable, but every loop remains bounded.

## Human Escalation Policy

Arun is escalated only for permission prompts, quota/auth blockers, forbidden
paths or actions, repeated validation failure beyond retry budget, ambiguous or
contradictory output, branch/commit/push/merge requests, and daily/final gates.
