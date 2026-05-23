# Data Source Decision Runbook

## Purpose
Before a backtest can be considered, the Workstation must know where the data will come from. This runbook explains how to choose a data sourcing path.

## Why Before Download?
To prevent the accidental ingestion of low-quality or unlicensed data, the operator must explicitly select a sourcing strategy (e.g. `manual_csv_import` or `future_yfinance_adapter`).

## No Download Rule
Generating this decision record **does not** trigger a download. It only documents the plan.

## Execution
```powershell
python scripts/quant/backtest_gate_cli.py data-source-decision `
  --candidate-file reports/quant/strategy_candidates/<candidate_id>.json `
  --data-requirement-file reports/quant/backtest_data_requirements/<DTR_id>.json `
  --decision-note scratch/quant_data_sources/example_vwap_data_source_decision.md `
  --dry-run
```
*(Append `--write` to save it).*

## Safety Boundaries
- **No API Calls:** No external network requests are made.
- **Provenance:** This step enforces accountability for where backtesting data originated.
