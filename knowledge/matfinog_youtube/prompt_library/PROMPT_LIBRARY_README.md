# Prompt Library

## Overview
This Prompt Library contains 366 deterministic, source-grounded research prompts extracted from the MatFinOg YouTube corpus. It is designed to act as the foundational data layer for the Quant Research Workflow Coach module.

## Generation
This library was generated deterministically from `knowledge\matfinog_youtube\processed\research_prompt_candidates.jsonl`.
No LLMs, vector databases, or external APIs were used in the generation of these records. The text was extracted directly from transcript boundaries using predefined regex and semantic matching rules defined in `workflow_taxonomy.yaml`.

## Source Artifacts Used
- `knowledge\matfinog_youtube\processed\research_prompt_candidates.jsonl`
- `knowledge\matfinog_youtube\processed\workflow_index.csv`
- `knowledge\matfinog_youtube\processed\topic_index.csv`

## Allowed Usage
- Browsing safe, structured research questions.
- Identifying validation and risk management checks for quantitative hypotheses.
- Sourcing learning prompts that point directly back to MatFinOg YouTube videos for human review.
- Planning future Quant MVP features.

## Forbidden Usage
- **NO Financial Advice:** Do not use these prompts to generate financial advice.
- **NO Trading Signals:** Do not use these prompts to determine what to buy or sell.
- **NO Bot Logic:** Do not use these prompts to generate live execution logic or broker routing code.
- **NO Live Trading Automation:** Do not connect any output of these prompts to live markets.

## Safety Constraints
Every record in `prompt_library.jsonl` contains the following flags explicitly set to `false`:
- `safety_financial_advice_generated: false`
- `safety_trading_signal_generated: false`
- `safety_bot_logic_generated: false`
- `safety_live_trading_logic_generated: false`

## Connection to Future Modules
- **Workflow Browser:** This library will serve as the read-only data source for a future Workflow Browser UI, enabling the human researcher to filter prompts by topic and workflow.
- **Quant MVP:** Selected prompts can be exported to a Research Notebook Template, guiding the human user to explicitly define in-sample/out-of-sample splits, risk parameters, and data sources *before* any implementation begins.
