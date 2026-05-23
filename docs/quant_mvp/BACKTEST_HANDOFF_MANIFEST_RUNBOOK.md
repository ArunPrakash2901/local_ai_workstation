# Backtest Handoff Manifest Runbook

## Purpose
This runbook explains how to generate the final artifact in the research ideation pipeline: the **Backtest Handoff Manifest**. This file acts as a formal contract handed to a quantitative developer or a backtesting engine (in a future phase) outlining exactly what needs to be tested, without providing the execution logic itself.

## Manifest Fields
The Handoff Manifest captures the frozen state of the candidate and readiness checklists, explicitly outlining:
- `required_datasets`
- `cost_model` & `slippage_model`
- `validation_protocol`
- `risk_checks`

## Allowed vs. Forbidden Actions
To maintain safety boundaries, the manifest explicitly defines what can and cannot be done next.
- **Allowed:** `human_review`, `request_more_detail`, `prepare_backtest_plan`.
- **Forbidden:** `run_backtest_without_human_approval`, `generate_trading_signal`, `place_order`, `paper_trade`, `live_trade`.

## Execution
*Note: A handoff can only be generated if the upstream Readiness Gate returned `ready_for_human_backtest_review`. If it is `needs_more_detail`, the handoff will generate in a `blocked` status.*

```powershell
python scripts/quant/strategy_candidate_cli.py backtest-handoff-draft `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --readiness-file reports/quant/pre_backtest_readiness/<READINESS_ID>.json `
  --dry-run
```

*(Append `--write` to save the manifest to the reports directory).*

## Safety Boundaries
- **No Performance Claims:** This manifest only describes *how* to test, it contains no results.
- **Human Approval:** Human operators must sign off on the manifest before any test occurs.