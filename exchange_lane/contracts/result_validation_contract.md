# Exchange Result Validation Contract

A result validation record is automated control-plane metadata for an imported
Exchange result packet. It validates capture integrity and safety signals, then
recommends the next loop decision.

Validation does not make output trusted. Validation does not apply code, dispatch
packets, run models, start terminals, create branches, commit, push, or merge.

## Required Fields

- validation_id
- result_id
- result_packet_path
- source_packet_id
- dispatch_plan_id
- capture_manifest_path
- parsed_result_path
- raw_output_path
- validation_source_path
- operator_report_path
- created_at
- validation_status
- validation_checks
- safety_flags
- expected_outputs_check
- forbidden_actions_check
- file_change_check
- command_check
- test_result_check
- blocker_check
- retry_eligibility
- human_escalation_required
- recommended_loop_decision
- reasons
- generated_by

## Allowed validation_status Values

- VALIDATION_PASSED
- VALIDATION_FAILED
- VALIDATION_WARNING
- VALIDATION_BLOCKED
- VALIDATION_INCOMPLETE

## Required Checks

1. Result packet exists.
2. Result status is `IMPORTED_PENDING_REVIEW` or `IMPORTED_PENDING_VALIDATION`.
3. Result packet is untrusted before validation.
4. Capture manifest exists.
5. `parsed_result.json` exists.
6. `raw_output.md` exists.
7. `validation.md` exists.
8. `operator_report.md` exists.
9. Capture manifest safety flags are conservative.
10. `branch_created` is false.
11. `commit_performed` is false.
12. `push_performed` is false.
13. `merge_performed` is false.
14. `app_source_modified` is false.
15. Fake dispatch does not claim a model/provider call.
16. Fake dispatch does not claim a terminal was started.
17. `parsed_result.commands_run` is empty or allowed.
18. `files_created` and `files_modified` are empty or inside allowed roots.
19. Blockers are surfaced.
20. Parsed result validation status is understood.

## MVP Status Rules

- Conservative fake dispatch with no blockers: `VALIDATION_PASSED` and
  `COMPLETED_PENDING_DAILY_REVIEW`.
- Blockers present: `VALIDATION_BLOCKED` and `BLOCKED_NEEDS_OPERATOR`.
- Forbidden safety flags true: `VALIDATION_FAILED` and
  `BLOCKED_FORBIDDEN_ACTION`.
- Required files missing: `VALIDATION_INCOMPLETE` and
  `BLOCKED_VALIDATION_FAILED`.
