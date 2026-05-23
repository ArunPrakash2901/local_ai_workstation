# Strategy Candidate Specification Runbook

## Purpose
This runbook captures human intuition, replicated paper claims, or MatFinOg prompts into a **Strategy Candidate**. A candidate is a conceptual draft. It organizes assumptions, data needs, and logic boundaries. 

## Inputs
- Ideas (`reports/quant/research_ideas/`)
- Paper Replications (`reports/quant/paper_replications/`)
- Local Notes (`scratch/quant_strategy_candidates/`)

## Execution
*Note: `ws` commands deferred (Q3.5).*

**1. Create a note in `scratch/quant_strategy_candidates/`**
Limit: 100KB max.

**2. Draft Candidate (Dry Run)**
```powershell
python scripts/quant/strategy_candidate_cli.py candidate-draft `
  --note-file scratch/quant_strategy_candidates/example_vwap_strategy_candidate_note.md `
  --dry-run
```

**3. Write Candidate**
```powershell
python scripts/quant/strategy_candidate_cli.py candidate-draft `
  --note-file scratch/quant_strategy_candidates/example_vwap_strategy_candidate_note.md `
  --write
```

## Review Status
Drafts start as `draft` and remain strictly conceptual. They cannot be executed. You must manually open the generated JSON/Markdown to fill in the `UNKNOWN` sections before running the Pre-Backtest Readiness Gate.