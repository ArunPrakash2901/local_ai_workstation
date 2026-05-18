# Phase 6.6: Targeted Learning Review Session Implementation

## Overview
Phase 6.6 implements the `ws learning-review-session` command, enabling the workstation to generate targeted study plans for students who have received a `REVIEW_CURRENT_TASK` or `REPEAT_SESSION` decision. This command mark a key advancement in adaptive learning within the Stronghold OS, automatically identifying knowledge gaps from the latest assessment and focusing the next study session on addressing those specific weaknesses.

## Files Changed
- **`scripts/ws`**: Integrated `learning-review-session` into the help menu and dispatcher.
- **`scripts/ws_learning_review_session.sh`** (New): Created the shell script to orchestrate the generation of targeted review plans. It handles stronghold resolution, validates the necessity of a review session based on the latest decision, and uses heuristics to extract specific "Areas for Improvement" from the assessment.
- **`WORKSTATION_MANUAL.md`**: Updated to include documentation for the new review planning command.

## Command Behavior
The command `ws learning-review-session <stronghold_id_or_path> --dry-run` performs the following:
1. **Validates Necessity**: Ensures the stronghold is in a `learning` domain and that the latest decision actually warrants a review (e.g., `REVIEW_CURRENT_TASK`).
2. **Gap Identification**: Automatically extracts specific study gaps from the latest `assessments/assessment_*.md` file.
3. **Targeted Plan Generation**: Creates a `sessions/<timestamp>_review_session_plan.md` that includes:
   - Specific Review Objectives.
   - A list of identified Gaps to Address.
   - Practice Tasks tailored for correction and re-submission.
   - Clear "Criteria to Advance" to the next task.
4. **Durable Logging**: 
   - Appends a "Review Session Planned" entry to `practice_log.md`.
   - Records the generation event in `loop_log.md`.
   - Updates `state.json` with review plan metadata.

## Validation Run
- **Syntax Check**: All scripts passed `bash -n`.
- **Preflight Gating**: Correctly identified that the `fine-tuning-small-open-source-models` stronghold required a review due to its `REVIEW_CURRENT_TASK` decision.
- **Plan Generation**: Successfully extracted specific gaps (dataset size, validation split, monitoring) and generated a comprehensive review plan.
- **Artifact Verification**: Confirmed that `sessions/`, `practice_log.md`, `loop_log.md`, and `state.json` were accurately updated.
- **System Stability**: Verified that `ws ready` and `ws agent-hygiene` remain stable.

## Limitations
- **Dry-Run Only**: This implementation generates the targeted plan but does not invoke a tutor model to conduct the session yet.
- **Extraction Heuristics**: Relies on specific header formatting in the assessment to identify gaps; highly unconventional assessment structures may result in less targeted gap lists.

## Next Step
Implement **Phase 7: Research Run Design**, leveraging these adaptive feedback patterns for the research and evidence synthesis domains.
