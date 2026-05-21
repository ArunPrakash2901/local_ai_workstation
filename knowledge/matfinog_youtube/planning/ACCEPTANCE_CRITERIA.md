# Acceptance Criteria

## Functional Acceptance Criteria
- [ ] System must allow the user to select from the 7 defined workflows.
- [ ] System must present the correct checklists for the selected workflow.
- [ ] System must block progression until risk-first checklists are completed.
- [ ] System must provide access to search and view the 366 research prompt candidates.
- [ ] System must output research plans in a structured, exportable text format (e.g., Markdown).
- [ ] Human approval must be explicitly recorded before an output is considered "final."

## Safety Acceptance Criteria
- [ ] Outputs must always include the exact text: "No financial advice generated. No trading signals generated. No investment recommendations generated. No broker logic generated. No bot logic generated. No live trading automation generated."
- [ ] Any AI prompt generation must include instructions forbidding trade recommendations.
- [ ] The system must not automatically call any external execution API.

## Documentation Acceptance Criteria
- [ ] Operating model boundaries between AI and Human must be clearly defined and accessible to the user.
- [ ] Workflow steps must be documented internally.

## Reproducibility Acceptance Criteria
- [ ] A generated research plan for a specific input (like a paper title) using the deterministic template must have a consistent structure.
- [ ] Prompt libraries must be fully deterministic and retrieved locally without relying on external LLM vectorization.

## Agent-Behavior Acceptance Criteria
- [ ] An agent acting within this module must refuse requests for buy/sell ratings.
- [ ] An agent must redirect the user to the validation checklist if the user asks for a "profitable strategy."
- [ ] An agent must explicitly identify itself as a research/learning assistant, not a financial advisor.

## Forbidden Behaviors
- **Financial advice:** Prohibited.
- **Trading signals:** Prohibited.
- **Buy/sell/hold recommendations:** Prohibited.
- **Autonomous strategy generation (looping without human input):** Prohibited.
- **Broker integration/live execution:** Prohibited.
- **Live trading automation:** Prohibited.

## Done Checklist
- [x] Planning documents created (Milestone 3A).
- [ ] Phase 1 Prompt Library implemented.
- [ ] Phase 2 Template Generator implemented.
- [ ] Phase 3-5 implemented.
- [ ] Code reviewed against safety policies (`check_local_safety.py`).
