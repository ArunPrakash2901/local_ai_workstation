# Research Report Contract

Discovery Lane accepts phase-wise Deep Research reports as Markdown. Each report should describe one implementation phase.

## Required Or Strongly Expected Sections

- Phase ID
- Phase Title
- Product Context
- Objective
- Scope
- Non-Goals
- Assumptions, if applicable
- User / Operator Workflow
- Functional Requirements
- Technical Requirements
- Architecture Guidance
- Data / File / State Requirements
- UI / UX / Wireframe Guidance, if applicable
- Implementation Tasks
- Suggested Parallel Workstreams, if applicable
- Dependencies
- Risks
- Validation / Test Strategy
- Acceptance Criteria
- Open Questions
- Sources / References, if applicable

## Flexible Heading Equivalents

- `Out of Scope` may satisfy `Non-Goals`.
- `In Scope` may satisfy `Scope`.
- `Success Criteria` may partially satisfy `Acceptance Criteria`.
- `Testing Strategy`, `Validation Plan`, or `Test Strategy` may satisfy `Validation / Test Strategy`.
- `Data Requirements`, `State Requirements`, or `File Requirements` may satisfy `Data / File / State Requirements`.

## Validation Policy

The validator is flexible about exact heading text and strict about meaning. If a report does not clearly provide a section, the generated packet records the gap as `NEEDS_HUMAN_DECISION` or `NOT_EXECUTION_READY`.

The validator never invents requirements from context. Filename or top-heading fallback may be used for identifiers, but those fields are flagged for human review.
