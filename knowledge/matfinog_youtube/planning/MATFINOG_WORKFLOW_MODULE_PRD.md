# MatFinOg-Inspired Quant Research Workflow Coach PRD

## Product Vision
To provide a locally hosted, AI-assisted learning and research scaffolding environment that guides users through disciplined quantitative research workflows, heavily emphasizing risk management, strict validation, and structured hypothesis testing.

## Problem Statement
Developing quant research skills often lacks structure, leading to rushed strategy formulation without proper validation, execution analysis, or risk-first thinking. There is a need for a local tool that enforces rigor and organizes research prompts without taking on the role of an automated trader.

## Target User
The primary user is a researcher or developer operating a Local AI Workstation who wants to learn and apply rigorous quantitative analysis techniques in a simulated, paper-trading environment.

## User Goals
- Learn structured quantitative research workflows.
- Organize research and validation prompts.
- Consistently apply risk-first review processes.
- Translate academic papers or market hypotheses into testable frameworks.

## Non-Goals
- Executing live trades.
- Generating automated trading strategies.
- Predicting market direction.
- Providing financial advice.

## Core Use Cases
1. **Hypothesis Validation Scaffold:** The user inputs a market hypothesis, and the module provides a checklist of validation and risk-review questions.
2. **Paper-to-Backtest Planner:** The user provides an academic paper, and the module extracts a structured plan for how to test it out-of-sample.
3. **Execution Review Checklist:** The module prompts the user to define their slippage, spread, and VWAP considerations for a proposed idea.
4. **Prompt Organization:** Browsing and selecting from the 366 pre-generated research prompts to guide independent research.

## Explicitly Unsupported Use Cases
- Asking the module what asset to buy or sell.
- Having the module connect to a broker API to place a trade.
- Running autonomous bots that iterate on strategies without human intervention.
- Requesting financial or investment advice.

## MVP Scope
- A prompt library and workflow browser based on the extracted `research_prompt_candidates.jsonl`.
- Static workflow templates for the 7 primary workflows identified in `workflow_index.csv`.
- Markdown-based checklist generators for risk and validation.

## Out-of-Scope Items
- Backtesting engine execution (this is handled by existing Quant MVP layers, not this learning module).
- Embeddings, RAG, or Vector DB integrations (Phase 6, requires separate approval).
- Live broker APIs.

## Source Artifacts Used
- `knowledge\matfinog_youtube\processed\workflow_index.csv`
- `knowledge\matfinog_youtube\processed\research_prompt_candidates.jsonl`
- `knowledge\matfinog_youtube\processed\topic_index.csv`

## User Journey
1. User opens the Workflow Coach module.
2. User selects a research intent (e.g., "Review a new market hypothesis").
3. The deterministic system loads the `market_inefficiency_hypothesis_workflow` template.
4. The system presents required inputs and validation checkpoints.
5. The AI assists in drafting the research plan (but cannot execute it).
6. The user must manually approve all checkpoints before the research plan is finalized.

## Human Approval Points
- Before any research plan is considered "ready for testing."
- Before any code is moved from the learning module to the local backtester.
- Review of all AI-generated prompt responses.

## AI Responsibilities
- Organizing and surfacing relevant research prompts.
- Drafting structural outlines for research plans.
- Highlighting missing validation steps based on templates.

## Deterministic System Responsibilities
- Enforcing the workflow sequence.
- Blocking progression if mandatory risk questions are unanswered.
- Tagging all outputs with safety disclaimers.

## Success Metrics
- Number of research plans successfully structured.
- Completion rate of risk-first checklists.
- 0 incidents of generated financial advice or broker logic.

## Risks
- The user might attempt to prompt the AI for trading signals despite UI warnings.
- The AI might hallucinate risk metrics.

## Assumptions
- The user will adhere to the local, paper-trading-only operating model.
- The workflow templates extracted from the MatFinOg corpus provide sufficient scaffolding.

## Open Questions
- How closely should this module integrate with the existing `docs\quant_mvp\`?
- What UI framework will ultimately present these workflows?

## Safety Notice
**No financial advice generated. No trading signals generated. No investment recommendations generated. No broker logic generated. No bot logic generated. No live trading automation generated.**
