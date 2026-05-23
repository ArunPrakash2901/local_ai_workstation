# Backtest Execution Gate Runbook

## Purpose
The Backtest Execution Gate is the final safety barrier in the Quant Trading Lane. It ensures that every technical prerequisite (Concrete Specification, Manual Dataset Import) and governance prerequisite (Master Eligibility, Human Approval Validation) is perfectly aligned before a backtest can be queued for future execution.

## The Gates
1. **Concrete Spec:** Moves the candidate from conceptual UNKNOWNs to explicit research parameters.
2. **Dataset Import:** Validates the schema and metadata of a locally provided human-supplied CSV fixture.
3. **Execution Preflight:** The master aggregator that exits with a blocked status unless all prerequisite artifacts are present and valid.

## Why it Stays Blocked
For Milestone Q26, the preflight will **always exit with a blocked status** because:
- The backtest runner engine is not yet implemented.
- The `execution_allowed` flag is hardcoded to `False` for safety.
- Human approval input validation is strictly pending.

## Commands
*Note: `ws` commands deferred (Q3.5 rules).*

### 1. Concretize Candidate
```powershell
python scripts/quant/backtest_execution_gate_cli.py concrete-spec `
  --candidate-file reports/quant/strategy_candidates/CAN-951be4d5c93a-R2.json `
  --spec-note scratch/quant_strategy_candidates/example_vwap_concrete_spec.md `
  --write
```

### 2. Import Dataset
```powershell
python scripts/quant/backtest_execution_gate_cli.py dataset-import `
  --candidate-file reports/quant/strategy_candidates/CAN-951be4d5c93a-R3.json `
  --import-note scratch/quant_data_imports/example_dataset_import_note.md `
  --write
```

### 3. Run Preflight
```powershell
python scripts/quant/backtest_execution_gate_cli.py preflight `
  --candidate-file reports/quant/strategy_candidates/CAN-951be4d5c93a-R3.json `
  --dataset-import-file reports/quant/manual_dataset_imports/<import_id>.json `
  --dry-run
```

## Safety Boundaries
- **No Network:** No market data APIs are called.
- **No Execution:** No strategy code is run.
- **Size Capped:** 1MB limit on dataset validation.
