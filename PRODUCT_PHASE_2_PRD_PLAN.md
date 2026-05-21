# Product Lane Phase 2 PRD Plan

Status: planning only. Phase 2 Slice 1 preview and Phase 2 Slice 2 guarded write are implemented; remaining slices are review/critique/wireframes.

## Objective

Add `ws product-prd --dry-run` as a deterministic preview path that turns a locked product scope into a structured PRD draft without writing `prd.md` or mutating product state.

## Non-Goals

- No `prd.md` writing in Slice 1
- No PRD review/approval workflow
- No model-assisted PRD generation or critique
- No cloud critique or browser automation
- No wireframes, UX spec, technical plan, or build plan generation
- No TUI Product screen changes in this slice

## PRD Output Sections

Phase 2 Slice 1 preview output should include:

- Executive Summary
- Problem Statement
- Target Users / Audience
- Goals
- Non-Goals
- In Scope
- Out of Scope
- Requirements
- Constraints
- Dependencies
- Success Criteria
- Risks and Mitigations
- Acceptance Criteria
- Generated From
- Next Step

## Safety Class Proposal

Use the existing workstation safety classes only.

Recommended classification:

- `ws product-prd --dry-run`: `DRY_RUN_ONLY`
- `writes_local_files`: `false`
- `writes_project_files`: `false`
- `invokes_agent_or_model`: `false`
- `external_provider_or_cloud`: `false`
- `read_only_strict`: `true`
- `read_only_with_local_reports`: `true`
- `safe_dry_run`: `true`
- `tui_exposure`: `hidden`
- `confirmation`: `none`

## No-Write Guarantee

Slice 1 must only preview PRD content from `product.yaml` and `scope_lock.md`.
It must not write `prd.md`, update `product.yaml`, or invoke any model, provider, or agent path.

## Future Slices

- PRD review and approval flow
- model-assisted PRD critique
- wireframes and user-flow planning
- downstream planning artifact generation
