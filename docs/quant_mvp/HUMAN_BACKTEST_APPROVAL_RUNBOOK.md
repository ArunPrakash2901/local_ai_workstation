# Human Backtest Approval Runbook

## Purpose
Even if a Strategy Candidate is fully specified and a Backtest Plan is drafted, no execution engine will run until a human explicitly authorizes it. This runbook explains how to create the **Pending Approval Stub**.

## What the Stub Is
It is a JSON contract that sits in `reports/quant/human_approvals/` with a hardcoded status of `pending`.

## What the Stub is NOT
- It is **not** strategy approval.
- It is **not** authorization to trade.
- It is **not** automatically approved.

## Execution
```powershell
python scripts/quant/readiness_remediation_cli.py human-approval-stub `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --readiness-file reports/quant/pre_backtest_readiness/<READINESS_ID>.json `
  --dry-run
```

## Safety Boundaries
- For Milestone Q14, the status **cannot** be changed to approved. Any attempt to do so in the JSON and run it through the validator will throw a `ValueError` protecting the system until the actual execution engine (future milestone) is hardened.