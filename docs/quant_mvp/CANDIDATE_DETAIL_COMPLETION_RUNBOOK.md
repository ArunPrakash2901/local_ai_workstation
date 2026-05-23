# Candidate Detail Completion Runbook

## Purpose
A Strategy Candidate often fails the Readiness Gate because specific execution, data, or risk parameters are `UNKNOWN`. This runbook explains how a human operator provides these missing details to move the candidate toward a backtest plan.

## How it Works
1. Review the **Gap Report** (`reports/quant/readiness_gap_reports/`).
2. Draft a **Completion Note** in `scratch/quant_strategy_candidates/`.
3. Run the `complete-candidate` command.

## Suffixing
The system appends an `-R2` suffix to the Candidate ID (branching from the revised `R1` candidate), preserving the historical research chain.

## Execution
```powershell
python scripts/quant/backtest_gate_cli.py complete-candidate `
  --candidate-file reports/quant/strategy_candidates/CAN-951be4d5c93a-R1.json `
  --completion-note scratch/quant_strategy_candidates/example_vwap_detail_completion.md `
  --dry-run
```
*(Append `--write` to save it).*

## Safety Boundaries
- **No Trading:** Completion notes cannot suggest "live trading" or "guaranteed profit." 
- **Conceptual Only:** Even with completed details, the candidate remains a theoretical draft until human-approved and backtested.
