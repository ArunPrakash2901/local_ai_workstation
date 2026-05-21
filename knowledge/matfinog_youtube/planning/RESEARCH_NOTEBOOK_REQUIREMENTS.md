# Research Notebook Requirements

## Purpose
To provide a secure, human-in-the-loop landing pad where learning notes and research prompts from the MatFinOg corpus can be developed into structured hypotheses without accidentally generating trading algorithms or financial advice.

## User Goals
- Translate raw concepts (prompts) into testable hypotheses.
- Define exact data requirements and out-of-sample validation rules *before* any implementation begins.
- Organize research systematically with explicit traceability to the original YouTube video.
- Maintain absolute safety by explicitly disclaiming financial advice and preventing automated execution.

## Required Inputs
- `source_prompt_id`: To trace back to the prompt library.
- `source_workflow_id`: To understand the broader context.
- `source_video_id` / `source_title`: For original human verification.
- `evidence_snippet`: The raw text that sparked the idea.

## Notebook Sections
1. **Notebook Metadata**: ID, timestamps, source tracing, and status.
2. **Research Framing**: Learning objective, restatement, and scope (what is *not* claimed).
3. **Evidence and Source Grounding**: Original quotes and required external literature.
4. **Hypothesis Discipline**: The core research question, testable hypothesis, assumptions, unknowns, and explicit failure conditions.
5. **Validation Plan**: Out-of-sample requirements, robustness checks, and bias mitigation.
6. **Safety Boundary**: Explicit disclaimer against financial advice or live trading.
7. **Next Action**: A strict whitelist of allowed actions (e.g., keep as note, request human review).

## Schema Requirements
- All fields in `research_notebook_schema.yaml` are mandatory.
- The `status` field must strictly adhere to the allowed enum (e.g., `draft_learning_note`, `needs_human_review`). No status can imply a "live" or "approved" trading strategy.
- `forbidden_next_actions` must be explicitly listed to act as a system-level block.

## Safety Requirements
- **No Financial Advice**: Must be stated explicitly.
- **No Trading Signals**: No specific entry/exit prices or recommendations.
- **No Execution**: The notebook cannot authorize backtests or live broker connections.
- **Human Gate**: `human_owner` is required. All state transitions out of "draft" require human approval.

## Acceptance Criteria
- [x] Template markdown file exists.
- [x] Schema YAML exists and enforces fields.
- [x] An example stub exists using a real prompt from the library.
- [x] No UI or execution code is implemented.

## Non-Goals
- Generating code to test the hypothesis.
- Running historical backtests.
- Connecting to data vendors or brokers.
- Creating a graphical UI or web app.

## Future Integration Points
- **Phase 4**: Validation checklists can parse the `Validation Plan` section.
- **Phase 5**: A human-approved notebook can be promoted to the Quant MVP backlog.
- **Milestone 3D**: The read-only CLI browser can render the notebook template for easier viewing.
