# Synthetic Result Review Runbook

## Purpose
After a synthetic execution run is completed, it must pass through the **Synthetic Result Review Gate**. This gate verifies that the results are indeed synthetic and have not accidentally touched real market data or strategy logic.

## Review Checks
- **Fixture Confirmation:** Confirms the `synthetic_fixture` flag is true.
- **Forbidden Interpretations:** Ensures the result is not being used as performance evidence for a strategy.
- **Plumbing Validation:** Marks the result as `valid_synthetic_plumbing_test`.

## Acceptable Interpretation
The results within this review can ONLY be used to confirm that the backtest engine's arithmetic and I/O logic are functioning correctly.

## Safety Boundaries
- **Strategy Evaluation:** The field `acceptable_for_strategy_evaluation` is hardcoded to `False`.
- **Real-World Flags:** Any record found with `real_market_data_used: true` will be rejected by the reviewer.

## Execution
```powershell
python scripts/quant/synthetic_execution_cli.py review-synthetic `
  --synthetic-run-file reports/quant/synthetic_execution_runs/<run_id>.json `
  --dry-run
```
*(Append `--write` to save the review).*
