# Pre-Backtest Readiness Gate Runbook

## Purpose
This runbook describes how to evaluate a Strategy Candidate to see if it is fully specified and ready to be handed off to a backtester. This ensures that no backtests are run on incomplete, purely theoretical, or loosely bounded ideas, eliminating the risk of overfitting through ambiguity.

## The Checklist
The system checks the candidate record for completeness:
- **Data:** `data_requirements` defined?
- **Universe:** `universe_definition` defined?
- **Timeframe:** `timeframe_definition` defined?
- **Features:** `feature_requirements` defined?
- **Slippage & Costs:** Execution models defined?
- **Risk:** `risk_controls_required` defined?
- **Validation:** `validation_requirements` defined?
- **Failure Modes:** `known_failure_modes` defined?

## Statuses
- **`needs_more_detail`**: One or more fields are empty or marked `UNKNOWN`.
- **`ready_for_human_backtest_review`**: All mandatory fields are populated. Human review required next.
- **`rejected`**: The candidate was deemed untestable.

## Execution
```powershell
# Dry Run to see what is missing
python scripts/quant/strategy_candidate_cli.py readiness-check `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --dry-run

# Write the readiness report
python scripts/quant/strategy_candidate_cli.py readiness-check `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --write
```

## Safety Boundaries
- **Readiness != Approval:** A status of `ready_for_human_backtest_review` simply means the paperwork is complete. It does not mean the strategy is approved, and it does not trigger any backtest process automatically.