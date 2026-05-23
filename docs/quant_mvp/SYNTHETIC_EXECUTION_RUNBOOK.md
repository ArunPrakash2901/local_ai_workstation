# Synthetic Backtest Execution Runbook

## Purpose
The Local AI Workstation prohibits automated backtesting of real trading strategies. The **Synthetic Execution Runner** exists to simulate the technical wiring of a backtest (data loading, arithmetic processing, result generation) using purely synthetic toy data.

## Proving Plumbing
The simulation proves:
- CSV fixtures can be loaded safely.
- Basic mathematical returns can be computed.
- The system correctly identifies synthetic vs. real market data.

## What is NOT executed
- **NO Strategy Logic:** The "toy exposure rule" is passive only.
- **NO Real Market Data:** Only files in `scratch/quant_data_imports/` are allowed.
- **NO Signal Generation:** No buy/sell/hold decisions are emitted.

## Execution
```powershell
python scripts/quant/synthetic_execution_cli.py run-synthetic `
  --candidate-file reports/quant/strategy_candidates/CAN-951be4d5c93a-R3.json `
  --fixture scratch/quant_data_imports/example_spy_daily_synthetic.csv `
  --dry-run
```
*(Append `--write` to save it).*

## Safety Boundaries
- **Run Status:** Always marked as `synthetic_smoke_test_only`.
- **Execution Allowed:** The flag for real candidate execution remains hardcoded to `False`.
