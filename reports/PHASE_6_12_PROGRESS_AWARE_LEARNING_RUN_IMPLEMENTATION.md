# Phase 6.12: Progress-Aware Learning Run Implementation

## Overview
Phase 6.12 enhances the `ws learning-run` dry-run mode by making it aware of the student's progress. Instead of simply selecting the first unchecked item in the checklist, the command now prioritizes the `next_learning_task` defined in `state.json` (populated by `ws learning-advance`) and cross-references `progress.md` to ensure that previously completed tasks are not re-selected. This creates a cohesive, stateful transition between study sessions.

## Files Changed
- **`scripts/ws_learning_run.sh`**: 
  - Updated the Python logic for task selection. It now explicitly checks `state.json` and `progress.md` before falling back to the `local_checklist.md`.
  - Refined the output parser in the Bash script to be more flexible, ensuring it can handle varying JSON keys between dry-run and model-backed execution modes without error.

## Command Behavior
In `--session --dry-run` mode, the command now:
1. **Reads `state.json`**: Retrieves the `next_learning_task` set during the last advancement.
2. **Reads `progress.md`**: Builds a set of all completed tasks to ensure they are excluded from selection.
3. **Logic-Based Selection**: 
   - If a `next_learning_task` exists and is not yet completed, it becomes the session focus.
   - Otherwise, it scans `local_checklist.md` for the next available, non-completed task.
4. **Plan Generation**: Correctly identifies the next tactical goal (e.g., "Format dataset as JSONL") and generates a structured study plan under `sessions/`.
5. **Durable Logging**: Records the "Planned Session" in `practice_log.md` and `loop_log.md`, maintaining an accurate audit trail of the adaptive study path.

## Validation Run
All implemented behavior was verified against the `fine-tuning-small-open-source-models` stronghold:
- **Progress Awareness**: Successfully identified that the "CLI collection" task was complete and correctly targeted "**Intern**: Format dataset as JSONL" as the focus for the next session.
- **Robustness**: Verified that the Bash script correctly parsed the dry-run JSON output, fixing a regression where it previously expected keys only present in model-backed sessions.
- **Artifact Verification**: Confirmed that `state.json` was updated with the latest plan metadata and that `progress.md` remains the authoritative record of completed work.
- **System Stability**: Verified that `ws ready` and `ws agent-hygiene` remain stable.

## Limitations
- **Manual Advancement required**: The dry-run still requires the operator to have run `ws learning-advance` to achieve optimal task targeting from `state.json`.
- **Heuristic-Based Logic**: Task matching relies on string equality; minor variations in task descriptions between the checklist and logs may cause redundant selection.

## Next Step
Implement **Phase 7: Research Run Design**, applying the established Stronghold OS feedback, remediation, and advancement patterns to the research and synthesis domain.
