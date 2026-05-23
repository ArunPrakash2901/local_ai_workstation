# MatFinOg-Inspired Workstation Requirements

## Overview
These requirements translate the quantitative research workflows extracted from the MatFinOg corpus into structured, enforceable features within the Quant Trading Workstation.

---

## 1. Market Inefficiency Hypothesis Builder
- **Requirement ID:** REQ-MF-001
- **Source Workflow:** `market_inefficiency_hypothesis_workflow`
- **Evidence Count:** 56 videos
- **User Need:** A structured way to document and refine market structure observations into testable hypotheses before writing code.
- **System Behavior:** Provides a template requiring the user to define the inefficiency, the expected duration, the market participants involved, and the required data.
- **Human Checkpoint:** The user must manually approve the completed Hypothesis Contract.
- **Safety Rule:** The system cannot suggest specific assets to target.
- **Acceptance Criteria:** A valid `hypothesis_contract.yaml` is generated and marked 'APPROVED' by the user.

---

## 2. Research Paper Replication Scaffold
- **Requirement ID:** REQ-MF-002
- **Source Workflow:** `research_paper_to_backtest_workflow`
- **Evidence Count:** 42 videos
- **User Need:** A guided process to extract claims from academic papers and structure out-of-sample tests.
- **System Behavior:** Prompts the user to identify core claims, assumptions, mathematical formulas, and data requirements from a paper, generating a step-by-step replication plan.
- **Human Checkpoint:** The user must verify the extracted logic against the source material.
- **Safety Rule:** AI cannot guarantee the profitability of the paper's claims.
- **Acceptance Criteria:** A `replication_plan.md` document is successfully generated, separating in-sample assertions from out-of-sample test requirements.

---

## 3. Risk-First Strategy Review
- **Requirement ID:** REQ-MF-003
- **Source Workflow:** `risk_first_strategy_review_workflow`
- **Evidence Count:** 59 videos
- **User Need:** Ensure risk management is considered fundamentally, not as an afterthought.
- **System Behavior:** A mandatory checklist that blocks progression to backtesting until position sizing limits, stop-loss mechanisms, and draw-down tolerances are explicitly defined.
- **Human Checkpoint:** The user must sign off on every risk parameter.
- **Safety Rule:** System must reject any specification lacking defined risk constraints.
- **Acceptance Criteria:** The backtest engine cannot be invoked unless a completed `risk_review_checklist.md` is attached to the strategy manifest.

---

## 4. Execution / Microstructure Review
- **Requirement ID:** REQ-MF-004
- **Source Workflow:** `execution_microstructure_review_workflow`
- **Evidence Count:** 29 videos
- **User Need:** Prevent naive backtesting by forcing consideration of real-world trading costs and mechanics.
- **System Behavior:** Prompts the user to define expected slippage, spread assumptions, volume participation limits, and fill-rate expectations.
- **Human Checkpoint:** User must acknowledge the microstructure constraints.
- **Safety Rule:** Must explicitly state that backtest results are theoretical and highly sensitive to these parameters.
- **Acceptance Criteria:** The generated strategy specification includes a distinct `microstructure_assumptions` block.

---

## 5. AI-Assisted Research Workflow
- **Requirement ID:** REQ-MF-005
- **Source Workflow:** `ai_assisted_quant_learning_workflow`
- **Evidence Count:** 52 videos
- **User Need:** Accelerate the boilerplate and structural organization of research without relinquishing control.
- **System Behavior:** AI assists in expanding prompts, structuring documents, and organizing the `Human Review Queue`.
- **Human Checkpoint:** All AI-generated research outputs must pass through the Human Review Queue before being accepted as canonical project files.
- **Safety Rule:** AI outputs must be flagged as `safety_financial_advice_generated: false`.
- **Acceptance Criteria:** AI can generate draft markdown files, but they remain in a 'draft' state until human intervention.

---

## 6. Workstation Learning Loop
- **Requirement ID:** REQ-MF-006
- **Source Workflow:** `psychological_process_and_discipline_workflow`
- **Evidence Count:** 18 videos
- **User Need:** Maintain a disciplined approach to research and paper trading.
- **System Behavior:** Enforces journaling and post-trade/post-backtest review memos.
- **Human Checkpoint:** User completes periodic review reflections.
- **Safety Rule:** Reflections must not be altered by the AI.
- **Acceptance Criteria:** A standardized `post_review_memo.md` template is available and trackable.