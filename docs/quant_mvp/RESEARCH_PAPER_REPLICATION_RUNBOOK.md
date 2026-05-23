# Research Paper Replication Runbook

## Purpose
This runbook guides operators through capturing raw notes from quantitative research papers and structuring them into formal Replication Plans within the Local AI Workstation. This marks **Phase Q5** of the Quant Trading MVP.

## Workflow Context
Idea Intake (Q4) captures broad hypotheses or insights. Paper Replication (Q5) is used when the source is a dense academic or practitioner paper that must be methodically reproduced to validate its out-of-sample edge. 

**Workflow:**
1. Analyst reads a paper and types notes into a Markdown file.
2. `paper-intake` ingests the note and structures a `research_paper` artifact.
3. `replication-plan-draft` generates the required validation, data, and assumption checklists.
4. Human analyst reviews and completes the plan.

## Allowed Inputs and Placement
- You must manually create paper notes. 
- **NO PDF PARSING, NO WEB SCRAPING, NO DOWNLOADING.** 
- All notes must reside in: `scratch/quant_papers/`
- Notes must be plain text or Markdown, under 100KB.

## Command Examples (PowerShell)
*Note: `ws` shortcuts are deferred by Q3.5 constraints. Use the standalone low-resource CLI.*

**Check Schema:**
```powershell
python scripts/quant/paper_replication_cli.py schema-check --dry-run
```

**Ingest a Paper Note (Dry Run):**
```powershell
python scripts/quant/paper_replication_cli.py paper-intake `
  --paper-note scratch/quant_papers/example_vwap_paper_note.md `
  --dry-run
```

**Ingest a Paper Note to Disk:**
```powershell
python scripts/quant/paper_replication_cli.py paper-intake `
  --paper-note scratch/quant_papers/example_vwap_paper_note.md `
  --write
```

**Draft a Replication Plan:**
The plan will be linked to the paper record. You can optionally link it to a pre-existing research idea.
```powershell
python scripts/quant/paper_replication_cli.py replication-plan-draft `
  --idea-file reports/quant/research_ideas/RI-98e3264573b3.json `
  --paper-file reports/quant/paper_replications/<GENERATED_PAPER_ID>.json `
  --dry-run
```
*(Append `--write` to save it).*

## Important Distinctions
- **Replication != Strategy Generation:** A replication plan is a plan to test if an academic claim holds up. It writes zero code and generates no signals.
- **Human Review:** The templates require checkboxes to confirm no look-ahead bias and realistic slippage assumptions.

## Safety Boundaries
- **No Financial Advice**
- **No Trading Signals**
- **No Live Trading**
- **No GPU/LLM Required:** This intake workflow uses 0GB VRAM and <150MB of system RAM. All validation is deterministic and local.