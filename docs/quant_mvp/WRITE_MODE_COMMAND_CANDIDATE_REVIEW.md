# Write-Mode Command Candidate Review (Q42)

## 1. Purpose
This document reviews potential Quant research commands for future exposure to write-mode operations within the unified `ws` workstation interface. Currently, all `ws quant` commands are strictly `PURE_READ`.

## 2. Risk Analysis
Exposing write-mode commands to a unified interface increases the risk of:
- **Accidental Mutation:** Overwriting research artifacts or reports.
- **Unauthorized Execution:** Running backtests or data downloads without full gate compliance.
- **Audit Fragmentation:** Creating artifacts without proper lineage or human signing.
- **Resource Exhaustion:** Triggering heavy writes or processing that violates the workstation's low-resource posture.

## 3. Candidate Review

| Candidate Command | Phase | Complexity | Write Risk | Backtest/Data Risk | Recommendation |
|---|---|---|---|---|---|
| **Research Idea Intake** | Intake | Low | Low (Single JSON) | None | **SELECTED** |
| **Paper Replication Intake** | Intake | Low | Low (Single JSON) | None | Future Candidate |
| **Strategy Candidate Draft** | Research | Medium | Medium (Internal Logic) | Low | Future Candidate |
| **Data Import** | Prep | High | High (Data Files) | Medium (Disk Space) | REJECTED for now |
| **Approval Input** | Gating | High | High (Safety Gate) | High (Bypassing) | REJECTED for now |
| **Synthetic Execution** | Testing | High | High (Results) | Medium (Simulation) | REJECTED for now |
| **Real Backtest** | Execution | Critical | Critical | Critical (Financial) | **STRICTLY BLOCKED** |

## 4. Selection: Research Idea Intake
Research idea intake is selected as the first candidate for future write exposure because:
- It is the entry point of the pipeline.
- It produces a simple, deterministic JSON artifact.
- It has no dependency on market data or execution engines.
- It already includes robust path and size validation in `idea_cli.py`.

## 5. Minimum Safety Requirements for Write Exposure
Before any `ws quant` command is allowed to write files:
1. **Mandatory Dry-Run:** Every write-capable command must have a verified dry-run mode.
2. **Human Approval Form:** A signed approval artifact must be present or generated during the workflow.
3. **Fail-Closed Integration:** The `ws` wrapper must strictly reject write flags unless explicit approval is detected.
4. **Path Lockdown:** Writes must be confined to approved `reports/quant/` subdirectories.

## 6. Current Posture: Dry-Run Only
In milestone Q42-Q44, the selected candidate will be exposed via `ws quant idea-intake-dry-run` as a **strictly no-write prototype**. This allows operators to test the integration and preview artifacts without any risk of mutating the repository state.
