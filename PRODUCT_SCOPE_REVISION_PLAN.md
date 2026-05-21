# Product Lane Answer / Scope Revision Workflow Plan

## Summary

The Product Lane needs a safe way to correct incomplete source answers after a product has already been scope-locked. The triggering case is `portfolio-website-redesign`: the product is `SCOPE_LOCKED`, has `scope_lock.md`, `scope_lock_hash`, and `prd.md`, but `product-prd-review --dry-run` returns `WARN` because `Out of Scope` contains `TODO/UNKNOWN`.

The triage classification is `SOURCE_ANSWERS_INCOMPLETE`. The source answers did not include explicit product-level out-of-scope or non-goal information. The scope lock and PRD correctly preserved that uncertainty, and the PRD review correctly flagged it.

This plan defines a revision workflow. It is a design plan only; no command behavior is implemented here.

## Core Principle

Locked and derived product artifacts must remain auditable.

- Do not directly edit `scope_lock.md` after it exists.
- Do not directly edit `prd.md` after it exists.
- Do not silently overwrite `answers.md`.
- Corrections after lock must create an explicit revision or change record.
- Downstream artifacts derived from stale scope must be marked stale or superseded.
- The main product state can remain `SCOPE_LOCKED`; artifact maturity and staleness should be tracked separately.
- The workflow must be deterministic and operator-controlled.
- The first implementation should not call models, providers, agents, browser automation, or cloud CLIs.

Direct edits are not allowed because they destroy lineage. If an operator changes the answer, the workstation must be able to show what changed, why it changed, when it changed, which prior artifacts were affected, and which future artifacts must be regenerated.

## Revision Model Options

### Option A: Versioned Scope Lock

Keep the original `scope_lock.md` immutable and create a new versioned scope lock, such as `scope_lock_v2.md` or `scope_locks/scope_lock_v2.md`. Add metadata in `product.yaml` that points to the active scope lock version.

Benefits:

- Clear immutable history of scope locks.
- Easy for downstream commands to resolve the active lock.
- Supports future comparison between versions.

Risks:

- If implemented without a prior change record, the reason for the new lock can be weak.
- Operators may treat scope revision as a direct regeneration workflow instead of an approved change workflow.

### Option B: Decision / Change Record First

Keep `scope_lock.md` unchanged. Create an explicit decision record under `decisions/`, such as `decisions/scope_change_<timestamp>.md`. A later command uses approved change records to generate a new versioned scope lock.

Benefits:

- Best audit trail.
- Separates "request a correction" from "regenerate an active locked scope".
- Allows dry-run impact reporting before any mutation.
- Lets the workstation mark stale artifacts before downstream work continues.

Risks:

- Requires two workflow stages instead of one.
- Requires metadata to track pending and applied scope changes.

### Option C: New Clean Product Record

For smoke tests only, abandon the current product record and create a new product record with better source answers.

Benefits:

- Fastest path for downstream testing.
- Avoids building revision workflow before wireframe testing.

Risks:

- Loses the opportunity to validate a real revision workflow.
- Can hide the exact class of failure the Product Lane should handle.
- Not suitable for real products.

## Chosen Model

Use Option B, decision/change record first, for the general Product Lane workflow.

The formal sequence should be:

1. Operator writes or provides a change request file.
2. `product-scope-change --dry-run` validates and reports the impact.
3. `product-scope-change --confirm` records an immutable change decision.
4. `product-scope-revision --dry-run` previews the revised scope lock and stale artifact effects.
5. `product-scope-revision --confirm` creates a new versioned scope lock and updates product metadata.
6. Existing PRD and downstream artifacts are marked stale or superseded.
7. PRD regeneration and approval happen through a later guarded workflow.

For the current smoke-test product, use this same workflow once implemented. Until then, preserve it as a failed-but-useful smoke checkpoint.

## Proposed Commands

### `ws product-scope-change --product <id> --file <change_file> --dry-run`

Purpose:

- Validate a proposed source-answer or scope correction.
- Confirm the product exists and is in a compatible state.
- Parse the change file deterministically.
- Report affected source-answer fields and downstream artifacts.
- Report whether `scope_lock.md`, `prd.md`, wireframes, UX specs, technical plans, or build plans would become stale.

Writes:

- No files.

Safety:

- `DRY_RUN_ONLY`
- `writes_local_files: false`
- `writes_project_files: false`
- `invokes_agent_or_model: false`
- `external_provider_or_cloud: false`
- `read_only_strict: true`
- `read_only_with_local_reports: true`
- `safe_dry_run: true`
- `tui_exposure: hidden`
- `confirmation: none`

### `ws product-scope-change --product <id> --file <change_file> --confirm`

Purpose:

