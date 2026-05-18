# Phase 6.11: Learning Advance to Next Task Implementation

## Overview
Phase 6.11 implements the `ws learning-advance` command, which formalizes the transition between study tasks in the Stronghold OS. This command deterministically marks the current learning task as completed by recording it in a new `progress.md` file and automatically identifies the next tactical task from the operational checklist. This ensures that the operator maintains a clear, evidence-based study path without the need for manual state manipulation.

## Files Changed
- **`scripts/ws`**: Integrated `learning-advance` into the help menu (under "Domain Specific Runners") and the dispatcher.
- **`scripts/ws_learning_advance.sh`** (New): Created the shell script to orchestrate task advancement. It handles stronghold resolution, verifies advancement eligibility (requiring an `ADVANCE_TO_NEXT_TASK` decision), and manages the `progress.md` artifact.
- **`WORKSTATION_MANUAL.md`**: Updated to include documentation for the new `learning-advance` command.

## Command Behavior
The command `ws learning-advance <stronghold_id_or_path>` performs the following:
1. **Verifies Advancement Eligibility**: Confirms that the latest learning review decision was explicitly `ADVANCE_TO_NEXT_TASK`.
2. **Determines Completed Task**: Extracts the focus task from the most recent session or review plan.
3. **Selects Next Task**: Scans `local_checklist.md` for the first unchecked task that has not been previously recorded in `progress.md`.
4. **Artifact Update**:
   - `progress.md`: Appends a "Task Completed" entry detailing the focus, evidence path, date, and next study goal.
5. **State & Log Persistence**:
   - Updates `state.json` with advancement metadata and transitions the session status to `ready_for_next_session`.
   - Appends detailed results to `practice_log.md` and `loop_log.md`.
6. **Next Safe Action Identification**: Provides the exact command to initiate the next study plan (`ws learning-run --session --dry-run`).

## Validation Run
All implemented behavior was verified against the `fine-tuning-small-open-source-models` stronghold:
- **Syntax Check**: All scripts passed `bash -n`.
- **Advancement Execution**: Successfully advanced from the "Gather sample CLI commands" task.
- **Artifact Verification**: 
  - `progress.md` was correctly initialized and updated with the completed task and its evidence.
  - `state.json` accurately reflected the transition to `ready_for_next_session` and identified the next task ("Format dataset as JSONL").
  - `loop_log.md` recorded the advancement event.
- **System Stability**: Verified that `ws ready` and `ws agent-hygiene` remain stable, with no unauthorized mutation of project repositories.

## Limitations
- **Manual Checklist Sync**: While the command tracks progress in `progress.md`, it does not currently rewrite `local_checklist.md` to check the boxes, ensuring the checklist remains a non-destructive reference.
- **Linear Progression**: The command assumes a linear progression through the checklist; complex branching study paths may require manual intervention in `progress.md`.

## Next Step
Transition to **Phase 7: Research Run Design**, applying the established Stronghold OS feedback, remediation, and advancement patterns to the research and synthesis domain.
