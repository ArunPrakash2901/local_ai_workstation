# Quant Lane Index

## Current State Summary
The Quant lane has established a robust infrastructure for "Safe Quant Research". All components for idea intake, paper replication, and synthetic execution are in place. The repository recently underwent a major cleanup (M4-M6), removing ~1900 temporary probe and test directories, resulting in a cleaner working environment. The system is currently in a "Readiness & Approval" phase.

## Active ws quant Commands
- `dashboard`: Real-time view of the research factory status.
- `reports`: Browse generated research artifacts.
- `status`: Check safety gates and resource usage.
- `list-tools`: List available quant CLI tools.
- `idea-intake-dry-run`: Test the intake process for a new research idea.
- `synthetic-status`: Check the status of the synthetic execution engine.
- `gates-status`: Check which milestones and safety gates are active.

## Key Contracts (contracts/quant/)
- `research_idea_schema.yaml`: Schema for new research ideas.
- `human_write_approval_schema.yaml`: Schema for HAFs.
- `execution_policy.yaml`: Global safety rules.
- `risk_policy.yaml`: Policy for backtest risk management.

## Key Scripts (scripts/quant/)
- `cli.py`: The entry point for all `ws quant` commands.
- `human_write_approval.py`: The validator for human approval forms.
- `write_approval_prepare.py`: Tool for generating draft HAFs and evidence.
- `ws_quant_summary.py`: Logic for the dashboard and status reports.

## Key Tests (tests/quant/)
- `test_ws_quant_operator_smoke.py`: Core CLI functionality test.
- `test_human_write_approval.py`: HAF validation test.
- `test_ws_quant_no_write_wrapper.py`: Verification of safety blocks.

## Milestone Reports (docs/quant_mvp/)
- **Phase 1: Foundation**: Q3 - Q5 (Synthesis, UX, Research Idea Intake).
- **Phase 2: Simulation**: Q6 - Q11 (Strategy Candidates, Backtest Skeleton).
- **Phase 3: Readiness**: Q42 - Q50 (No-Write Wrapper, Guarded Write, Approval Prep).
- **Phase 4: Executor Control**: Q51 - Q53 (No-Op Write Executor, Blocked Audit).

## Current Candidate Lineage
- Source: `scratch/quant_ideas/example_vwap_research_paper_idea.md`
- Draft HAF: `scratch/quant_approvals/example_idea_intake_write_approval_draft.md`
- No-Op Execution: `scratch/quant_approvals/evidence/AUDIT-GW-NOOP-XXXX.md`
- Status: **BLOCKED** (Final block verified in Q53).

## What Remains Blocked
- Real backtest execution (`run_backtest`).
- Disk mutation in `reports/quant/` from `ws quant` commands.
- Signal generation and live trading paths.

## Recommended Next Milestone
**Quant Q54-Q56**: First Guarded Write Enablement Review + Single Artifact Write Simulation.
Authorizing the first single-artifact mutation (idea intake only) to prove the HITL process.
