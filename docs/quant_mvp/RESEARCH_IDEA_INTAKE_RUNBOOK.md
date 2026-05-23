# Research Idea Intake Runbook

## Purpose
This runbook guides operators through capturing raw quantitative research ideas and converting them into strict, human-reviewed Hypothesis Contracts within the Local AI Workstation. This marks **Phase Q4** of the Quant Trading MVP.

## Where Ideas Come From
Research ideas can originate from:
- Human intuition and market observations.
- Prompts derived from the MatFinOg YouTube corpus.
- Claims extracted from academic research papers.
- Exploratory outputs from cloud LLMs (via the Exchange Lane).

## Allowed Source Types
When capturing an idea, the `source_type` must be one of:
- `human_note`
- `matfinog_prompt`
- `research_paper`
- `market_structure_observation`
- `cloud_model_suggestion`
- `other`

## Review Statuses
The workflow is strictly gated.
- **Research Ideas** start as `needs_human_review`. Once validated by an operator, they can be marked `accepted_for_hypothesis_contract` or `rejected`.
- **Hypothesis Contracts** start as `draft` or `needs_human_review`. An operator must verify that the claim is falsifiable and data is available before marking it `accepted_for_research_planning`.
- **Forbidden:** No artifact here can be marked `approved_strategy`, `paper_trading`, or `live_trading`.

## Idea Examples
- **Safe Idea:** "Investigate if the VIX displays mean-reverting properties after three consecutive days of >5% gap ups, focusing on the 2015-2023 window."
- **Unsafe Idea (BLOCKED):** "Create a strategy to direct buy AAPL whenever RSI crosses 30 for guaranteed profit using broker execution."
*(The system will actively reject the unsafe idea using local regex guards).*

## Important Distinctions
- **Idea Intake != Strategy Generation:** Idea intake merely records a concept. It writes zero code and generates no signals.
- **Hypothesis Contract != Backtest Approval:** A hypothesis contract defines *how* a test should be structured. It does not run the backtest, nor does it approve live capital.

## Human Review Checkpoints
Both the `research_idea_template.md` and `hypothesis_contract_template.md` require physical/digital checkboxes to be ticked by the human operator confirming safety, realism, and alignment.

## Command Examples (PowerShell)
*Note: `ws` shortcuts are deferred by Q3.5 constraints. Use the standalone low-resource CLI.*

**Check Schema:**
```powershell
python scripts/quant/idea_cli.py schema-check --dry-run
```

**Draft an Idea (from string, Dry Run):**
```powershell
python scripts/quant/idea_cli.py idea-intake `
  --title "VIX Mean Reversion" `
  --source-type "human_note" `
  --raw-idea "Test VIX spikes fading over 5 days." `
  --dry-run
```

**Draft an Idea (from Markdown file, Dry Run):**
Place your idea file inside `scratch/quant_ideas/` or `reports/quant/research_ideas/inputs/`. File must be < 50KB.
```powershell
python scripts/quant/idea_cli.py idea-intake `
  --title "VWAP Research Paper Replication Idea" `
  --source-type "human_note" `
  --idea-file "scratch/quant_ideas/example_vwap_research_paper_idea.md" `
  --dry-run
```

**Write an Idea to Disk:**
Replace `--dry-run` with `--write` to save the validated idea record to the reports folder.
```powershell
python scripts/quant/idea_cli.py idea-intake `
  --title "VWAP Research Paper Replication Idea" `
  --source-type "human_note" `
  --idea-file "scratch/quant_ideas/example_vwap_research_paper_idea.md" `
  --write
```

**Generate a Hypothesis Draft:**
The resulting Hypothesis Contract is printed out (or saved alongside the idea record if `--write` is specified).
```powershell
python scripts/quant/idea_cli.py hypothesis-draft `
  --idea-file reports/quant/research_ideas/<GENERATED_IDEA_ID>.json `
  --dry-run
```

## Safety Boundaries
- **No Financial Advice**
- **No Trading Signals**
- **No Live Trading**
- **No GPU/LLM Required:** This intake workflow uses 0GB VRAM and <150MB of system RAM. All validation is deterministic and local.