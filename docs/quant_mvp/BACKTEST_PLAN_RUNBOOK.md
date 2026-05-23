# Backtest Plan Runbook

## Purpose
This runbook explains how to generate the formal Backtest Plan contract based on an approved Handoff Manifest. A backtest plan finalizes all assumptions (timeframe, data sources, position sizing, cost models) before the deterministic execution engine is allowed to run.

## Workflow Context
The flow must be strictly followed:
`Strategy Candidate` -> `Pre-Backtest Readiness Gate` -> `Backtest Handoff Manifest` -> **`Backtest Plan`**

If the Pre-Backtest Readiness Gate determines the candidate is `needs_more_detail`, the system will generate a Backtest Plan with a status of `blocked`. 

**Why the current VWAP candidate is blocked:**
The current `CAN-951be4d5c93a` artifact intentionally lacks explicit details (e.g., data parameters and universe). Because of this intentional incompleteness designed to force human thought, the Readiness Gate rejected it, successfully protecting the system from running a backtest on an ambiguous idea.

## Execution
*Note: `ws` commands deferred (Q3.5).*

```powershell
# Attempt to draft a plan
python scripts/quant/backtest_cli.py plan-draft `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --readiness-file reports/quant/pre_backtest_readiness/<READINESS_ID>.json `
  --dry-run
```

*(Append `--write` to save if unblocked).*

## Safety Boundaries
- **No Execution:** This generates a plan only. It does not call the backtester.
- **Human Approval:** A plan requires human sign-off before it can be executed.