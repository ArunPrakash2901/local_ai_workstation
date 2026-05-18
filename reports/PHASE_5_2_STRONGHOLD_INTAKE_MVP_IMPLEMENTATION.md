# Phase 5.2: Generic Stronghold Intake MVP Implementation

## Overview
Phase 5.2 implements the `ws stronghold-intake` command, a critical step in establishing "Absolute Understanding" before plan generation in the generic Stronghold Operating System. This command generates domain-specific questions for each stronghold type (learning, product, feature, research, and trading-research), transitioning the stronghold state to `INTAKE_IN_PROGRESS`.

## Files Changed
- **`scripts/ws`**: Added `stronghold-intake` to the help menu and dispatcher.
- **`scripts/ws_stronghold_intake.sh`** (New): Orchestrates the generation of intake questions based on the stronghold type defined in `state.json`.
- **`WORKSTATION_MANUAL.md`**: Updated to include the `stronghold-intake` command and its purpose.

## Command Behavior
The command `ws stronghold-intake <stronghold_id_or_path>` performs the following:
1. **Resolves Stronghold**: Supports absolute paths or slugs under `D:\_ai_brain\strongholds/`.
2. **Type-Specific Questions**: Generates a unique set of questions tailored to the stronghold's domain:
   - **Learning**: Background, target outcome, learning style, time commitment.
   - **Product**: Problem description, MVP boundary, success metrics.
   - **Feature**: Repo/project context, expected behavior, allowed files, acceptance criteria.
   - **Research**: Core question, sources, hypothesis, evidence standard.
   - **Trading Research**: Instruments, timeframe, alpha signal, backtest parameters, and **mandatory safety confirmation**.
3. **Artifact Generation**:
   - `intake_questions.md`: The generated questionnaire.
   - `intake_response.md`: A placeholder for the human operator to provide answers.
   - `reports/intake_report_<timestamp>.md`: A diagnostic report of the intake generation.
4. **State Management**: Updates `state.json` to `INTAKE_IN_PROGRESS` and records the `last_intake_at` timestamp.
5. **Logging**: Appends a "Stronghold Intake Generated" entry to `loop_log.md`.

## Validation Run
- **Syntax Check**: All modified scripts passed `bash -n`.
- **Execution**: Successfully generated intake packets for `learning`, `product`, and `trading-research` strongholds.
- **Safety Boundary**: Confirmed that `trading-research` intake questions include prominent warnings about the strictly disabled live trading and capital deployment.
- **State Integrity**: Verified `state.json` accurately reflected the transition to `INTAKE_IN_PROGRESS`.
- **System Stability**: `ws ready` and `ws agent-hygiene` remain passing.

## Limitations
- **Manual Response**: The operator must still manually copy questions to `intake_response.md` and provide answers.
- **No Automated Parsing**: This phase only handles the generation of the questionnaire; parsing and validating the responses will be part of a later phase.

## Next Step
Implement `ws stronghold-plan` to consume the `intake_response.md` and generate an initial implementation or research roadmap.
