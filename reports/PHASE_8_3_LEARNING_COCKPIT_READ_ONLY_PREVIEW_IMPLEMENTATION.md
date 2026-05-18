# Phase 8.3: Learning Cockpit Read-Only Preview Implementation

## Overview
Phase 8.3 implements the **Learning Cockpit** read-only preview surface within the Workstation TUI. This dashboard provides the operator with a centralized view of study progress, artifact provenance, and tactical next steps without authorizing autonomous mutation. It bridges the gap between raw CLI runners and a managed user interface, ensuring the human operator retains absolute understanding of the stronghold's state before manual execution.

## Files Changed
- **`tui/app.py`**: 
    - Implemented a `LearningStronghold` state synthesizer that discoveres strongholds and builds a complete state profile from `state.json` and durable logs.
    - Added a recommendation engine that computes the logical next study action based on current artifact presence and session status.
    - Integrated the `Learning Cockpit` section into the `--snapshot` output and the interactive `--plain` mode.
    - Implemented a command preview generator that translates the recommended next action into its exact CLI syntax.
- **`tui/README.md`**: Updated to document the new Learning Cockpit features and reiterate the read-only safety policy.
- **`WORKSTATION_MANUAL.md`**: Added a dedicated section for TUI and Dashboard capabilities.

## Read-Only Behavior
The Learning Cockpit is strictly informational. It performs the following analytical tasks:
1. **Stronghold Discovery**: Scans `strongholds/learning` for active workspaces.
2. **State Synthesis**: Reads `state.json`, `progress.md`, and `practice_log.md` to identify the last completed task and the current tactical focus.
3. **Artifact Mapping**: Resolves paths for the latest session plans, tutor sessions, answer templates, and assessments.
4. **Provenance Tracking**: Verifies if imported answers are explicitly linked to the latest tutor session, identifying potentially stale or contaminated evidence.

## Command Preview Behavior
The cockpit calculates the most logical next command to progress the stronghold. Examples include:
- `ws learning-run <id> --session --dry-run` (if a new task is ready).
- `ws learning-assess <id> --model <model>` (if answers have been imported but not evaluated).
- `ws learning-advance <id>` (if a positive advancement decision has been recorded).

Commands requiring variable human input (like an answers file) use the `<answers_file>` placeholder to guide the operator.

## Validation Run
- **Syntax Check**: `python3 -m py_compile tui/app.py` passed.
- **Snapshot Execution**: `ws tui --snapshot` successfully displayed the current state of the "fine-tuning-small-open-source-models" stronghold, correctly identifying it as ready for its next session plan.
- **Interactive Execution**: `ws tui --plain` successfully responded to the `l` key, displaying the detailed Learning Cockpit and returning to the main menu.
- **System Stability**: Verified that `ws ready` and `ws stronghold-status` remain consistent.

## Limitations
- **Read-Only**: The cockpit cannot yet execute the previewed commands.
- **Linear Logic**: The recommendation engine follows the primary learning/review loop; complex branching may require manual command entry.

## Next Recommended Phase
Implement **Phase 8.4: Research Cockpit**, applying these same analytical TUI patterns to the research domain to track hypotheses and evidence matrices.
