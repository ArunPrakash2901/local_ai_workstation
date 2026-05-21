# Product Lane Phase 2 PRD Review Plan

Status: planning only. No commands are implemented by this document.

## 1. Objective

Product Lane Phase 2 Slice 3 adds a deterministic PRD review and approval flow after `prd.md` has been created from a locked scope.

The slice should let the operator answer:

- Does `prd.md` exist and match the expected deterministic structure?
- Is it grounded in `scope_lock.md` and `product.yaml`?
- Are critical PRD sections complete enough to proceed?
- Has the operator explicitly approved the PRD for downstream planning?

The first implementation should remain local, deterministic, and bounded to `products/<product_id>/`.

## 2. Non-Goals

- No model-backed PRD review.
- No cloud critique.
- No browser automation.
- No PRD rewrite or overwrite flow.
- No wireframe generation.
- No UX specification generation.
- No technical planning.
- No build planning.
- No TUI Product screen implementation in this slice.
- No implementation work based on the PRD.

## 3. PRD Status Model Decision

Decision: use artifact-level PRD status.

The main product state remains `SCOPE_LOCKED`. Phase 2 Slice 3 should not introduce `PRD_DRAFTED`, `PRD_REVIEWED`, or `PRD_APPROVED` as primary product states.

Rationale:

- Product Lane already keeps the main state stable after `prd.md` creation.
- `product.yaml` already records artifact metadata such as `prd_created_at`.
- PRD review and approval are artifact lifecycle events, not scope lifecycle events.
- Keeping `state: SCOPE_LOCKED` avoids unnecessary state machine expansion before downstream planning is implemented.

Planned `product.yaml` fields:

- `prd_status`: `DRAFTED`, `REVIEWED`, `APPROVED`, or `NEEDS_CHANGES`
- `prd_reviewed_at`
- `prd_approved_at`
- `prd_review_notes`
- `updated_at`
- `last_action`

Initial interpretation:

- `prd_created_at` exists and `prd_status` is missing: treat as `DRAFTED`.
- `prd_status: DRAFTED`: PRD exists but has not been approved.
- `prd_status: REVIEWED`: deterministic review checks have been run and passed, but approval has not happened.
- `prd_status: APPROVED`: operator approved the PRD for downstream planning.
- `prd_status: NEEDS_CHANGES`: deterministic review or operator review found blocking issues.

## 4. Commands To Plan

These commands are planned only. They should not be implemented until this plan is accepted.

| Command | Purpose | Writes files? | Safety class | Notes |
|---|---:|---:|---|---|
| `ws product-prd-review --product <product_id> --dry-run` | Run deterministic PRD review checks and print a review report. | No | `DRY_RUN_ONLY` | No model/provider/agent calls. |
| `ws product-prd-approve --product <product_id> --confirm` | Approve the existing PRD after checks pass. | Yes | `GUARDED_WRITE` | Updates `product.yaml` and writes one approval decision artifact. |
| `ws product-prd-status --product <product_id>` | Show PRD artifact status and metadata. | No | `PURE_READ` | Optional but recommended if implementation remains small. |

Do not plan model-backed review or cloud critique in Slice 3.

## 5. Safety Classification Proposal

Use only the existing workstation safety classes.

| Command | Safety class | Read-only strict | Safe dry-run | Confirmation | Provider/model/agent use |
|---|---|---:|---:|---|---|
| `ws product-prd-review --dry-run` | `DRY_RUN_ONLY` | Yes | Yes | None | No |
| `ws product-prd-approve --confirm` | `GUARDED_WRITE` | No | No | Explicit | No |
| `ws product-prd-status` | `PURE_READ` | Yes | Yes | None | No |

Planned TUI exposure:

- `product-prd-review --dry-run`: hidden or disabled until Product screen exists.
- `product-prd-approve --confirm`: hidden until a guarded Product screen and dispatcher path exists.
- `product-prd-status`: safe to expose later as read-only metadata.

