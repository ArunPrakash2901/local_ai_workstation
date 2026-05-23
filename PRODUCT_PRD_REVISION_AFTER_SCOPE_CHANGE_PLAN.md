# Product Lane PRD Revision After Scope Change Plan

## 1. Objective

After a product's scope revision is confirmed, the existing Product Requirements Document (PRD) becomes stale because it reflects the older, incomplete, or inaccurate scope. The objective of this plan is to define a safe and auditable workflow for generating a revised PRD. A stale PRD must not be approved and must not be used as the basis for downstream artifacts like wireframes or technical plans until it has been regenerated and re-reviewed against the active revised scope.

## 2. Source-of-Truth Hierarchy

To maintain an immutable audit trail and clear lineage of artifacts, the source-of-truth hierarchy is defined as follows:
- The original `scope_lock.md` remains an immutable historical record.
- The `active_scope_lock` (defined in `product.yaml`) points to the current revised scope artifact.
- The `active_scope_lock_hash` in `product.yaml` is the current hash used for planning and generating downstream artifacts.
- The original `prd.md` becomes a historical/stale artifact until superseded.
- A future PRD revision artifact becomes the active PRD.

## 3. PRD Revision Artifact Policy

When regenerating the PRD, we must preserve the original `prd.md` to maintain the audit trail of what was initially generated. 
- Do not overwrite the original `prd.md`.
- **Recommended Strategy:** Use versioned PRD artifacts stored in a dedicated directory. The revised PRD should be written to `products/<product_id>/prds/prd_v2.md` (and incremented for subsequent revisions). This cleanly separates the active PRD from historical ones while keeping the artifact type obvious.

## 4. Proposed Commands

The following commands are proposed to support the PRD revision workflow. This plan does not implement them.

- `ws product-prd-revision --product <id> --dry-run`: Previews the generation of the new PRD based on the active scope lock, checks for existing active PRDs, and lists metadata updates without writing any files.
- `ws product-prd-revision --product <id> --confirm`: Executes the PRD generation, writes the versioned PRD artifact (e.g., `prds/prd_v2.md`), and updates the product metadata.
- `ws product-prd-review --product <id> --active` (or future equivalent): Reviews the current active PRD against the active scope lock to ensure alignment.
- `ws product-prd-approve --product <id> --confirm`: Formally approves the active PRD. This command may require future adjustments to properly reference active versions over historical ones.
- `ws product-prd-status`: Should eventually report which PRD is active, which PRDs are stale, and the alignment status between the active PRD and the active scope lock.

## 5. Safety Classifications

The new commands must adhere to strict safety classifications using existing classes:
- `product-prd-revision --dry-run`: `DRY_RUN_ONLY`
- `product-prd-revision --confirm`: `GUARDED_WRITE`
- There should be no model, provider, or agent calls in the first implementation (e.g., the command could just stub or use deterministic fallback generation until the full model integration is safe).

## 6. Metadata Policy

The `product.yaml` file must be updated to track the state of PRD revisions. The planned fields include:
- `active_prd`: Path to the currently active PRD artifact.
- `active_prd_hash`: Hash of the currently active PRD artifact.
- `active_prd_revision`: Integer indicating the current revision number.
- `previous_prd`: Path to the previously active PRD artifact.
- `previous_prd_hash`: Hash of the previously active PRD artifact.
- `prd_revision_count`: Total number of times the PRD has been revised.
- `prd_status`: The status of the current active PRD (e.g., `DRAFTED`, `NEEDS_REVISION`, `STALE`, `APPROVED`).
- `prd_created_at` / `prd_revised_at`: Timestamps for creation and revision.
- `prd_reviewed_at`: Timestamp of the last review.
- `prd_approved_at`: Timestamp of the active PRD's approval.
- `stale_artifacts`: List containing paths of artifacts that are no longer valid (e.g., the original `prd.md`).
- `last_action`: Records the last Product Lane action taken.
- `updated_at`: Standard timestamp for the last update to the metadata.

## 7. Staleness Policy

To prevent cascading errors from outdated information, the staleness policy is enforced as follows:
- If the active scope changes, the old PRD immediately becomes `NEEDS_REVISION` or `STALE`.
- If a PRD was already approved, the approval is invalidated if the scope changes after approval.
- Generating or previewing wireframes strictly requires the active PRD to be `APPROVED` and not stale.
- Creating technical plans strictly requires the active PRD to be `APPROVED` and not stale.

## 8. Review/Approval Implications

The review and approval gates must be updated to handle versioned artifacts:
- `product-prd-review` must review the active PRD against the active scope lock.
- `product-prd-approve` must approve the active PRD only.
- The resulting approval record must explicitly include both the `active_scope_lock_hash` and the `active_prd_hash` to bind the approval to specific artifact states.
- The approval command must refuse to process a stale PRD.

## 9. Current Portfolio Recommendation

For the `portfolio-website-redesign` product, which is currently blocked with incomplete source answers and an out-of-scope `TODO/UNKNOWN`, the recommended sequence is:
1. First, implement the `product-scope-revision --confirm` command.
2. Run it on the real `portfolio-website-redesign` product to revise the scope.
3. Then, implement the PRD revision dry-run and confirm commands (`product-prd-revision`).
4. Regenerate the PRD from the newly active revised scope.
5. Rerun the PRD review against the new PRD.
6. Only approve the PRD if the review returns `PASS`.
7. Only then run the wireframe dry-run command.

## 10. Tests Needed Later

Future testing of the implemented commands must verify the following constraints:
- `dry-run` properly uses the `active_scope_lock`, not the original `scope_lock.md`.
- `confirm` successfully writes `prds/prd_v2.md`.
- The original `prd.md` remains completely unchanged.
- `product.yaml` properly updates the `active_prd` field.
- `product.yaml` properly updates the `stale_artifacts` list.
- The review gate explicitly uses the active PRD.
- The approval gate refuses a stale PRD.
- The wireframe generation refuses a stale or unapproved PRD.
- No writes occur outside the specific `products/<product_id>/` directory.
- No model, provider, or agent calls occur during the execution of these first revision implementations.

## 11. Parallel Lane Note

This document was created as a parallel-safe planning task. It intentionally avoided inspecting or modifying any "hot" files (such as `scripts/ws`, `registry/ws_command_safety.yaml`, `WS_COMMAND_SAFETY_MATRIX.md`, `scripts/check_local_safety.py`, or any runtime/session code) that are currently being edited by another concurrent lane working on Runtime Session features. This separation ensures that strategic planning can occur without blocking or colliding with active implementation work.
