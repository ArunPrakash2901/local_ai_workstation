# Human Backtest Decision Packet Runbook

## Purpose
This runbook explains how to generate the comprehensive decision packet that a human quant researcher must review before investing compute resources into a backtest.

## Decision Statuses
- **`blocked`**: Either the Readiness Gate or Dataset Mapping Gate failed.
- **`pending_human_review`**: All gates passed. Waiting for operator.

## Approval Limitations
- A decision packet does NOT approve the strategy itself.
- A decision packet does NOT authorize trading.
- An approval status of `approved_for_single_backtest_plan` limits authorization to *one* backtest plan execution.

## No Automatic Approval
The Python logic explicitly prevents `decision_status` from being generated as approved. It requires a later human intervention to change this state.

## Execution
```powershell
python scripts/quant/backtest_preparation_cli.py decision-packet `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --readiness-file reports/quant/pre_backtest_readiness/<READINESS_ID>.json `
  --data-requirement-file reports/quant/backtest_data_requirements/<REQ_ID>.json `
  --dataset-mapping-file reports/quant/dataset_mapping_stubs/<MAP_ID>.json `
  --dry-run
```
*(Append `--write` to save it).*

## Safety Boundaries
- **Strictly Forbidden:** The artifact locks out next actions like `paper_trade` or `place_order`. Validation fails if these are omitted from the forbidden list.