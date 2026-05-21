# Workflow Requirements

## 1. Research Paper to Backtest Workflow
- **Workflow ID:** `research_paper_to_backtest_workflow`
- **Evidence Count:** 42 videos
- **Why it matters:** Provides a structured method to translate academic claims into testable local code without skipping out-of-sample validation.
- **Candidate Workstation Feature:** "Paper to Code" scaffolding wizard.
- **Required Inputs:** Research paper abstract/claims.
- **Expected Outputs:** A step-by-step validation plan and out-of-sample data separation strategy.
- **Human Approval Point:** User must confirm the in-sample/out-of-sample split before proceeding.
- **Safety Rule:** Must output learning plans, not live trading algorithms.
- **Acceptance Criteria:** Successfully generates a validation checklist based on user input.

## 2. Market Inefficiency Hypothesis Workflow
- **Workflow ID:** `market_inefficiency_hypothesis_workflow`
- **Evidence Count:** 56 videos
- **Why it matters:** Encourages identifying structural market reasons for an edge before writing code.
- **Candidate Workstation Feature:** Hypothesis Definition Template.
- **Required Inputs:** Description of the perceived inefficiency.
- **Expected Outputs:** A formatted hypothesis document highlighting data needs and failure conditions.
- **Human Approval Point:** User must approve the failure conditions.
- **Safety Rule:** AI must not confirm if the hypothesis is "profitable."
- **Acceptance Criteria:** Forces user to define "how this edge disappears."

## 3. Risk-First Strategy Review Workflow
- **Workflow ID:** `risk_first_strategy_review_workflow`
- **Evidence Count:** 59 videos
- **Why it matters:** The most prominent workflow in the corpus; ensures capital protection is the primary focus.
- **Candidate Workstation Feature:** Pre-Flight Risk Checklist.
- **Required Inputs:** Proposed research concept.
- **Expected Outputs:** Required stop-loss, drawdown, and tail-risk questions to be answered.
- **Human Approval Point:** User must manually answer risk questions.
- **Safety Rule:** Cannot calculate optimal stop losses; must ask the user to define them.
- **Acceptance Criteria:** Checklist cannot be bypassed.

## 4. Execution Microstructure Review Workflow
- **Workflow ID:** `execution_microstructure_review_workflow`
- **Evidence Count:** 29 videos
- **Why it matters:** Bridges the gap between theoretical backtests and realistic fill mechanics.
- **Candidate Workstation Feature:** Slippage & Spread Impact Estimator (Theoretical).
- **Required Inputs:** Instrument type, assumed spread.
- **Expected Outputs:** A set of prompts challenging the user on volume, liquidity, and VWAP constraints.
- **Human Approval Point:** User confirmation of realistic spread assumptions.
- **Safety Rule:** Must not connect to live order books.
- **Acceptance Criteria:** Generates microstructure review questions.

## 5. AI-Assisted Quant Learning Workflow
- **Workflow ID:** `ai_assisted_quant_learning_workflow`
- **Evidence Count:** 52 videos
- **Why it matters:** Defines safe ways to use LLMs to speed up coding without compromising validation integrity.
- **Candidate Workstation Feature:** Safe Code Assistant Prompt Library.
- **Required Inputs:** Learning objective.
- **Expected Outputs:** Pre-structured prompts that ask the LLM for explanations, not solutions.
- **Human Approval Point:** Selection of the prompt template.
- **Safety Rule:** AI must explicitly refuse to "write a profitable strategy."
- **Acceptance Criteria:** Library contains only educational/structural prompts.

## 6. Workstation Module Candidate Workflow
- **Workflow ID:** `workstation_module_candidate_workflow`
- **Evidence Count:** 56 videos
- **Why it matters:** Identifies fragments that should become core UI components in the future.
- **Candidate Workstation Feature:** Modular Dashboard.
- **Required Inputs:** Workflow selection.
- **Expected Outputs:** Loaded layout of relevant checklists.
- **Human Approval Point:** N/A (UI layout).
- **Safety Rule:** UI must display safety banners prominently.
- **Acceptance Criteria:** Dynamically loads correct components per workflow.

## 7. Psychological Process and Discipline Workflow
- **Workflow ID:** `psychological_process_and_discipline_workflow`
- **Evidence Count:** 18 videos
- **Why it matters:** Emphasizes journaling, rule-following, and removing emotion.
- **Candidate Workstation Feature:** Trade/Research Journal Template.
- **Required Inputs:** Session notes.
- **Expected Outputs:** Tagged, searchable journal entries.
- **Human Approval Point:** Saving the entry.
- **Safety Rule:** N/A (Text logging).
- **Acceptance Criteria:** User can save and retrieve process logs.

## Safety Notice
**No financial advice generated. No trading signals generated. No investment recommendations generated. No broker logic generated. No bot logic generated. No live trading automation generated.**
