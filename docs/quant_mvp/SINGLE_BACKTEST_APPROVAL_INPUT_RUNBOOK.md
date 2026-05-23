# Single Backtest Approval Input Runbook

## Purpose
The Local AI Workstation enforces a "human-in-the-loop" requirement for every backtest. This runbook explains how to draft the **Approval Input** file that an operator must sign before the workstation's execution module can be unlocked.

## Approval Limitations
Approval is **strictly single-use**. A separate approval file is required for every individual backtest plan. This prevents "auto-optimization" or "signal mining" without oversight.

## What Human Must Complete
An operator must manually edit the approval input file to set `explicit_approval_for_single_backtest: True` and supply their signature statement. **The system will never generate an auto-approved file.**

## Execution
```powershell
python scripts/quant/backtest_gate_cli.py approval-input `
  --candidate-file reports/quant/strategy_candidates/<candidate_id>.json `
  --approval-note scratch/quant_approvals/example_single_backtest_approval_input.md `
  --dry-run
```

## Safety Boundaries
- **No Trading:** Approval to backtest is **not** approval to trade real or paper capital.
- **Blocked Status:** If any upstream gate (Readiness, Data mapping) is failed, the approval status will remain `draft` or `rejected`.
