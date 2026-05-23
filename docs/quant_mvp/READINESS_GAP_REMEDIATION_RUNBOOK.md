# Readiness Gap Remediation Runbook

## Purpose
When a Strategy Candidate hits the Pre-Backtest Readiness Gate and lacks critical details (like data requirements or execution models), it fails. This runbook explains how to generate a **Gap Report** to explicitly identify what is missing.

## Workflow
If the Readiness Check returns `needs_more_detail`, generate a Gap Report. This report lists all `UNKNOWN` fields and blocking issues.

**Why the current VWAP candidate is blocked:**
It intentionally left the Universe and Timeframe definitions as `UNKNOWN` to force the operator into this remediation cycle.

## Execution
*Note: `ws` commands deferred (Q3.5).*

```powershell
python scripts/quant/readiness_remediation_cli.py gap-report `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --readiness-file reports/quant/pre_backtest_readiness/<READINESS_ID>.json `
  --dry-run
```
*(Append `--write` to save it).*

## Safety Boundaries
- **No Bypassing:** You cannot jump from a failed readiness check to an approved backtest. You must clear the gaps.
- **No Signal Generation:** This report analyzes text completeness; it does not analyze financial logic.