## 6. Deterministic PRD Review Criteria

`ws product-prd-review --dry-run` should require:

- `product.yaml` exists.
- `product_id` is valid.
- Product state is `SCOPE_LOCKED`.
- `scope_lock.md` exists.
- `scope_lock_hash` exists in `product.yaml`.
- `prd.md` exists.
- `prd_created_at` exists or the implementation can explicitly report it as missing.
- No model/provider/agent evidence is required.

The review should verify required PRD sections:

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

The review should also verify:

- `prd.md` has a Generated From section.
- `prd.md` references `scope_lock.md` or `scope_lock_hash`.
- `prd.md` does not contain unresolved `TODO/UNKNOWN` in critical sections unless explicitly allowed.
- Downstream files are not required yet.
- `scope_lock_hash` in `product.yaml` still matches `scope_lock.md` if the existing hash helper is safe to reuse.

Critical sections for `TODO/UNKNOWN` blocking:

- Executive Summary
- Problem Statement
- Target Users / Audience
- Goals
- In Scope
- Requirements
- Success Criteria
- Acceptance Criteria

Non-critical sections may contain `TODO/UNKNOWN` only if the review report calls this out clearly.

## 7. Review Output

The dry-run review report should print:

- Product ID
- Product type
- Current product state
- PRD status
- Scope lock hash
- Required section checklist
- Critical TODO/UNKNOWN findings
- Missing artifact findings
- Pass/fail result
- No-write statement
- No model/provider/agent statement
- Next recommended action

If checks pass:

- Recommend `ws product-prd-approve --product <product_id> --confirm`.

If checks fail:

- Recommend a future guarded PRD revision workflow.
- Do not recommend direct overwrite of `prd.md`.

## 8. Approval Behavior

Planned command:

```powershell
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-prd-approve --product <product_id> --confirm'
```

`ws product-prd-approve --confirm` should:

- Require product state `SCOPE_LOCKED`.
- Require `prd.md` exists.
- Require `scope_lock.md` exists.
- Require `scope_lock_hash` exists.
- Require deterministic review checks to pass.
- Refuse if `prd_status` is already `APPROVED`.
- Not edit `prd.md`.
- Not create wireframes, UX specs, technical plans, or build plans.
- Not call models, providers, agents, or browser automation.

Recommended writes:

- Update `product.yaml`.
- Write `decisions/prd_approval.md`.
- Append `action_log.md` only if the existing action log policy supports it.

Recommended `product.yaml` updates:

- `prd_status: APPROVED`
- `prd_reviewed_at`
- `prd_approved_at`
- `updated_at`
- `last_action: ws product-prd-approve --confirm`
- `prd_review_notes`: short deterministic summary of checks passed

Recommended approval artifact:

- `products/<product_id>/decisions/prd_approval.md`

Reason:

- Approval is a durable operator decision, so it belongs under `decisions/`.
- A separate `reviews/` directory can be deferred until reviews become richer or repeated.
- Writing one decision artifact keeps the write surface small.

## 9. Immutability And Revision Policy

Current policy:

- `prd.md` is not formally immutable.
- `ws product-prd --confirm` refuses overwrite.

Slice 3 policy:

- PRD approval must not edit `prd.md`.
- PRD approval records that the existing PRD artifact is accepted for downstream planning.
- If PRD changes are needed, set or recommend `prd_status: NEEDS_CHANGES`.
- Future slices should add a guarded revision flow rather than direct overwrite.

Future revision flow should likely create:

- `prd_revisions/<timestamp>_prd.md`, or
- `decisions/<timestamp>_prd_change.md`

Do not implement revision handling in Slice 3.

## 10. Future Transition After Approval

After `prd_status: APPROVED`, downstream planning may proceed.

Recommended next commands for later phases:

