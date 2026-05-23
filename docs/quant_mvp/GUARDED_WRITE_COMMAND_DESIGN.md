# Guarded Write Command Design (Q45)

## 1. Purpose
This document defines the architecture and safety requirements for future "guarded write" operations within the Quant research lane. While the workstation currently enforces a strictly read-only/dry-run posture for all `ws quant` commands, this design establishes the protocol for safe, human-approved mutation of local research artifacts.

## 2. Why Write Mode Remains Blocked Today
Write mode is currently blocked in `ws quant` to:
- Prevent accidental or unlogged mutation of the research repository.
- Ensure that every state change is accompanied by a human-signed audit trail.
- Maintain a clean separation between "speculative" research (dry-run) and "committed" research (write).
- Validate the safety wrapper logic in a non-destructive environment.

## 3. Future Candidate Command
The first command targeted for guarded write exposure is:

```bash
ws quant idea-intake-write --approval-file <approval_file>
```

**Note:** This command is NOT yet implemented or exposed in `ws`.

## 4. Required Preconditions for Write Execution
A future write command must only execute if the following conditions are met:
1. **Valid Approval File:** A human-signed YAML or Markdown approval file must be provided.
2. **Schema Compliance:** The approval file must match the `human_write_approval_schema.yaml`.
3. **Hash Matching:** The `source_input_hash` in the approval must match the current hash of the input file.
4. **Dry-Run Evidence:** The `dry_run_output_hash` must match the result of a recent, verified dry-run.
5. **Path Constraint:** The `intended_output_directory` must be within approved workstation paths (e.g., `reports/quant/research_ideas/`).
6. **No Safety Violations:** All safety flags (e.g., `safety_financial_advice_generated`) must be explicitly `false`.
7. **Not Expired:** The approval must not have passed its `expires_at` timestamp.

## 5. Approval File Requirements
- **Format:** YAML or Markdown with YAML frontmatter.
- **Location:** Must be stored in `scratch/quant_approvals/`.
- **Content:** Must include a reason for write, operator confirmation, and explicit acknowledgement of forbidden actions.

## 6. Forbidden Write-Mode Commands
The following capabilities are NEVER authorized via the standard guarded write path:
- `run_backtest`: No real backtest execution.
- `generate_signal`: No trading signal generation.
- `approve_strategy`: No promotion of an unvalidated strategy.
- `paper_trade`: No simulated trading with broker logic.
- `live_trade`: No live market execution.
- `broker_execution`: No direct broker API interaction.
- `download_data`: No external market data fetching.

## 7. Rollback and Recovery
- All write operations must be atomic (writing a single file).
- If a write fails, the system must report the failure and leave no partial artifacts.
- The operator is responsible for manually deleting an incorrect artifact if a mistake is made after approval.

## 8. Why Research Idea Intake First?
Research Idea Intake was selected as the first write candidate because:
- It produces a static, deterministic JSON artifact.
- It has no market data or execution dependencies.
- It is the natural starting point for a research lineage.
- It provides a low-risk testbed for the Human Approval Form (HAF) workflow.

## 9. Future Implementation Sequence
1. **Q45-Q47 (Current):** Design the schema and validator; keep write mode blocked.
2. **Q48-Q50:** Implement the HAF generator (dry-run) and evidence packager.
3. **Q51+:** Enable the first guarded write path behind strict human-in-the-loop (HITL) gates.

## 10. Explicit Limits
- **Write approval does not approve a strategy.**
- **Write approval does not approve a backtest.**
- **Write approval does not approve paper/live trading.**
- **Write approval does not authorize broker actions.**
- **Write approval only permits one local artifact write.**
