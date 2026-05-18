# Phase 7.3: Research Evidence Decision MVP Implementation Report

## Overview
This phase implemented the `ws research-decision` command, providing a local, deterministic classification of research progress within strongholds.

## Files Changed
- `scripts/ws`: Added `research-decision` to help and dispatcher.
- `scripts/ws_research_decision.sh`: Implemented the decision logic using artifact analysis.
- `WORKSTATION_MANUAL.md`: Updated with `ws research-decision` usage.

## Command Behavior
The command `ws research-decision <research_stronghold>`:
1. **Resolves** the stronghold path.
2. **Verifies** all required artifacts (`hypothesis_log.md`, `evidence_matrix.md`, `research_summary.md`, `goals.md`, `success_criteria.md`).
3. **Analyzes** the quantity and quality of evidence:
   - Counts processed sources in `papers/`.
   - Counts candidate hypotheses in `hypothesis_log.md`.
   - Counts evidence entries in `evidence_matrix.md`.
   - Detects if sample/demo sources were used.
4. **Classifies** the next safe action:
   - `ENOUGH_FOR_SYNTHESIS`: Ready to move to synthesis (requires >= 3 sources, >= 2 hypotheses, >= 3 evidence rows).
   - `NEEDS_MORE_SOURCES`: Fewer than 3 sources or sparse evidence.
   - `NEEDS_HUMAN_REVIEW`: Metadata thresholds met but synthesis eligibility is unclear.
   - `RESEARCH_BLOCKED`: Missing artifacts.
5. **Generates** a markdown report in the stronghold's `reports/` folder.
6. **Updates** `state.json` and `loop_log.md`.

## Validation Run
- Executed against the `agentic` research stronghold.
- **Result**: `NEEDS_MORE_SOURCES`
- **Reason**: Insufficient sources (1). Need at least 3 for synthesis.
- **Report**: `strongholds/research/agentic/reports/research_decision_20260518_152054.md`.
- **State Update**: Verified in `state.json`.

## Limitations
- Deterministic only; no semantic understanding of the evidence quality.
- Simple threshold-based classification.
- No PDF parsing or browser integration.

## Next Step
- Phase 7.4: Research Synthesis Runner (Ollama-backed).