- `ws product-wireframe --product <product_id> --dry-run` for UI products.
- `ws product-tech-plan --product <product_id> --dry-run` for non-UI products or after UX planning.
- `ws product-build-plan --product <product_id> --dry-run` only after UX and technical planning are stable.

No implementation should start until a future build-plan approval exists.

## 11. Tests Needed

Implementation tests should use temp directories only.

Required tests:

- PRD review dry-run passes for a complete `prd.md`.
- PRD review dry-run fails for missing `prd.md`.
- PRD review detects missing required sections.
- PRD review detects critical `TODO/UNKNOWN`.
- PRD review rejects non-`SCOPE_LOCKED` products.
- PRD review rejects missing `scope_lock.md`.
- PRD review rejects missing `scope_lock_hash`.
- PRD approval refuses if review fails.
- PRD approval refuses duplicate approval.
- PRD approval updates only `product.yaml`, `decisions/prd_approval.md`, and optionally `action_log.md`.
- PRD approval writes nothing outside `products/<product_id>/`.
- PRD approval does not edit `prd.md`.
- PRD approval does not create `wireframes.md`, `ux_spec.md`, `technical_plan.md`, or `build_plan.md`.
- `ws product-prd-status` is pure read if implemented.
- No model/provider/agent usage occurs.
- `check_local_safety.py` remains no-write against real workstation state.

## 12. TUI Impact

No TUI implementation in Slice 3.

Future Product screen should show:

- PRD exists or missing.
- `prd_status`.
- `prd_created_at`.
- `prd_reviewed_at`.
- `prd_approved_at`.
- Next safe action:
  - run PRD review if PRD exists but is not reviewed
  - approve PRD if deterministic review passes
  - plan PRD revision if review fails

Guarded approval should remain hidden or disabled until the TUI dispatcher has a safe confirmation path for Product Lane writes.

## 13. Documentation Impact

Minimal docs to update during implementation:

- `WORKSTATION_MANUAL.md`
- `products/README.md`
- `scripts/ws_product_help.py`

Docs should state:

- `product-prd-review --dry-run` is deterministic and no-write.
- `product-prd-approve --confirm` is guarded and writes approval metadata.
- PRD approval does not edit `prd.md`.
- No models, providers, agents, or browser automation are used.
- PRD revision is future work.

## 14. Implementation Order

1. Add deterministic PRD review helpers.
2. Add `ws product-prd-review --dry-run`.
3. Add PRD approval helpers.
4. Add `ws product-prd-approve --confirm`.
5. Add optional `ws product-prd-status` if small.
6. Add manifest and safety matrix entries.
7. Add temp-root tests.
8. Add safe local check integration.
9. Add minimal docs.
10. Run no-write validation.

## 15. Acceptance Criteria

Phase 2 Slice 3 implementation is acceptable when:

- `ws product-prd-review --dry-run` exists and writes no files.
- `ws product-prd-approve --confirm` exists and is guarded.
- `product.yaml` uses artifact-level PRD status.
- Main product state remains `SCOPE_LOCKED`.
- Approval writes only within `products/<product_id>/`.
- Approval does not edit `prd.md`.
- Approval refuses duplicate approval.
- Review rejects missing required sections and critical unresolved `TODO/UNKNOWN`.
- No model/provider/agent/browser automation paths are used.
- Manifest and safety matrix classify new commands correctly.
- Safe local check passes.

## 16. Open Questions

- Should `prd_status: REVIEWED` be persisted by a dry-run review command, or should only approval persist status? Recommendation: do not persist review status from dry-run.
- Should `decisions/prd_approval.md` be a fixed filename or timestamped? Recommendation: fixed filename in Slice 3, because duplicate approval is refused.
- Should review notes be a string or structured object? Recommendation: start with a short string in `product.yaml` and keep detailed checks in `decisions/prd_approval.md`.
- Should `ws product-prd-status` be implemented in Slice 3? Recommendation: implement only if it remains a thin pure-read helper.
