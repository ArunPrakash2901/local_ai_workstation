# Backtest Eligibility Report Runbook

## Purpose
The Backtest Eligibility Report is the final "master gate" in the Quant Research workflow. It summarizes the status of every prerequisite gate (Readiness, Data Source, Plan, and Approval) to determine if a future backtest can proceed.

## Required Gates
All of the following must be in a "Ready" state:
1. **Readiness:** `ready_for_human_backtest_review`
2. **Data Source:** `selected_for_future_data_adapter_review`
3. **Backtest Plan:** `ready_for_human_backtest_review` (or equivalent)
4. **Approval Validation:** `valid_for_single_backtest_plan_review`

## Eligibility Statuses
- **`blocked`**: One or more gates have failed.
- **`pending_human_approval`**: All technical gates pass, but the human has not yet signed the approval input.
- **`ready_for_future_single_backtest_execution`**: ALL gates pass. This candidate is now eligible to be queued for a real backtest run in a future milestone.

## Execution
```powershell
python scripts/quant/backtest_eligibility_cli.py eligibility-report `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --readiness-file reports/quant/pre_backtest_readiness/<READINESS_ID>.json `
  --backtest-plan-file reports/quant/backtest_plans/<PLAN_ID>.json `
  --data-source-decision-file reports/quant/data_source_decisions/<DSD_ID>.json `
  --approval-validation-file reports/quant/backtest_approval_validations/<VLD_ID>.json `
  --dry-run
```

## Safety Boundaries
- **No Execution:** This is a status report only.
- **No Trading:** Every eligibility report explicitly forbids trading signals and orders.
- **No Performance:** There are no backtest results at this stage.
