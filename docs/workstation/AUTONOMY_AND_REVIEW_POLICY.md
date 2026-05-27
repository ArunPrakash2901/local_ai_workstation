# Autonomy and Review Policy

This policy governs the autonomy level of the Local AI Workstation and defines when human intervention is required versus when automated loops can safely proceed.

## Autonomy Levels

The workstation operates under a configurable autonomy mode. The active mode dictates the maximum allowed automated progression.

- `LEVEL_0_CAPTURE_ONLY`: The workstation captures outputs but does not automatically validate or summarize them. Every imported result requires manual review.
- `LEVEL_1_VALIDATE_AND_SUMMARIZE`: Results are automatically validated. Clean validations are promoted to summaries, but no automated repair or looping occurs.
- `LEVEL_2_AUTO_REPAIR_PACKET`: The workstation may automatically generate a repair packet for blocked validations (e.g., malformed JSON, missing sections) and dispatch it.
- `LEVEL_3_PATCH_PROPOSAL`: Validated results can be automatically parsed into source patches, but they are not applied.
- `LEVEL_4_APPLY_WITHIN_ALLOWED_SCOPE`: Patches can be automatically applied to the local filesystem if they fall entirely within the explicitly allowed workspace scope and do not touch guarded files.
- `LEVEL_5_TEST_AND_REPAIR_LOOP`: The workstation may automatically run tests and generate repair iterations based on test failures.
- `LEVEL_6_PREPARE_COMMIT_ONLY`: The workstation can automatically stage changes and prepare commit messages, but will pause for human confirmation before committing.
- `LEVEL_7_COMMIT_REQUIRES_APPROVAL`: The workstation can commit changes automatically but pauses before pushing or merging.
- `LEVEL_8_PUSH_MERGE_REQUIRES_APPROVAL`: The workstation can push and merge changes automatically (Full Autonomy within boundaries).

**MVP Status:** Currently, the workstation defaults to `LEVEL_1_VALIDATE_AND_SUMMARIZE`. Higher levels involving automated patch application or looping are not yet implemented for the CLI adapters.

## Review Granularity

To prevent operator fatigue while maintaining strict safety, the workstation distinguishes between actions that *always* require human review and those that can be safely automated.

### What is Automated (No Manual Review Required)
- **Raw Output Packet Review:** Raw outputs captured from CLI tools are considered untrusted. They do not require manual review *before* automated validation.
- **Validation Report Generation:** The system automatically runs validation checks against imported results based on the exchange contract.

### What Requires Human Review
- **Blocker Report Review:** Any validation failure or execution blockage (`BLOCKED_NEEDS_OPERATOR`) must be reviewed and resolved by a human.
- **Final Implementation Report:** Before promoting a body of work as "complete" or moving to the next major phase, an operator must review the synthesized summary.
- **Source Mutation (Git Operations):** Creating branches, committing, pushing, and merging always require explicit human approval (`LEVEL_6` through `LEVEL_8` transition gates).

## Result Promotion Statuses

As raw outputs move through the workstation pipeline, they are assigned promotion statuses. These statuses drive the loop decisions.

- `RAW_UNTRUSTED`: Initial state upon importing a capture manifest.
- `VALIDATED_FOR_SUMMARY`: The result passed all structural and safety checks and is ready to be summarized into a human-readable report.
- `VALIDATED_FOR_REPAIR_LOOP`: The result failed validation in a way that the system believes it can auto-repair (if autonomy level permits).
- `VALIDATED_FOR_PATCH_PROPOSAL`: The result passed validation and contains actionable code changes ready to be parsed.
- `VALIDATED_FOR_TEST_RUN`: Patches have been applied, and the system is ready to run automated tests.
- `READY_FOR_OPERATOR_REVIEW`: The automated loop has paused, and a synthesized report is ready for human inspection.
- `BLOCKED_NEEDS_OPERATOR`: A critical failure occurred (e.g., safety violation, unrecoverable error) requiring manual intervention.
- `REJECTED_BY_POLICY`: The result attempted an action expressly forbidden by the current autonomy policy or safety constraints.
