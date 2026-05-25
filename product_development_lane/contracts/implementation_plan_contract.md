# Implementation Plan Contract

An implementation plan is a non-executing planning artifact derived from an approved Discovery Lane execution queue.

## Required Sections

- Phase Mapping
- Workstreams
- Suggested Order
- Dependencies
- Validation Commands / Placeholders
- File-Scope Assumptions
- Risks
- Human Decisions Required

## Rules

- Do not execute worker prompts.
- Do not create or checkout branches.
- Do not commit, push, or merge.
- Preserve `PLANNED_NOT_CREATED` branch status from Discovery Lane branch plans.
- Use `NEEDS_HUMAN_DECISION` when file scope, commands, or implementation order is unclear.

