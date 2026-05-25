# Phase Packet Contract

A phase packet is the bounded local handoff artifact generated from one research report.

## Required Packet Sections

- Phase ID
- Phase Title
- Source Research Report
- Current Status
- Product Context
- Objective
- In Scope
- Out of Scope
- Assumptions
- Human Decisions Required
- Functional Requirements
- Technical Requirements
- Architecture Notes
- Data / State / File Requirements
- UX / Wireframe Notes
- Implementation Plan
- Suggested Parallel Workstreams
- Dependencies
- Risks
- Validation Plan
- Acceptance Criteria
- Execution Boundaries
- Generated Worker Prompt Location
- Manifest Location

## Status Policy

- `READY_FOR_HUMAN_REVIEW`: ready for operator review before execution handoff.
- `NEEDS_HUMAN_DECISION`: requires operator clarification before execution.
- `NOT_EXECUTION_READY`: must not be handed to an execution worker.

## Execution Boundary Policy

Phase packets do not grant permission to modify source code, commit, push, merge, or run external services. Those permissions must be added by a later execution or orchestration lane prompt.