- Record the operator-approved change request as an immutable decision artifact.
- Do not regenerate `scope_lock.md`.
- Do not rewrite `answers.md`.
- Do not rewrite `prd.md`.
- Mark that a scope change is pending revision.

Writes:

- `products/<product_id>/decisions/scope_change_<timestamp>.md`
- `product.yaml` metadata for pending change and staleness status.

Safety:

- `GUARDED_WRITE`
- `writes_local_files: true`
- `writes_project_files: false`
- `invokes_agent_or_model: false`
- `external_provider_or_cloud: false`
- `read_only_strict: false`
- `read_only_with_local_reports: false`
- `safe_dry_run: false`
- `tui_exposure: hidden`
- `confirmation: required`

### `ws product-scope-revision --product <id> --dry-run`

Purpose:

- Preview the revised active scope lock that would be generated from the current active scope and confirmed change records.
- Show a deterministic diff or section-level impact report.
- Show which artifact statuses would change.
- Refuse to proceed if no confirmed pending scope change exists.

Writes:

- No files.

Safety:

- `DRY_RUN_ONLY`
- `writes_local_files: false`
- `writes_project_files: false`
- `invokes_agent_or_model: false`
- `external_provider_or_cloud: false`
- `read_only_strict: true`
- `read_only_with_local_reports: true`
- `safe_dry_run: true`
- `tui_exposure: hidden`
- `confirmation: none`

### `ws product-scope-revision --product <id> --confirm`

Purpose:

- Create a new versioned scope lock from confirmed scope changes.
- Update active scope metadata.
- Mark older derived artifacts stale or superseded.
- Refuse direct overwrite of `scope_lock.md`.
- Do not regenerate PRD in the same command.

Writes:

- `products/<product_id>/scope_locks/scope_lock_v<N>.md`
- `product.yaml` metadata for active scope, revision count, hashes, stale artifacts, and last action.
- Optional `products/<product_id>/staleness.md` if human-readable staleness reporting is needed.

Safety:

- `GUARDED_WRITE`
- `writes_local_files: true`
- `writes_project_files: false`
- `invokes_agent_or_model: false`
- `external_provider_or_cloud: false`
- `read_only_strict: false`
- `read_only_with_local_reports: false`
- `safe_dry_run: false`
- `tui_exposure: hidden`
- `confirmation: required`

## Change File Shape

The change file should be deterministic and operator-authored. It should not be model-generated in the first implementation.

Recommended fields:

- `product_id`
- `reason`
- `source_answer_revision`
- `affected_sections`
- `operator_notes`
- `expected_downstream_effects`

For the portfolio case, the change should explicitly supply product-level out-of-scope or non-goal answers. Examples of fields to resolve include backend/API exclusion, authentication/account exclusion, CMS/blog exclusion, payments/e-commerce exclusion, complex animation exclusion, and private or client-confidential website content exclusion.

The dry-run command should reject ambiguous change files rather than infer missing content.

## Artifact Policy

Use these artifact locations:

- `products/<product_id>/decisions/scope_change_<timestamp>.md` for confirmed change records.
- `products/<product_id>/scope_locks/scope_lock_v<N>.md` for versioned scope locks after revision.
- `products/<product_id>/staleness.md` only if a human-readable staleness report is useful.

Keep `scope_lock.md` as the original immutable lock for legacy compatibility and audit history. New commands should resolve the active scope using `product.yaml`. If no active-scope metadata exists, the active scope defaults to `scope_lock.md`.

Avoid a generic `revisions/` directory for scope locks because the artifact type should be obvious. Use `scope_locks/` for immutable revised locks and `decisions/` for operator decisions.

## `product.yaml` Metadata Plan

Planned fields:

- `active_scope_lock`: path to the active scope lock, defaulting to `scope_lock.md` for legacy records.
- `active_scope_lock_version`: integer, defaulting to `1`.
- `active_scope_lock_hash`: hash of the active scope lock.
- `scope_revision_count`: count of confirmed revised scope locks.
- `scope_change_pending`: boolean.
- `pending_scope_change_ids`: list of confirmed change record identifiers not yet applied to a revised lock.
- `applied_scope_change_ids`: list of change records applied to the active lock.
- `last_scope_change_at`: timestamp of the latest confirmed change decision.
- `last_scope_revision_at`: timestamp of the latest confirmed revised scope lock.
- `prd_status`: may become `NEEDS_REVISION` or `STALE` when scope changes invalidate the current PRD.
- `prd_source_scope_lock`: path or version of the scope lock used to generate the current PRD.
- `prd_source_scope_lock_hash`: hash used to generate the current PRD.
- `stale_artifacts`: list of stale artifacts such as `prd.md`, `wireframes.md`, `ux_spec.md`, or `technical_plan.md`.
- `superseded_artifacts`: optional list of artifacts superseded by a newer active scope.
- `last_action`: latest Product Lane action.
- `updated_at`: latest product metadata update timestamp.

