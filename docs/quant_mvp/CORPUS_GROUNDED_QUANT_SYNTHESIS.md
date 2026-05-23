# Corpus-Grounded Quant Synthesis

## Purpose of Ingestion
The MatFinOg YouTube corpus (154 canonical transcripts) was ingested to map and extract recurring quantitative research workflows, discipline frameworks, and learning modules. By grounding the Quant Trading Workstation in these extracted realities, we ensure the system is built on practical, rigorous, risk-first methodologies rather than generic or unsafe assumptions.

## Extracted Patterns
Based on the deterministic analysis of the corpus, several major workflows were identified:
- **Risk-First Strategy Review** (59 videos): Highlighting the necessity of evaluating risk management, position sizing, and protection before any strategy is deployed.
- **Market Inefficiency Hypothesis** (56 videos): The process of identifying structural or institutional constraints that form the basis of a testable hypothesis.
- **AI-Assisted Quant Learning** (52 videos): Leveraging automation and assistants to accelerate research without bypassing critical human validation.
- **Research Paper to Backtest** (42 videos): The structured workflow of taking academic claims, replicating logic, and validating results out-of-sample.
- **Execution Microstructure Review** (29 videos): Focusing on slippage, spread, volume, and fill-quality considerations.

## Shaping the Quant Trading Workstation
These patterns dictate a fundamental shift in how the Workstation should operate. The system must act as a structured *research coach and validation scaffold* rather than just an execution engine.
- Workflows must require users to formulate a concrete hypothesis (Market Inefficiency Hypothesis) before any backtesting occurs.
- Risk management (Risk-First Strategy Review) must be a mandatory, hard-gated checkpoint.
- Execution realities (Microstructure Review) must be accounted for in the research phase to prevent naive backtest overfitting.
- The system should facilitate the translation of literature into code (Research Paper to Backtest) through structured prompts and templates.

## Changes to the Existing Quant MVP Direction
- **Before:** The MVP was primarily focused on data ingestion, backtest execution, and paper trading pipelines.
- **After:** The MVP must now front-load the research process. It needs dedicated "Idea Intake", "Hypothesis Contracts", and "Validation Checklists" that must be completed and human-approved before the backtester is even invoked. The workstation becomes a comprehensive research environment.

## What Should Not Change
- The split-brain architecture separating generative AI (ideation) from deterministic systems (execution/safety) remains intact.
- The strictly enforced local execution and data storage model (DuckDB/Parquet).
- The prohibition of live trading in the MVP.
- The fundamental "AI proposes, Human approves, Software executes" philosophy.

## Safety Boundaries
The following safety boundaries remain absolute and non-negotiable:
- No financial advice generated.
- No trading signals generated.
- No investment recommendations generated.
- No broker logic generated.
- No live trading automation generated.
- No automated order generation.

## Future Exchange Lane
While the Exchange Lane (for cloud-model handoff) is strictly out of scope for the current MVP and implementation, the structured workflow outputs (e.g., Hypothesis Contracts, Risk Checklists) are designed to be serialized. In the future, these standardized artifacts will allow safe, bounded context to be passed to heavier cloud models in the Exchange Lane for advanced processing without exposing sensitive local data or execution capabilities.