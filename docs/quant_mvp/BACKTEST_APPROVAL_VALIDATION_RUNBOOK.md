# Backtest Approval Validation Runbook

## Purpose
Once a human operator has drafted an Approval Input file, this gate validates it. It ensures all technical and safety criteria are met before a single backtest run can be authorized in a future milestone.

## Validation Rules
The system enforces several strict requirements:
1. **Explicit Approval:** `explicit_approval_for_single_backtest` must be `True`.
2. **Reviewer Identified:** A real human reviewer must be specified.
3. **Scope Bounded:** Approval must be limited to a single backtest plan only.
4. **Technical Readiness:** Upstream gates (Readiness, Backtest Plan, Data Source) must all be in an approved or ready state.
5. **Forbidden Actions:** No authorization for paper or live trading is allowed.

## Statuses
- **`blocked`**: One or more validation rules failed.
- **`pending_human_completion`**: The approval input artifact is missing or incomplete.
- **`valid_for_single_backtest_plan_review`**: All criteria pass. Ready for final eligibility summary.

## Execution
```powershell
python scripts/quant/backtest_eligibility_cli.py approval-validate `
  --candidate-file reports/quant/strategy_candidates/<CANDIDATE_ID>.json `
  --readiness-file reports/quant/pre_backtest_readiness/<READINESS_ID>.json `
  --backtest-plan-file reports/quant/backtest_plans/<PLAN_ID>.json `
  --data-source-decision-file reports/quant/data_source_decisions/<DSD_ID>.json `
  --approval-input-file reports/quant/single_backtest_approval_inputs/<INPUT_ID>.json `
  --dry-run
```

## Safety Boundaries
- **Validation != Execution:** This report only validates paperwork. It does not run any code.
- **Single Use:** Validations are specific to the unique ID of the input file.