Status usage:

- `DRAFTED`: PRD exists and is tied to the active scope, but not approved.
- `APPROVED`: PRD exists, is tied to the active scope, and approval artifact is current.
- `NEEDS_REVISION`: a confirmed scope change exists but no revised active scope lock has been generated yet.
- `STALE`: the active scope has changed after PRD generation or approval.

## Staleness Policy

If scope changes after `prd.md` exists, the PRD must become stale or needs-revision. The workstation must not let downstream planning continue against stale scope.

Rules:

- A confirmed scope change sets `scope_change_pending: true`.
- A confirmed scope change should set `prd_status: NEEDS_REVISION` if `prd.md` exists.
- A confirmed scope revision should set `prd_status: STALE` if `prd.md` was generated from an older scope lock.
- If `prd_status` was `APPROVED`, the approval becomes stale or superseded when the active scope changes.
- Existing `prd.md` should remain on disk as an auditable artifact, not be overwritten silently.
- Wireframes, UX specs, technical plans, and build plans derived from the stale PRD must be blocked until a regenerated PRD is reviewed and approved.
- Future write-mode commands must refuse to generate downstream artifacts from stale PRDs.

## Review Gate Implications

`product-prd-review` should eventually verify:

- `prd.md` was generated from the active scope lock.
- `prd_source_scope_lock_hash` matches `active_scope_lock_hash`.
- No confirmed pending scope change invalidates the PRD.
- No stale artifact marker applies to `prd.md`.

If stale, `product-prd-review` should return `FAIL` or a hard `WARN` that blocks approval.

`product-prd-approve` should refuse stale PRDs. Approval should require:

- Product state remains `SCOPE_LOCKED`.
- PRD exists.
- PRD review passes.
- PRD is tied to the active scope lock.
- No pending scope change affects PRD-critical sections.

`product-prd-status` should report:

- Active scope lock path and hash.
- PRD source scope lock path and hash.
- Whether the PRD is current, stale, or needs revision.
- Whether an approval artifact is current or superseded.

`product-wireframe` should require:

- `prd_status: APPROVED`
- PRD not stale.
- Approval artifact current.
- PRD source scope hash matches active scope hash.

## Current Smoke-Test Product Recommendation

Recommendation: Option B.

Keep `portfolio-website-redesign` as the real failed smoke checkpoint, then repair it through the formal scope revision workflow after that workflow is implemented.

Reasoning:

- The failure is useful evidence that the review gate catches incomplete source answers.
- Direct edits would weaken the audit model the Product Lane is trying to enforce.
- A clean second smoke product can be created later if downstream wireframe testing is urgent, but it should not replace this failure as the revision-workflow test case.
- Manual discard and recreate should be avoided unless the team explicitly decides the smoke artifact has no ongoing diagnostic value.

## Tests Needed Later

Planned tests should use temporary directories only and must not modify real products.

- `product-scope-change --dry-run` detects affected fields from a change file.
- `product-scope-change --dry-run` writes no files.
- `product-scope-change --confirm` writes only `decisions/scope_change_*.md` and expected `product.yaml` metadata.
- `product-scope-change --confirm` does not modify `answers.md`, `scope_lock.md`, or `prd.md`.
- `product-scope-revision --dry-run` previews a revised scope lock without writing files.
- `product-scope-revision --confirm` refuses direct overwrite of `scope_lock.md`.
- `product-scope-revision --confirm` writes `scope_locks/scope_lock_v<N>.md`.
- Confirmed change marks existing PRD as `NEEDS_REVISION` or `STALE`.
- Scope revision marks PRD approval stale or superseded when applicable.
- `product-prd-review` warns or fails for stale PRDs.
- `product-prd-approve` refuses stale PRDs.
- `product-wireframe` refuses stale or unapproved PRDs.
- No command writes outside `products/<product_id>/`.
- No command invokes models, providers, agents, browser automation, or cloud CLIs.
- `check_local_safety.py` remains safe against real workstation state.

## Implementation Notes For Future Slice

The first implementation should be small and deterministic:

- Add helper-level tests before adding routes.
- Use explicit parser rules for change files.
- Prefer section-level impact reports before full document diffs.
- Keep TUI exposure hidden until the workflow has passed CLI validation.
- Add safety manifest entries before exposing routes.
- Keep confirm commands guarded and require explicit confirmation flags.
- Do not combine scope revision with PRD regeneration in the same command.

## Commands Not Run By This Plan

This plan does not require or authorize:

- `ws product-prd-approve`
- `ws product-wireframe`
- `ws ready`
- product lifecycle write commands
- learning apply workflows
- agents
- models
- providers
- browser automation
- cloud CLIs

