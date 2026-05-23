# Backtest Data Requirement Runbook

## Purpose
After a strategy candidate has been revised, it may require specific datasets before a backtest can be considered. This runbook extracts and formalizes those requirements from the Candidate record.

## How Requirements are Derived
The `backtest_data_requirements.py` engine strictly maps the Candidate's conceptual `data_requirements`, `universe_definition`, and `timeframe_definition` into a formal contract.

## Why No Data is Downloaded
This milestone explicitly prohibits calling Yahoo Finance, Alpaca, IBKR, or any external market data API. The Workstation requires explicit, safe data management. This artifact only defines what *must* exist.

## Status Meanings
- **`blocked_missing_candidate_detail`**: The upstream strategy candidate failed to provide basic definitions.
- **`needs_data_mapping`**: The requirements are clear; next, the dataset mapping stub must be produced.

## Execution
```powershell
python scripts/quant/backtest_preparation_cli.py data-requirements `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --readiness-file reports/quant/pre_backtest_readiness/<READINESS_ID>.json `
  --dry-run
```
*(Append `--write` to save it).*

## Safety Boundaries
- **No Performance Claims:** Gathering requirements does not validate a strategy.
- **No Network I/O:** Execution uses zero external requests.