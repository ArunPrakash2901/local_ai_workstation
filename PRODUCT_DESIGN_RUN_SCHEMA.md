# Product Design Run Schema

This document defines the planned schema for future Open Design run artifacts.
It is a contract/planning file only. It does not imply execution in the current slice.

## Planned Sandbox Layout

`products/<product_id>/design_runs/open_design/<run_id>/`

- `design_input.yaml`
- `design_prompt.md`
- `design_run.yaml`
- `raw_output/`
- `prototype/`
- `screenshots/`
- `export/`
- `validation.md`
- `operator_report.md`

## `design_run.yaml` (Planned Fields)

- `run_id`
- `product_id`
- `tool`
- `tool_version`
- `created_at`
- `status`
- `source_artifacts`:
  - `active_scope_lock`
  - `active_scope_lock_hash`
  - `active_prd`
  - `active_prd_hash`
  - `active_wireframe`
  - `active_wireframe_hash`
  - `active_technical_plan` (optional)
  - `active_technical_plan_hash` (optional)
- `output_paths`
- `allowed_write_root`
- `forbidden_paths`
- `execution_mode`
- `external_calls_policy`
- `validation_status`
- `operator_review_status`

## `design_input.yaml` (Planned Fields)

- product metadata
- design objective
- source summaries
- layout requirements
- page/screen map
- component inventory
- accessibility requirements
- responsive requirements
- explicit non-goals
- sandbox write boundary

## Hash Policy

- Future confirm-mode runs should compute hashes for generated design artifacts.
- `product.yaml` should receive `active_design_*` metadata only after design approval.
- Render preview must not update `product.yaml`.
