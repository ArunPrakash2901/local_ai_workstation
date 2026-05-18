# Phase 5.6: Generic Local Intern Checklist MVP Implementation

## Overview
Phase 5.6 implements the `ws stronghold-local-checklist` command. This command formalizes the "Intern/Operator" role for local Ollama-hosted models by converting an imported Senior Architect's master plan into a granular, step-by-step operational checklist. This allows the workstation to transition from strategic planning to tactical execution while maintaining a strict cognitive hierarchy.

## Files Changed
- **`scripts/ws`**: Integrated `stronghold-local-checklist` into the help menu and dispatcher.
- **`scripts/ws_stronghold_local_checklist.sh`** (New): Orchestrates the local model query. It validates the stronghold state (`ARCHITECT_PLAN_IMPORTED`), aggregates the strategic context and imported plan, and formats a tactical prompt for the local model.
- **`WORKSTATION_MANUAL.md`**: Updated to include the `stronghold-local-checklist` command and its purpose as an "Intern" mode for task decomposition.

## Command Behavior
The command `ws stronghold-local-checklist <id_or_path> --model hermes3:8b` performs the following:
1. **State Validation**: Strictly mandates the `ARCHITECT_PLAN_IMPORTED` state, ensuring a strategic master plan is available.
2. **Tactical Prompting**: Invokes the local model with an "Intern/Operator" system prompt, instructing it to decompose the master plan into actionable tasks, identify dependencies, and recommend actor assignments (Human, Local Model, Codex).
3. **Domain-Specific Guidance**: Tailors the tactical focus based on the stronghold type:
   - **Learning**: Study sessions, exercises, and assessments.
   - **Product**: Feature implementation and review gates.
   - **Research**: Evidence collection and hypothesis evaluation.
   - **Trading Research**: Backtest gates and strict "RESEARCH ONLY" safety preserving.
4. **Artifact Generation**:
   - `local_checklist.md`: The authoritative tactical roadmap for the stronghold.
   - `responses/local_checklist_<timestamp>.md`: Durable record of the model's output.
   - `evidence/local_model_checklist_<timestamp>.md`: Complete transcript of the reasoning step.
5. **State Management**: Updates `state.json` to `LOCAL_CHECKLIST_READY` and records execution metadata.
6. **Logging**: Appends the generation event to `loop_log.md`.

## Validation Run
- **Syntax Checks**: Verified scripts pass `bash -n`.
- **Execution (Learning)**: Successfully decomposed the fine-tuning master plan into tactical study and dataset preparation steps.
- **Execution (Trading Research)**: Successfully generated a backtesting checklist that strictly respected the "NO LIVE TRADING" constraint and focused on data quality and drawdown limits.
- **Artifact Verification**:
  - `local_checklist.md` contains granular tasks with dependencies and assignments.
  - `state.json` correctly reflected the transition to `LOCAL_CHECKLIST_READY`.
  - `loop_log.md` accurately recorded the event.
- **System Integrity**: `ws ready` and `ws agent-hygiene` remain passing.

## Limitations
- **Ollama Dependency**: The command requires a local Ollama instance with the specified model available.
- **Semantic Nuance**: As an "Intern," the local model may occasionally miss complex strategic nuances from the architect plan, requiring human oversight of the generated checklist.

## Next Step
Implement `ws stronghold-run` (starting with a dry-run) to begin executing tasks defined in the operational checklist.
