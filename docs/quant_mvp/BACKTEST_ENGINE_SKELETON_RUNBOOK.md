# Deterministic Backtest Engine Skeleton Runbook

## Purpose
The Local AI Workstation prohibits the automated backtesting of real trading strategies to prevent the generation of unverified signals or financial advice. The `backtest_engine.py` script serves as a **skeleton interface** to test the arithmetic and IO pipelines of the Workstation using purely synthetic, mathematically defined toy data.

## What the Smoke Test Proves
- The Python pipeline can successfully parse JSON rows.
- Basic deterministic arithmetic (e.g. simple returns) works locally.
- The Engine outputs result data in a shape the Manifest layer expects.

## What it Does NOT Prove
- It does **not** test strategy logic.
- It does **not** evaluate technical indicators or signals.
- It does **not** connect to brokers or real market data.

## Execution
```powershell
python scripts/quant/backtest_cli.py synthetic-smoke `
  --fixture scratch/quant_backtests/synthetic_price_fixture.json `
  --dry-run
```

*(Append `--write` to save the dummy test results).*

## Resource Expectations
- Zero GPU.
- < 150MB RAM usage. Only standard Python libraries are used. No large `pandas` loads are permitted for these toy fixtures.