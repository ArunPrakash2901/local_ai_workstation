# Product Design Render Confirm Plan (Not Implemented)

## Scope
This document defines the implementation plan for a future guarded command:

- `ws product-design-render --product <id> --tool open-design --confirm`

This is a planning artifact only. Execution mode is not implemented in this slice.

## Proposed Safety Boundary (Interim)
- Provisional class: `PROVIDER_CALL` until runtime/provider behavior is verified.
- Reclassification to `GUARDED_WRITE` is allowed only if fully local execution is proven with no provider/agent delegation and no external calls.

## Preconditions (Must All Pass)

Product/readiness gates:
- Valid product id and supported tool (`open-design`).
- UI-capable product type (`website`, `webapp`, `dashboard`).
- `prd_status == APPROVED`.
- Active scope file exists and hash matches product metadata.
- Active PRD file exists and hash matches product metadata.
- Active wireframe file exists and hash matches product metadata.
- Deterministic wireframe review status is `PASS`.

Prepared packet gates:
- Prepared run directory exists:
  - `products/<product_id>/design_runs/open_design/open-design-render-v1/`
- Required packet files exist and parse:
  - `design_input.yaml`
  - `design_prompt.md`
  - `design_run.yaml`
- `design_run.yaml` must indicate:
  - `status: PREPARED_NOT_EXECUTED`
  - `execution_mode: NOT_EXECUTED`
  - bounded `allowed_write_root` in expected sandbox
  - required forbidden path protections

Review gate:
- Review surface has been generated and reviewed by human operator.
- Latest review status must be `PASS` or explicit operator override recorded.

Runtime probe gate:
- `ws product-design-runtime-probe --tool open-design --dry-run` completed.
- Probe result must not be `RUNTIME_NOT_FOUND`.
- Final go/no-go remains human decision (probe is advisory only).

## Execution Policy (Future Confirm)

Allowed write root:
- `products/<product_id>/design_runs/open_design/open-design-render-v1/`

Forbidden paths:
- `src/`
- `app/`
- `components/`
- `package.json`

Execution process controls:
- Run with explicit timeout.
- Capture stdout/stderr to sandbox-scoped logs.
- No automatic browser open.
- No implicit install/update/clone steps inside confirm flow.

Provider/agent controls:
- Detect and log whether external provider or local agent CLI is invoked.
- Block if execution mode violates configured policy.
- Explicitly declare BYOK requirements before run.

## Timeout and Cancel Policy (Planned)
- Default timeout budget: deterministic fixed value configured in command.
- On timeout:
  - mark run state as timed out (without promoting artifacts),
  - keep partial output isolated under sandbox,
  - require human triage before retry.
- Operator cancel must be recorded as non-success completion.

## stdout/stderr Capture Policy (Planned)
- Capture to sandbox-scoped logs inside run directory.
- Preserve original output for audit.
- Redaction policy to be defined before any provider call path is enabled.

## Result Folder Policy (Planned)
- Render output, if produced, stays inside:
  - `raw_output/`
  - `prototype/`
  - `screenshots/`
  - `export/`
- No app/source repository writes.
- No output promotion outside sandbox during render confirm.

## Post-Render Validation (Planned)
- Validate outputs stayed within `allowed_write_root`.
- Validate forbidden paths unchanged.
- Validate required output artifacts presence/shape.
- Emit deterministic render validation report.
- Require human review checkpoint before any metadata promotion.

## product.yaml Update Policy (Planned)
- `product.yaml active_design_*` metadata is not updated by render start.
- Promotion to active design metadata occurs only after:
  - render validation pass,
  - explicit human approval,
  - deterministic metadata write command (separate slice).

## Rollback/Retry Policy (Planned)
- Never delete prepared packet files.
- Failed render retains artifacts for audit.
- Retry only by explicit operator action with updated status trail.

## Human Approval Checkpoints (Planned)
1. Pre-execution approval: runtime + packet + review gate.
2. Post-execution approval: render output quality/safety check.
3. Promotion approval: any active design metadata update.

## Not Implemented In This Plan
- Direct render execution.
- Auto-approval or auto-promotion.
- Branch creation/checkout/merge.
- App/source code generation workflows.
