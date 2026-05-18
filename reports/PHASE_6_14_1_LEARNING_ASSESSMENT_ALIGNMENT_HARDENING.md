# Phase 6.14.1: Learning Assessment Alignment Hardening

## Root Cause
The initial alignment fix implemented in Phase 6.14 relied on a simple modification timestamp comparison. This proved insufficient because it didn't prevent assessments when an answer import failed or was skipped. In a specific observed failure mode, the operator's attempt to import fresh answers failed (due to a missing source file), but the orchestrator's state still pointed to the *previous* successful import's answers. Since those old answers had a timestamp newer than an *even older* tutor session, the logic was not resilient enough to detect that they were unrelated to the *currently active* tutor session.

## Contaminated Scenario Observed
- **Tutor Session**: Generated for "Format dataset as JSONL" (Timestamp B).
- **Import Attempt**: Fails (Answers for B not recorded).
- **Previous Answers**: Still exist from the "Gather sample CLI commands" task (Timestamp A).
- **`ws learning-assess`**: Successfully executed, assessing Answers A against Tutor Context B.
- **Contaminated Artifacts**:
  - `assessments/assessment_20260518_154016.md`
  - `reports/learning_decision_20260518_154026.md`
  - *Note: These files are preserved for historical audit but should be considered invalid/contaminated.*

## Explicit-Link Fix Implemented
Implemented a "Hard-Block" strategy requiring an explicit logical link in `state.json`.

1. **Successful Import Recording**: `ws learning-import-answers` now only records a successful link if the copy operation actually succeeds. It persists:
   - `last_learning_answers_for_tutor_session_path`
   - `last_learning_answers_import_success: true`
2. **Strict Link Verification**: `ws learning-assess` now ignores timestamps and strictly verifies that:
   - `last_learning_answers_import_success` is exactly `true`.
   - The path stored in `last_learning_answers_for_tutor_session_path` is an exact match for the *currently latest* tutor session file.
3. **Hard Blocking**: Any mismatch or missing success flag results in a hard stop with the error code `LEARNING_ASSESSMENT_REQUIRES_CURRENT_ANSWERS`.
4. **Actionable Recovery**: The error message now identifies which tutor session the current answers belong to (if any) and provides the precise command to establish a valid link.

## Validation Results
- **Mismatched State**: Confirmed that after generating a new tutor session, `ws learning-assess` blocks correctly even if old answers exist.
- **Successful Linking**: Confirmed that a successful `ws learning-import-answers` run correctly populates the explicit link in `state.json`.
- **Authorized Assessment**: Confirmed that the assessment only proceeds when the explicit link is verified.
- **System Stability**: Verified that `ws ready` and `ws agent-hygiene` remain stable.

## Conclusion
The learning domain's integrity is now significantly hardened. The system no longer trusts simple temporal proximity and instead enforces a strict data-provenance link between exercises and their corresponding answers.
