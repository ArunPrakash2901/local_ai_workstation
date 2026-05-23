# Strategy Candidate Revision Runbook

## Purpose
After generating a Gap Report, you must revise the Strategy Candidate. This runbook explains how to submit a revision note that clarifies missing fields without overwriting the original artifact history.

## Workflow
1. Write a markdown note in `scratch/quant_strategy_candidates/` answering the gaps.
2. Run the `revise-candidate` command.
3. The system appends an `-R1` suffix to the Candidate ID and writes a fresh JSON file, preserving the original.

## Execution
```powershell
python scripts/quant/readiness_remediation_cli.py revise-candidate `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --gap-report-file reports/quant/readiness_gap_reports/<GAP_REPORT_ID>.json `
  --revision-note scratch/quant_strategy_candidates/<YOUR_NOTE>.md `
  --dry-run
```

## Safety Boundaries
- **No Trading Allowed:** A revision note that suggests "live trading" or "guaranteed profit" will be rejected by the local regex guards.
- **Human Review:** The revised candidate is automatically marked `needs_human_review`. It is not automatically approved.