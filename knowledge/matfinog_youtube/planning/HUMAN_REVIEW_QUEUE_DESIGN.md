# Human Review Queue Design

## Purpose
The Human Review Queue serves as a triage area for high-potential research prompts extracted from the MatFinOg corpus. It ensures that no idea progresses from a mere text prompt to a structured research notebook without explicit human evaluation of its educational value, safety, and relevance.

## Queue Lifecycle
1. **New**: An item is seeded into the queue via deterministic rules (e.g., specific prompt types).
2. **Needs Review**: A human is assigned to evaluate the item.
3. **Reviewed**: A decision has been recorded.
4. **Rejected**: The item is deemed unsafe, irrelevant, or low value.
5. **Archived**: The item is stored for historical purposes but no action is taken.

## Review Decisions
A human reviewer must select from the following allowed decisions:
- `pending`: Default state.
- `keep_learning_note`: Retain as a personal learning artifact.
- `create_research_notebook`: Promote the prompt to a full Research Notebook template.
- `request_more_sources`: The concept is interesting but needs external validation.
- `reject_unsafe_or_irrelevant`: Fails safety checks or doesn't fit goals.
- `future_backlog_candidate`: Valid idea but not for current sprint.

## Prioritization Rules
Items seeded into the queue are prioritized based on their `prompt_type`. Priority is given to:
1. `validation_question`
2. `risk_review_question`
3. `workflow_design_question`
4. `workstation_feature_question`
5. `replication_question`

## Human Responsibilities
- Manually read the `source_title` and `evidence_snippet`.
- Confirm that the prompt contains NO financial advice or trading signals.
- Select an appropriate `review_decision`.
- Provide `safety_notes` confirming the review.

## AI Responsibilities
- AI may assist in formatting the Research Notebook *after* the human decides to `create_research_notebook`.
- AI may *suggest* next actions based on text, but cannot execute them.
- AI must strictly refuse to process any item whose decision is not explicitly authorized by the human.

## Deterministic System Responsibilities
- Seed the queue using strict keyword matching and logic rules (e.g., Python scripts).
- Enforce schema validation on the CSV/JSON data.
- Block the promotion of items if `reviewer` is `HUMAN_REQUIRED`.

## Prohibited Automations
The system MUST NOT:
- Automatically approve trades.
- Automatically generate trading signals.
- Automatically create bots.
- Run live strategies.
- Trigger broker execution.

## Future Integration With Workflow Browser
The forthcoming read-only CLI Workflow Browser (Milestone 3D) will allow users to visualize the `review_status` of prompts and filter the queue interactively without modifying files directly.

## Future Integration With Quant MVP Backlog
Items decided as `create_research_notebook` or `future_backlog_candidate` will serve as the safe, sanitized input layer for Phase 5 (Integration with Quant MVP). This ensures the Quant lane only works on thoroughly vetted, human-approved hypotheses.
