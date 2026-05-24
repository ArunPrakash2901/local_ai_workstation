# Open Design Execution Readiness Audit

## Scope
This audit evaluates whether the workstation is ready to cross from non-executing packet preparation/review into future guarded Open Design render execution.

This audit does not execute Open Design, does not install Open Design, and does not run any coding-agent CLI.

## Current Prepared Run State

Product:
- `portfolio-website-redesign`

Prepared run directory:
- `products/portfolio-website-redesign/design_runs/open_design/open-design-render-v1/`

Prepared packet files currently present:
- `design_input.yaml`
- `design_prompt.md`
- `design_run.yaml`
- `operator_report.md`

Prepared run metadata snapshot (`design_run.yaml`):
- `run_id`: `open-design-render-v1`
- `status`: `PREPARED_NOT_EXECUTED`
- `execution_mode`: `NOT_EXECUTED`
- `allowed_write_root`: `products/portfolio-website-redesign/design_runs/open_design/open-design-render-v1/`
- `forbidden_paths`: `src/`, `app/`, `components/`, `package.json`
- `external_calls_policy`: `NOT_ALLOWED_IN_PREPARE_PHASE`

## Current Review Artifact State

Review directory currently present:
- `products/portfolio-website-redesign/design_runs/open_design/open-design-render-v1/review/`

Review files currently present:
- `design_run_review.html`
- `design_run_review_manifest.json`
- `design_run_review_report.md`

Review surface status:
- Static/local human review surface exists.
- HTML is non-canonical; packet Markdown/YAML remains canonical source.

## Exact Inputs Available For Future Render
- `design_input.yaml`
- `design_prompt.md`
- `design_run.yaml`
- `operator_report.md` (operator context; optional in schema)
- Source artifact references/hashes embedded in `design_run.yaml`:
  - active scope lock path/hash
  - active PRD path/hash
  - active wireframe path/hash
  - active technical plan path/hash (optional context, currently present)

## Not Yet Verified (Execution Boundary Gaps)

Local runtime and installation gaps:
- Open Design executable path certainty: `TO_VERIFY`
- Open Design CLI command contract for this workstation: `TO_VERIFY`
- Node/pnpm/npm version constraints and compatibility: `TO_VERIFY`
- Windows-native vs WSL runtime behavior: `TO_VERIFY`

Execution-control gaps:
- Whether Open Design can be hard-bounded to `allowed_write_root`: `TO_VERIFY`
- Whether writes outside sandbox can be reliably blocked/detected: `TO_VERIFY`
- Whether forbidden paths can be guaranteed (`src/`, `app/`, `components/`, `package.json`): `TO_VERIFY`
- Timeout/cancel handling contract: `TO_VERIFY`
- stdout/stderr capture policy and log retention contract: `TO_VERIFY`

External-call/provider gaps:
- Whether Open Design invokes external providers/services in this setup: `TO_VERIFY`
- Whether Open Design delegates to local coding-agent CLIs during render: `TO_VERIFY`
- BYOK/provider credential behavior and failure modes: `TO_VERIFY`
- Hidden external network path risk under default config: `TO_VERIFY`

Post-render governance gaps:
- Result import and validation policy for raw/prototype/export artifacts: `TO_VERIFY`
- Promotion policy into `product.yaml active_design_*` metadata: `TO_VERIFY`
- Rollback/retry protocol after partial/failing render: `TO_VERIFY`

## Risk Summary
- Uncontrolled writes outside design sandbox.
- Scope drift from approved scope/PRD/wireframe.
- Hidden provider/network calls during render.
- Ambiguous runtime dependency contract on Windows/WSL.
- Missing standardized execution log and timeout policy.

## Readiness Classification
`READY_FOR_LOCAL_INSTALL_EVALUATION`

Rationale:
- Prepared packet and review surface are present and consistent.
- Execution constraints are documented at planning level.
- Runtime/tool/provider behavior for real execution remains unverified.
- Guarded render execution should not be enabled yet.

## Required Next Gate
Complete a no-write runtime probe and finalize guarded execution policy before implementing:
- `ws product-design-render --product <id> --tool open-design --confirm`

Supporting no-write commands for the install-evaluation layer:
- `ws product-design-install-checklist --tool open-design --dry-run`
- `ws product-design-runtime-report --tool open-design --dry-run`
