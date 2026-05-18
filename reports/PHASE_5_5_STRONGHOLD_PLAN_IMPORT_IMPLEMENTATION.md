# Phase 5.5: Generic Stronghold Architect Plan Import Implementation

## Overview
Phase 5.5 implements the `ws stronghold-plan-import` command. This command facilitates the transition from strategic cloud-based planning to local execution by importing a Senior Architect's response into a stronghold as the authoritative `architect_plan.md`. This ensures that the workstation maintains a durable, auditable record of the master plan derived from high-reasoning frontier models.

## Files Changed
- **`scripts/ws`**: Integrated `stronghold-plan-import` into the help menu and dispatcher.
- **`scripts/ws_stronghold_plan_import.sh`** (New): Orchestrates the import of architect responses. It validates the handoff role, state, and stronghold alignment before promoting the response to a plan artifact.
- **`WORKSTATION_MANUAL.md`**: Updated to include the `stronghold-plan-import` command and its role in the cognitive hierarchy.

## Command Behavior
The command `ws stronghold-plan-import <id_or_path> --from-handoff latest|<handoff_id>` performs the following:
1. **Resolves Stronghold and Handoff**: Supports slugs, absolute paths, and the `latest` keyword for handoffs.
2. **Preflight Validation**:
   - Ensures the handoff was generated for a `senior_architect` role.
   - Verifies the handoff response is non-empty and non-placeholder.
   - Confirms the handoff `stronghold_id` matches the target stronghold.
   - Allows importing from `RESPONSE_IMPORTED`, `REVIEW_ACCEPTED`, or `ARCHITECT_REVIEW_READY` (to support manual overrides).
3. **Artifact Promotion**: Copies the content of `response.md` in the handoff packet to `architect_plan.md` in the stronghold root.
4. **Safety Analysis (Trading Research)**:
   - Scans the imported plan for keywords associated with live trading (e.g., "brokerage", "execute trades", "real money").
   - If violations are detected, the stronghold is moved to `NEEDS_HUMAN_REVIEW` instead of `ARCHITECT_PLAN_IMPORTED`, and a prominent warning is issued.
5. **State Management**: Updates `state.json` with the authoritative plan path and transitions the state.
6. **Durable Logging**: Records the import event in `loop_log.md` and generates a timestamped report under `reports/`.

## Validation Run
- **Learning Stronghold**: Successfully imported a simulated master plan for the Llama fine-tuning stronghold. The state transitioned to `ARCHITECT_PLAN_IMPORTED`.
- **Trading Research (Safe)**: Imported a research-only backtesting plan; state transitioned as expected.
- **Trading Research (Blocked)**: Attempted to import a plan mentioning "brokerage" and "real money". The system correctly flagged the safety violation, warned the operator, and set the state to `NEEDS_HUMAN_REVIEW`.
- **System Integrity**: Verified that `ws ready` and `ws agent-hygiene` remained stable.

## Limitations
- **No Semantic Understanding**: Beyond simple keyword matching for trading safety, the command does not interpret the plan's feasibility or quality.
- **Manual Handover**: The process still requires the operator to have imported the response into the handoff packet first (via `ws handoff-import`).

## Next Step
Implement `ws stronghold-local-review` (or refine the existing feature-local-review to be generic) so the local "Intern" model can audit the imported architect plan against the original contract.
