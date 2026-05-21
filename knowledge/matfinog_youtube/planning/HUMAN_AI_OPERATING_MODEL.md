# Human-AI Operating Model

## Overview
This document defines the strict boundaries of responsibility between the human user, the AI assistant, and the deterministic software components within the MatFinOg Workflow Module.

## Human Responsibilities
- Defining the initial research hypothesis.
- Setting explicit risk parameters, stop losses, and drawdown limits.
- Validating all out-of-sample backtest results.
- Executing any code in the backtesting environment.
- Reviewing and approving all AI-generated research plans.
- Maintaining psychological discipline and following the workflow rules.

## AI Responsibilities
- Organizing and presenting relevant research prompts from the library.
- Drafting structural templates for research plans (e.g., formatting a paper replication checklist).
- Highlighting missing elements in a user's hypothesis (e.g., "You have not defined a failure condition").
- Explaining coding concepts or market microstructure theory (educational support).

## Deterministic Software Responsibilities
- Enforcing workflow sequences (e.g., blocking the "Code" step until the "Risk Review" step is completed).
- Appending safety disclaimers to all outputs.
- Logging research activities into local files.
- Searching and filtering the prompt library using keyword matching.

## What AI Can Draft
- Research plan outlines.
- Explanations of academic papers.
- Checklists for validation.
- Template Python code for data processing (if requested by user, completely isolated from broker APIs).

## What AI Cannot Decide
- Asset selection (what to trade).
- Directional bias (buy, sell, hold).
- Sizing or leverage limits.
- When an idea is "ready" to trade.

## Escalation Points
- If the AI detects a request for a trading signal or financial advice, it must immediately escalate to a hard refusal and point the user to this operating model.

## Review Checkpoints
- **Hypothesis Definition:** Human must sign off before moving to validation planning.
- **Validation Planning:** Human must define in-sample/out-of-sample data splits before coding begins.
- **Risk Review:** Human must manually answer all risk questions.

## Prohibited Automations
- AI may not trigger backtests without explicit human request.
- AI may not promote any idea to a strategy autonomously.
- AI may not modify backtest parameters to "optimize" for better historical results without human direction.

## Evidence Requirements
- Any research plan generated must reference the specific workflow pattern or prompt type it is based on (e.g., "Based on execution_microstructure_review_workflow").

## Failure Modes
- If the AI hallucinates financial advice, the deterministic system's safety tags (`safety_financial_advice_generated: false`) act as the final authority, and the output must be flagged/ignored.
- If the user attempts to bypass checkpoints, the deterministic system must prevent state advancement.

## Safety Notice
**No financial advice generated. No trading signals generated. No investment recommendations generated. No broker logic generated. No bot logic generated. No live trading automation generated.**
