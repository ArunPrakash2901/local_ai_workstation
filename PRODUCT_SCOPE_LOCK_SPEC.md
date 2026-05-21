# Product Scope Lock Spec

Status: Phase 1 planning. No command implementation in this document.

## Purpose

`scope_lock.md` is the reviewed commitment artifact for a Product Lane product. It captures what the operator has agreed to build or produce before later phases create PRDs, wireframes, technical plans, handoffs, or implementation tasks.

Scope lock is a guarded product-state mutation. It must be explicit, reviewable, and immutable after creation.

## Planned Command

| Command | Safety class | Confirmation | Notes |
|---|---|---|---|
| `ws product-lock-scope <product_id> --confirm` | `GUARDED_WRITE` | Explicit | Writes `scope_lock.md`, updates `product.yaml`, and appends to `action_log.md`. |
| `ws product-scope --dry-run <product_id>` | `DRY_RUN_ONLY` | None | Prints deterministic scope draft content and blockers. Writes nothing. |

Phase 1 v1 does not use agents, local models, providers, cloud CLIs, or browser automation for scope drafting or lock.

## scope_lock.md Template

```markdown
# Product Scope Lock: <label>

Product ID: <product_id>
Product Type: <product_type>
Private: <true|false>
Locked At: <iso_timestamp>
Scope Lock Hash: <sha256_hash>

## Goal

<one or two paragraphs describing the product outcome>

## Target User / Audience

<who this product is for>

## In Scope

- <included outcome, artifact, workflow, page, feature, or content item>

## Out of Scope

- <explicit non-goal or deferred item>

## Constraints

- <technical, privacy, time, platform, design, data, or content constraint>

## Assumptions

- <assumption used to lock scope>

## Dependencies

- <required input, asset, data source, approval, or external dependency>

## Privacy Level

<privacy stance and any private data restrictions>

## Success Criteria

- <observable result that makes the product acceptable>

## Explicit Non-Goals

- <non-goal repeated from out-of-scope if important enough to prevent drift>

## Generated From

- product.yaml
- intake.md
- questions.md
- answers.md
- ws product-scope --dry-run output reviewed by operator

## Open Questions At Lock

- None, or explicitly accepted non-blocking open question.

## Operator Confirmation

I confirm that this scope is accurate for Product Lane Phase 1 and that later changes require a separate scope change decision. I understand this command writes durable files under products/<product_id>/ and does not run agents, models, providers, browser automation, or cloud handoffs.
```

Implementation note: the hash line should be blank or set to a placeholder while computing the hash, then filled after canonicalization. The exact canonicalization function must be deterministic and tested.

## Hash and Staleness Policy

Recommended Phase 1 policy:

- Use SHA-256.
- Hash normalized UTF-8 markdown content for `scope_lock.md`.
- Normalize line endings to `\n`.
- Trim trailing whitespace on each line before hashing.
- Exclude the `Scope Lock Hash:` line from the hash input, or set it to a fixed placeholder before hashing.
- Store the resulting hash in both `scope_lock.md` and `product.yaml.scope_lock_hash`.
- Set `product.yaml.scope_locked_at` to the same timestamp shown in `scope_lock.md`.

Staleness rules:

| Condition | Status | Operator implication |
|---|---|---|
| `scope_lock.md` missing and product state is `SCOPE_LOCKED` | Invalid | Product status should report a blocker. |
| `product.yaml.scope_lock_hash` missing after lock | Invalid | Product status should report a blocker. |
| Hash of current `scope_lock.md` differs from `product.yaml.scope_lock_hash` | Stale/tampered | Do not proceed to PRD/build phases; require future scope change decision. |
| `answers.md` updated after `scope_locked_at` | Stale inputs | Require future scope change decision before downstream artifacts. |
| `intake.md` updated after `scope_locked_at` | Stale inputs | Require future scope change decision before downstream artifacts. |

Phase 1 should detect obvious staleness but does not need to implement a full downstream artifact lineage system.

## Immutability Rule

`scope_lock.md` is write-once in Phase 1.

Rules:

- `ws product-lock-scope` must refuse to overwrite existing `scope_lock.md`.
- `ws product-lock-scope` must refuse if `product.yaml.scope_locked_at` or `scope_lock_hash` is already set.
- Direct scope changes after lock are not supported.
- A future phase may introduce `ws product-scope-change --dry-run` and guarded scope change decision records.

## Operator Confirmation Language

The command should require `--confirm` and print a clear preview before writing.

Suggested confirmation text:

```text
This will lock scope for <product_id>.
It will write products/<product_id>/scope_lock.md, update product.yaml, and append action_log.md.
It will not run agents, models, providers, browser automation, or cloud handoffs.
After lock, scope_lock.md cannot be overwritten by Phase 1 commands.
Re-run with --confirm only after reviewing the dry-run output.
```

Do not add a `--yes` alias in Phase 1.

## Scope Change Policy

Phase 1 does not implement scope changes after lock.

If scope needs to change:

- Do not edit `scope_lock.md` directly.
- Record the issue as a blocker or open question in `product.yaml` only through a future guarded command.
- Plan a later `scope_change` decision artifact that references the original hash.
- Downstream PRD/build phases should treat hash mismatch as blocked.

## Lock Preconditions

`ws product-lock-scope` must refuse to lock when:

- product does not exist
- product state is not `SCOPE_READY`
- `intake.md` is missing
- `questions.md` is missing
- `answers.md` is missing
- required questions are unanswered
- blocking questions are unresolved
- `scope_lock.md` already exists
- `scope_locked_at` is already set
- `scope_lock_hash` is already set
- product path resolution would escape `products/<product_id>/`
- the product type is unknown

Private products must include a privacy warning in the dry-run output and scope lock text.

## Tests Needed

| Test | Expected result |
|---|---|
| Scope draft render is deterministic | Same inputs produce same markdown. |
| Scope hash is stable | Same canonical lock content produces same SHA-256. |
| Hash excludes hash line correctly | Re-rendering with the stored hash validates. |
| Lock preconditions enforced | Missing intake, questions, answers, or required answers block lock. |
| Blocking questions enforced | Unresolved blocking question blocks lock. |
| Lock writes only under product dir | No write outside `products/<product_id>/`. |
| Existing lock refused | Existing `scope_lock.md` or lock metadata blocks overwrite. |
| Private warning present | Private/default-private products show warning text. |
| Dry-run writes nothing | `ws product-scope --dry-run` leaves temp tree unchanged. |
| No agent/provider/model path | Phase 1 scope helpers do not import or invoke agent/model/provider tooling. |

## Open Questions

| Question | Current recommendation |
|---|---|
| Should `scope_lock.md` include a machine-readable front matter block? | Defer. Plain markdown plus `product.yaml` metadata is enough for Phase 1. |
| Should accepted non-blocking open questions be allowed at lock? | Allow only if explicitly listed under `Open Questions At Lock` and not marked blocking. |
| Should `scope_draft.md` be persisted before lock? | Defer. Start with dry-run output to avoid extra mutable artifacts. |
