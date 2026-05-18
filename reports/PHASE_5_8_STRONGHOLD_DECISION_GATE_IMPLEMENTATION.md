# Phase 5.8: Generic Stronghold Decision Gate Implementation

## Overview
Phase 5.8 implements the `ws stronghold-decision` command, which serves as a deterministic "Decision Gate" within the Stronghold OS. This command analyzes a stronghold's current state, artifact readiness, and domain-specific constraints to classify the next safe state or action. It provides the operator with clear guidance on whether a stronghold is ready for local work, supervised agent execution, or requires further planning/review.

## Files Changed
- **`scripts/ws`**: Integrated `stronghold-decision` into the help menu and dispatcher. Fixed minor syntax issues in the dispatcher tail.
- **`scripts/ws_stronghold_decision.sh`** (New): Orchestrates the analysis of stronghold artifacts. It uses Python to implement a state-aware classification matrix, tailored to the five primary stronghold domains.
- **`WORKSTATION_MANUAL.md`**: Updated to include the `stronghold-decision` command and its role in the supervised workflow.

## Command Behavior
The command `ws stronghold-decision <id_or_path>` performs the following:
1. **Resolves Stronghold**: Supports slugs or absolute paths.
2. **Artifact Analysis**: Checks for the presence and content of core artifacts (`state.json`, `contract.md`, `goals.md`, `constraints.md`, `success_criteria.md`, `architect_plan.md`, `local_checklist.md`, `final_report.md`).
3. **Deterministic Classification**: Assigns one of several states (e.g., `READY_FOR_LOCAL_WORK`, `READY_FOR_SUPERVISED_AGENT`, `NEEDS_ARCHITECT_PLAN`, `BLOCKED`) based on readiness and domain.
4. **Safety Enforcement**:
   - **Trading Research**: Explicitly prevents any classification leading to live trading. Mandates safety reminders for research/backtest/paper-trading only.
   - **Learning**: Prioritizes human-centric study and practice over automated execution.
5. **Durable Reporting**: Writes a timestamped decision report to the stronghold's `reports/` folder.
6. **State Persistence**: Updates `state.json` and `loop_log.md` with the decision metadata.

## Validation Run
- **Syntax Check**: All scripts passed `bash -n`.
- **Learning Stronghold**: Correctly classified a fully prepared stronghold as `READY_FOR_LOCAL_WORK`, recommending study and practice.
- **Trading Research Stronghold**: Correctly classified as `READY_FOR_LOCAL_WORK` while prominently displaying the **MANDATORY** safety warnings against live trading and capital deployment.
- **Incomplete Stronghold**: Correctly identified missing artifacts (e.g., plans or reports) and recommended the appropriate `ws` commands to resolve them.
- **System Stability**: Verified that `ws ready` and `ws agent-hygiene` remain passing.

## Limitations
- **Read-Only Gate**: The command only provides guidance; it does not automatically transition the stronghold state to "Running" or "Complete".
- **Deterministic Logic**: The decision is based on artifact existence and simple content checks; it does not perform deep semantic analysis of the plan's quality.

## Next Step
Implement `ws stronghold-run` (starting with dry-run) to begin executing tasks defined in the operational checklist for domains that support automated workers.
