# Phase 6: Learning Run Design

## Executive Summary
Following the successful stabilization of the Generic Stronghold OS, this document designs the first domain-specific execution runner: the **Learning Run**. Unlike implementer agents that mutate codebase state, the Learning Run orchestrates an interactive reasoning loop between the human operator and local models to facilitate skill acquisition, study, and assessment. This domain is prioritized as the first runner due to its high feedback value and inherently low risk profile.

## 1. Rationale: Why Learning First?
- **Safety**: No risk of accidental codebase corruption or capital loss.
- **Cognitive Hierarchy Validation**: Perfect environment to test the "Senior Architect" (Planning) and "Local Intern" (Tutoring/Checking) relationship.
- **High Utility**: Immediate value in helping the operator master the complex AI tools being built within the workstation.

## 2. Execution Pre-requisites
A Learning Run is only authorized when the stronghold is in the `LOCAL_CHECKLIST_READY` state. This ensures that:
1. A clear contract and goals exist.
2. A Senior Architect has provided a strategic Master Plan.
3. A local model has decomposed that plan into granular operational tasks.

## 3. Command Surface
**Primary Command:**
```bash
ws learning-run <stronghold_id_or_path> --session [--model m] [--dry-run]
```
- `--session`: Initiates an interactive learning session based on the next item in the `local_checklist.md`.
- `--dry-run`: Previews the session agenda without invoking the tutor model.

## 4. Information Flow

### 4.1 Ingested Artifacts
The runner will read the following to establish context:
- `contract.md` & `goals.md`: The objective and scope.
- `syllabus.md`: The structured educational path.
- `architect_plan.md`: The high-level strategic roadmap.
- `local_checklist.md`: The source of the current tactical task.
- `practice_log.md`: History of previous sessions and acquired knowledge.
- `skill_map.md`: Current competency levels.

### 4.2 Generated Artifacts
- `strongholds/learning/<id>/sessions/<timestamp>_session.md`: The primary record of the interactive session (tutor prompts, student answers, model feedback).
- `practice_log.md`: Appends a summary of the session duration and focus.
- `assessment.md`: Updated if the session included a formal evaluation step.
- `loop_log.md`: Records the session start, end, and terminal state.

## 5. Actor Roles in a Learning Run
- **Human (Student)**: Performs the actual study/practice, provides answers to model prompts, and performs manual exercises.
- **Local Ollama (Tutor)**: Generates explanations, asks probing questions, creates practice exercises, and evaluates student responses.
- **Browser ChatGPT/Gemini (Architect)**: Available via manual handoff for complex explanations that exceed local model capacity.
- **WSL (Orchestrator)**: Manages the session files, tracks time, and updates the state machine.

## 6. Interaction Model: The Tutoring Loop
1. **Selection**: WSL identifies the next pending task in `local_checklist.md`.
2. **Contextualization**: Local model ingests the task and relevant `syllabus.md` section.
3. **Engagement**: Model generates a "Learning Prompt" (e.g., "Explain the concept of X" or "Try to solve exercise Y").
4. **Response**: Human operator writes answers in the session file.
5. **Evaluation**: Local model reviews the answer and provides feedback or follow-up questions.
6. **Finalization**: Human marks the session complete; WSL updates logs and checklists.

## 7. Progress & Measurement
Progress is recorded qualitatively in the `practice_log.md` and quantitatively via the `skill_map.md`. The local model will suggest competency updates (e.g., "Learner has mastered LoRA configuration") which the human must manually confirm.

## 8. Terminal States
- `LEARNING_SESSION_READY`: Preflight checks passed; waiting for human engagement.
- `LEARNING_SESSION_COMPLETED`: Session finished and logged successfully.
- `LEARNING_SESSION_NEEDS_REVIEW`: Human or model flagged a concept for later re-study.
- `LEARNING_SESSION_BLOCKED`: Missing resources (e.g., a paper or dataset) or Ollama failure.

## 9. Safety & Constraints
- **Isolation**: No `learning-run` can mutate project source code.
- **Data Protection**: No PII or secrets sent to any model (local or cloud).
- **Manual Oversight**: No automatic state transition to `COMPLETE` without human approval.
- **Resource Gating**: If Ollama is unresponsive, the command blocks safely with `LOCAL_REASONING_UNAVAILABLE`.

## 10. Recommended MVP implementation
The first implementation phase (**Phase 6.1**) will focus on the **Dry-Run Session Planner**.

**MVP Behavior:**
`ws learning-run <id> --session --dry-run`
1. Resolves the stronghold.
2. Identifies the next checklist task.
3. Generates a `sessions/<timestamp>_session_plan.md` outlining what should be studied and what questions the model *would* ask.
4. Writes no model calls.

## Next Steps
1. Create `scripts/ws_learning_run.sh`.
2. Implement the dry-run session planner.
3. Define the "Tutor" system prompt for `hermes3:8b`.
4. Validate the planning logic against the `fine-tuning-small-open-source-models` stronghold.
