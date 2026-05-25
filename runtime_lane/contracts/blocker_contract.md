# Blocker Contract

Runtime blockers record why a manually operated session needs operator attention. Blocker records are metadata only.

Required fields:
- `blocker_id`
- `session_id`
- `blocker_type`
- `detected_or_reported_at`
- `description`
- `operator_action_required`
- `suggested_safe_response`
- `resolved_at`
- `resolution`
- `followup_required`

Allowed blocker types:
- `WAITING_FOR_PERMISSION_PROMPT`
- `QUOTA_EXHAUSTED_OR_RATE_LIMITED`
- `CLI_AUTH_EXPIRED`
- `TOOL_REQUEST_OUT_OF_SCOPE`
- `TERMINAL_FROZEN_OR_UNRESPONSIVE`
- `FILE_CONFLICT_RISK`
- `GIT_DIRTY_UNEXPECTED`
- `VALIDATION_FAILED`
- `UNKNOWN_BLOCKER`

Blockers should describe the safe next operator action. Runtime Session Lane must not auto-resolve permission prompts, quota issues, auth issues, or git conflicts.

