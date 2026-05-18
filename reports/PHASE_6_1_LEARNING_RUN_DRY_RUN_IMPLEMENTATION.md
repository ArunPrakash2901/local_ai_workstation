# Phase 6.1: Learning Run Dry-Run MVP Implementation

## Overview
Phase 6.1 implements the `ws learning-run` command in a dry-run-only capacity. This command marks the first domain-specific "Runner" for the Stronghold OS, focusing on orchestrating interactive learning sessions. The MVP successfully automates the transition from a tactical checklist to a structured study plan without the risk of AI hallucination or code mutation.

## Files Changed
- **`scripts/ws`**: Added `learning-run` to the help menu (under "Domain Specific Runners") and the dispatcher.
- **`scripts/ws_learning_run.sh`** (New): Created the shell script to orchestrate session planning. It handles stronghold resolution, type validation, and state-aware preflight checks.
- **`WORKSTATION_MANUAL.md`**: Updated to include the `learning-run` command and its role in the study workflow.

## Command Behavior
The command `ws learning-run <stronghold_id_or_path> --session --dry-run` performs the following:
1. **Resolves Stronghold**: Strictly targets subfolders of `D:\_ai_brain\strongholds/learning/`.
2. **Validates State**: Ensures the stronghold is in a ready state (`LOCAL_CHECKLIST_READY`, `ARCHITECT_PLAN_IMPORTED`, or `READY_FOR_LOCAL_WORK`).
3. **Identifies Task**: Uses a flexible regex to extract the first pending task from `local_checklist.md`.
4. **Generates Session Plan**: Creates a timestamped file under `sessions/` containing:
   - Specific session objective based on the next task.
   - Theoretical study topics and practice exercises.
   - Self-assessment questions.
   - Estimated time management blocks.
5. **Durable Logging**:
   - Appends a "Planned Session" entry to `practice_log.md`.
   - Records the generation event in `loop_log.md`.
   - Updates `state.json` with the latest plan metadata.

## Validation Run
All implemented behavior was verified against the `fine-tuning-small-open-source-models` learning stronghold:
- **Syntax Check**: All scripts passed `bash -n`.
- **Preflight Gating**: Correctly refused to run against non-learning strongholds or those in an incorrect state.
- **Plan Generation**: Successfully extracted the first task ("Gather sample CLI commands") and generated a comprehensive session plan.
- **Artifact Verification**: Confirmed that `sessions/`, `practice_log.md`, `loop_log.md`, and `state.json` were correctly updated.
- **System Stability**: Verified that `ws ready` and `ws agent-hygiene` remain stable.

## Limitations
- **Dry-Run Only**: This implementation strictly generates a markdown plan; it does not call the local model to act as a tutor yet.
- **Simple Heuristics**: Topic extraction and exercise generation use simple templates based on the task description rather than deep syllabus analysis.

## Next Step
Implement the **Model-Backed Tutor Session** (Phase 6.2), allowing local Ollama models to actively explain concepts and evaluate exercises defined in the session plan.
