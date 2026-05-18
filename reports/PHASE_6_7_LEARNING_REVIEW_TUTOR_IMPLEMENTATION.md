# Phase 6.7: Targeted Learning Review Tutor Implementation

## Overview
Phase 6.7 extends the `ws learning-run` command to support real interactive study sessions specifically focused on remediating knowledge gaps. This implementation introduces the `--review-session` flag, which instructs the local Ollama tutor (defaulting to `hermes3:8b`) to ingest the latest assessment feedback and generate a specialized review session. This ensures that the student achieves mastery of difficult concepts before proceeding to new implementation tasks.

## Files Changed
- **`scripts/ws_learning_run.sh`**: Extended to support the `--review-session` mode. Implemented specialized prompt engineering for the "Review Tutor" role, which specifically addresses identified gaps from the latest assessment. Added support for generating `review_tutor_session.md` and `review_answer_template.md`.
- **`WORKSTATION_MANUAL.md`**: Updated to include documentation for the new targeted review session command.

## Command Behavior
The command `ws learning-run <id_or_path> --review-session --model <m> --from-plan <f>` performs the following:
1. **Preflight Gating**: Verifies the stronghold is in a state requiring review (`REVIEW_CURRENT_TASK` or `REPEAT_SESSION`) and ensures all necessary artifacts (latest assessment, review plan) are available.
2. **Review Tutor Prompting**: Instructs the local model to act as a "Targeted Review Tutor." The prompt ingests the review session plan and the full text of the latest assessment, specifically tasking the model to explain each identified gap and provide corrected examples.
3. **Adaptive Artifact Generation**:
   - `sessions/<timestamp>_review_tutor_session.md`: A tailored tutorial focused on remediation.
   - `sessions/<timestamp>_review_answer_template.md`: A structured template for the user to demonstrate mastery of the previously failed areas.
4. **State & Log Persistence**:
   - Updates `state.json` with review session metadata and transitions the session status to `awaiting_review_answers`.
   - Appends a detailed entry to `practice_log.md` and `loop_log.md` to maintain the audit trail of adaptive study.

## Validation Run
- **Syntax Check**: All modified scripts passed `bash -n`.
- **Adaptive Execution**: Successfully generated a review tutor session for the Llama fine-tuning stronghold based on the `7/10` assessment.
- **Context Integrity**: Verified that the tutor prompt correctly included the "Areas for Improvement" from the assessment (dataset size, validation split, monitoring).
- **Artifact Verification**: Confirmed the generation of both the review session and the review-specific answer template.
- **System Stability**: Verified that `ws ready` and `ws agent-hygiene` remain stable. No project source files were mutated.

## Limitations
- **Ollama Consistency**: The quality of the review depends on the model's ability to remain focused on the provided assessment text; `hermes3:8b` demonstrated high adherence in this MVP.
- **Template Separation**: The review answer template is a separate file from previous templates to avoid data corruption and ensure clear progress measurement.

## Next Step
Transition to **Phase 7: Research Run Design**, applying the established Stronghold OS feedback and remediation patterns to the research and synthesis domain.
