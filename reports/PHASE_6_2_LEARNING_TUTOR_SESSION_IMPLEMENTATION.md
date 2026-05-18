# Phase 6.2: Learning Tutor Session Implementation

## Overview
Phase 6.2 implements the model-backed tutoring capability for the `ws learning-run` command. This enables local Ollama-hosted models (defaulting to `hermes3:8b`) to act as active tutors, generating explanations, worked examples, and specific practice exercises based on a previously generated session plan. This phase maintains the human-in-the-loop requirement by providing a structured answer template for the operator to complete manually.

## Files Changed
- **`scripts/ws_learning_run.sh`**: Extended to support the `--model <m> --from-plan <f>` flags. Implemented the logic to aggregate stronghold context, build a tutor-specific prompt, and query the local Ollama instance. Added extraction logic for answer templates and artifact management.
- **`WORKSTATION_MANUAL.md`**: Updated to include documentation for the new model-backed learning session command.

## Command Behavior
The command `ws learning-run <id_or_path> --session --model <m> --from-plan <f>` performs the following:
1. **Preflight Gating**: Verifies the stronghold type (`learning`), ensures all core artifacts are present, and confirms Ollama is reachable with the requested model.
2. **Tutor Prompting**: Instructs the local model to act as a "Technical Tutor (Intern Level)". The prompt ingests the session plan, feature contract, strategic plan, syllabus, and relevant practice history.
3. **Artifact Generation**:
   - `sessions/<timestamp>_tutor_session.md`: Contains the generated tutorial, examples, and exercises.
   - `sessions/<timestamp>_answer_template.md`: A structured markdown template for the user to provide answers.
   - Durable records in `responses/` and `evidence/` for auditability.
4. **Logging**: 
   - Appends a "Tutor Session Generated" entry to `practice_log.md`, marking it as "awaiting human answers".
   - Records the event in `loop_log.md`.
   - Updates `state.json` with the tutor session metadata.

## Validation Run
- **Syntax Check**: All scripts passed `bash -n`.
- **Preflight**: Correctly identified the available `hermes3:8b` model.
- **Execution**: Successfully generated a tutor session for the "Gather sample CLI commands" task within the Llama fine-tuning stronghold.
- **Artifact Verification**:
  - Confirmed the generation of the tutor session and answer template.
  - Verified that `state.json`, `practice_log.md`, and `loop_log.md` were accurately updated with session metadata.
- **System Stability**: Verified that `ws ready` and `ws agent-hygiene` remain stable, with no unauthorized mutation of project repositories.

## Limitations
- **Passive Feedback**: This phase provides the session content but does not yet evaluate or "grade" the human's answers.
- **Context Size**: Relies on the default context window in `ollama_call.py`; extremely large syllabi may require future context compression.

## Next Step
Implement **Answer Assessment** (Phase 6.3), allowing the local model to ingest and evaluate the completed `answer_template.md`, updating the `skill_map.md` based on demonstrated proficiency.
