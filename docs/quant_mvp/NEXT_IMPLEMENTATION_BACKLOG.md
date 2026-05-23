# Next Implementation Backlog (Quant Trading Lane)

This backlog focuses strictly on the safe implementation of the newly integrated research workflows.

*Note: MatFinOg notebook browser work and Exchange Lane work are explicitly excluded.*

---

## 1. Idea Intake Schema
- **Objective:** Create a YAML schema for validating market inefficiency hypothesis inputs.
- **Files Likely Involved:** `contracts/quant/hypothesis_contract_schema.yaml`
- **Dependencies:** None
- **Safety Constraints:** Must not contain executable code or trading logic.
- **Acceptance Criteria:** Schema validates required fields (inefficiency description, duration, data needs).
- **Recommended Agent:** Codex for implementation.

## 2. Market Inefficiency Hypothesis Template
- **Objective:** Provide a human-readable Markdown template corresponding to the schema.
- **Files Likely Involved:** `contracts/quant/hypothesis_template.md`
- **Dependencies:** Idea Intake Schema
- **Safety Constraints:** Must include safety disclaimers.
- **Acceptance Criteria:** Markdown file includes placeholders for all schema fields and a human signature line.
- **Recommended Agent:** Gemini for planning/research.

## 3. Research Paper Replication Template
- **Objective:** Create a structured markdown template for extracting and planning paper replication.
- **Files Likely Involved:** `contracts/quant/paper_replication_template.md`
- **Dependencies:** None
- **Safety Constraints:** Must enforce separation of in-sample claims from out-of-sample testing plans.
- **Acceptance Criteria:** Template includes sections for core claims, mathematical logic, data requirements, and out-of-sample validation steps.
- **Recommended Agent:** Gemini for planning/research.

## 4. Risk Review Checklist
- **Objective:** Implement the mandatory risk-first strategy review checklist.
- **Files Likely Involved:** `contracts/quant/risk_review_checklist.md`
- **Dependencies:** Existing `risk_policy.yaml`
- **Safety Constraints:** Must cover position sizing, drawdowns, and stop-loss logic.
- **Acceptance Criteria:** Checklist requires explicit user input/acknowledgment for 5 core risk categories.
- **Recommended Agent:** Gemini for planning/research.

## 5. Execution Microstructure Checklist
- **Objective:** Implement the microstructure review gate.
- **Files Likely Involved:** `contracts/quant/microstructure_checklist.md`
- **Dependencies:** None
- **Safety Constraints:** Must emphasize that backtests are theoretical.
- **Acceptance Criteria:** Checklist demands assumptions on slippage, spread, and liquidity participation.
- **Recommended Agent:** local model for bounded checks later.

## 6. Strategy Candidate Spec Template Update
- **Objective:** Update the existing strategy spec template to include mandatory links to the hypothesis, risk checklist, and microstructure checklist.
- **Files Likely Involved:** `contracts/quant/strategy_spec_template.md`
- **Dependencies:** Items 1, 4, 5.
- **Safety Constraints:** Retain all existing split-brain boundaries.
- **Acceptance Criteria:** The template cannot be considered 'complete' without references to the upstream research and validation artifacts.
- **Recommended Agent:** Codex for implementation.

## 7. Backtest Manifest Alignment
- **Objective:** Update the backtest manifest template to require an APPROVED strategy spec.
- **Files Likely Involved:** `contracts/quant/experiment_manifest_template.yaml`
- **Dependencies:** Item 6.
- **Safety Constraints:** Must strictly decouple execution from ideation.
- **Acceptance Criteria:** Manifest validation fails if the upstream strategy spec lacks a human approval signature.
- **Recommended Agent:** Codex for implementation.