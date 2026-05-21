# Product Lane Phase 1: Intake + Scope Lock Plan

Status: Planning only. Do not implement commands from this plan until a separate implementation task is approved.

Date: 2026-05-20

## 1. Objective

Phase 1 adds a deterministic, local-first intake and scope lock workflow on top of the Phase 0 Product Lane registry.

The goal is to help the operator move a product from a basic `product.yaml` record to a reviewable, locked scope without calling models, providers, cloud tools, browser automation, or agents.

Phase 1 should produce:

- static intake questions selected by product type
- durable intake and answer artifacts under `products/<product_id>/`
- deterministic scope draft preview
- explicit scope lock with hash metadata
- product state updates that remain bounded to `products/<product_id>/`
- no-write tests and safe local check coverage

Current Phase 0 source of truth:

- `products/<product_id>/product.yaml`
- `products/<product_id>/action_log.md`
- `scripts/product_registry.py`
- `scripts/ws_product_new.py`
- `scripts/ws_product_list.py`
- `scripts/ws_product_status.py`
- `scripts/ws_product_help.py`
- `registry/ws_command_safety.yaml`
- `WS_COMMAND_SAFETY_MATRIX.md`

## 2. Non-goals

- No product PRD generation.
- No model-backed question generation.
- No local model calls.
- No cloud provider calls.
- No cloud CLI or browser handoff.
- No agent execution.
- No wireframe generation.
- No technical build planning.
- No product-to-stronghold promotion.
- No TUI execution path for guarded writes.
- No direct edit of `scope_lock.md` after lock.
- No new safety taxonomy beyond the manifest classes.

## 3. Phase 1 Command Scope

Plan these commands only:

| Command | Purpose | Phase 1 behavior |
|---|---|---|
| `ws product-intake --dry-run <product_id>` | Preview intake start. | Prints target product, question set, files that would be created, and product.yaml fields that would change. Writes nothing. |
| `ws product-intake <product_id> --confirm` | Start intake. | Creates or refreshes initial `intake.md` and `questions.md`, updates `product.yaml` state to `INTAKE_STARTED`, and appends to `action_log.md`. |
| `ws product-questions --dry-run <product_id>` | Preview the question bank for one product. | Reads `product.yaml` and the static question bank, prints required/optional/blocking/privacy questions. Writes nothing. |
| `ws product-answer-import <product_id> --answers <path> --confirm` | Import operator-written answers. | Validates a local plaintext/markdown answer file, writes `answers.md`, updates `product.yaml`, and appends to `action_log.md`. |
| `ws product-scope --dry-run <product_id>` | Preview scope draft. | Reads product record, intake, questions, and answers. Prints deterministic `scope_draft.md` content and unresolved blockers. Writes nothing. |
| `ws product-lock-scope <product_id> --confirm` | Lock reviewed scope. | Writes `scope_lock.md` exactly once, records `scope_locked_at` and `scope_lock_hash` in `product.yaml`, and appends to `action_log.md`. |

Do not implement:

- `ws product-prd`
- `ws product-wireframe`
- `ws product-build-plan`
- `ws product-handoff`
- `ws product-promote-stronghold`
- model-backed product commands
- provider-backed product commands

## 4. Safety Classification Proposal

Use only the existing manifest safety classes:

- `PURE_READ`
- `LOCAL_REPORT_WRITE`
- `DRY_RUN_ONLY`
- `GUARDED_WRITE`
- `AGENT_RUN`
- `PROVIDER_CALL`
- `DESTRUCTIVE`
- `UNKNOWN`

| Command | Safety class | Writes local files? | Writes project files? | Agent/model? | Provider/cloud? | READ_ONLY_STRICT | SAFE_DRY_RUN | TUI exposure | Confirmation |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `ws product-intake --dry-run` | `DRY_RUN_ONLY` | No | No | No | No | Yes | Yes | Visible or visible_with_label | None |
| `ws product-intake` | `GUARDED_WRITE` | Yes | No | No | No | No | No | Hidden or disabled | Explicit |
| `ws product-questions --dry-run` | `DRY_RUN_ONLY` | No | No | No | No | Yes | Yes | Visible | None |
| `ws product-answer-import` | `GUARDED_WRITE` | Yes | No | No | No | No | No | Hidden or disabled | Explicit |
| `ws product-scope --dry-run` | `DRY_RUN_ONLY` | No | No | No | No | Yes | Yes | Visible or visible_with_label | None |
| `ws product-lock-scope` | `GUARDED_WRITE` | Yes | No | No | No | No | No | Hidden or disabled | Explicit |

Rationale:

- Product intake artifacts are durable product state, not transient local status reports; write commands are `GUARDED_WRITE`, not `LOCAL_REPORT_WRITE`.
- Dry-run commands must not write files, update `product.yaml`, create caches, or append logs.
- Phase 1 v1 uses static question banks and deterministic templates only; no `AGENT_RUN` or `PROVIDER_CALL` commands are introduced.
- `products/<product_id>/` is workstation-local product registry state. It is classified as local files, not project source files, unless a later decision changes the product source-code policy.

## 5. State Transitions

Phase 0 code currently allows `INBOX`, `INTAKE_STARTED`, and `BLOCKED`. Phase 1 should extend the allowed state list in the product registry implementation.

Planned Phase 1 states:

| State | Meaning |
|---|---|
| `INBOX` | Product exists, but intake has not started. |
| `INTAKE_STARTED` | Intake artifacts exist or intake has been started. |
| `CLARIFICATION_NEEDED` | Intake exists, but one or more required/blocking questions are unanswered. |
| `SCOPE_READY` | Required intake content exists and a deterministic scope draft can be produced. |
| `SCOPE_LOCKED` | Scope has been explicitly confirmed and locked. |
| `BLOCKED` | Product cannot proceed until an operator-visible blocker is resolved. |

Allowed transitions:

| From | To | Trigger |
|---|---|---|
| `INBOX` | `INTAKE_STARTED` | `ws product-intake <product_id> --confirm` creates intake/question artifacts. |
| `INTAKE_STARTED` | `CLARIFICATION_NEEDED` | Required or blocking questions remain unresolved after answer import/check. |
| `CLARIFICATION_NEEDED` | `SCOPE_READY` | Required answers and blockers are resolved. |
| `INTAKE_STARTED` | `SCOPE_READY` | Required answers are complete and no blocking questions remain. |
| `SCOPE_READY` | `SCOPE_LOCKED` | `ws product-lock-scope <product_id> --confirm` writes scope lock. |
| Any unlocked state | `BLOCKED` | A validation or operator blocker is recorded. |

Guard rules:

- Cannot lock scope without `intake.md`.
- Cannot lock scope without `answers.md`.
- Cannot lock scope with unresolved required questions.
- Cannot lock scope with unresolved blocking questions.
- Cannot lock scope without explicit operator confirmation.
- Cannot overwrite `scope_lock.md`.
- Cannot directly mutate `scope_lock.md` after lock.
- Scope changes after lock require a future decision/change record, not direct edit.
- Dry-run commands must leave state unchanged.

## 6. Artifact Writes

All Phase 1 artifacts live under `products/<product_id>/`.

| Artifact | Created in Phase 1? | Produced by | Notes |
|---|---:|---|---|
| `intake.md` | Yes | `ws product-intake --confirm` | Human-readable intake shell and product summary. |
| `questions.md` | Yes | `ws product-intake --confirm` | Static question bank rendered for the product type. |
| `answers.md` | Yes | `ws product-answer-import --confirm` | Operator-provided answers copied/normalized from plaintext or markdown input. |
| `scope_draft.md` | Deferred write | Future non-dry-run scope draft command | Phase 1 v1 should start with `ws product-scope --dry-run` only. |
| `scope_lock.md` | Yes | `ws product-lock-scope --confirm` | Immutable locked scope artifact. |
| `decisions/<timestamp>_scope_lock.md` | Deferred | Future decision workflow | Do not create a decisions directory in Phase 1 unless implementation scope is explicitly expanded. |
| `action_log.md` | Existing | Guarded write commands | Append operator-visible history lines. |

Phase 1 should not create:

- product source code
- generated binaries
- large datasets
- raw model outputs
- `.env` files
- credentials or tokens
- raw Graphify outputs

## 7. product.yaml Schema Updates

Planned fields to add or update:

| Field | Type | Purpose |
|---|---|---|
| `state` | string | One of the Phase 1 states. |
| `phase` | string | Suggested value: `phase_1_intake_scope` after intake starts. |
| `intake_started_at` | null/string | Timestamp set by confirmed intake start. |
| `intake_completed_at` | null/string | Timestamp set when required answers are complete. |
| `scope_ready_at` | null/string | Timestamp set when scope can be locked. |
| `scope_locked_at` | null/string | Existing field; set only once by scope lock. |
| `scope_lock_hash` | null/string | Existing field; hash of canonical `scope_lock.md`. |
| `open_questions` | list | Required/optional questions still unresolved. |
| `blockers` | list | Blocking issues preventing scope readiness or lock. |
| `updated_at` | string | Updated by confirmed write commands only. |
| `last_action` | null/string | Last Product Lane command that changed state. |

Compatibility rules:

- Existing Phase 0 products should remain loadable after schema expansion.
- Schema migration should be explicit and tested; do not silently discard fields.
- Dry-run commands must not update any schema fields.
- Unknown future fields should either be preserved or explicitly rejected by schema validation; choose one policy before implementation.

## 8. TUI Future Behavior

Do not implement TUI changes during planning.

Future TUI behavior should be read-first and manifest-backed:

- Product screen or Home card shows product count, active product, state, open required questions, blocker count, and scope lock status.
- Next Safe Action Engine recommends `product-intake --dry-run` for `INBOX` products.
- Next Safe Action Engine recommends answer import or clarification when blockers remain.
- Next Safe Action Engine recommends `product-scope --dry-run` when required answers are complete.
- Scope lock is visible only as guarded/disabled until explicit confirmation UX exists.
- Private product warning is visible for `job-pack`, `cover-letter`, and `interview-prep`.
- No cloud handoff appears in Phase 1.
- TUI rendering must not bypass `registry/ws_command_safety.yaml` or `tui/action_dispatcher.py`.

## 9. Tests

Future no-write tests should use temporary directories and should not execute `ws` routes unless a safe temp-root harness is explicitly designed.

Required tests:

| Test | Expected result |
|---|---|
| Question bank coverage | Every Phase 0 product type has required, optional, blocking, and completion rules. |
| Question IDs stable | Question IDs are unique and deterministic. |
| Missing required answers | Product cannot reach `SCOPE_READY`. |
| Unresolved blocking questions | Product cannot lock scope. |
| Scope draft dry-run | Writes nothing and reports expected generated content. |
| Scope lock hash stability | Same canonical lock content produces same hash. |
| Scope lock immutability | Existing `scope_lock.md` cannot be overwritten. |
| Path traversal guard | Intake, answer import, and lock helpers cannot write outside `products/<product_id>/`. |
| Private content warnings | `job-pack`, `cover-letter`, and `interview-prep` include privacy warning questions. |
| Dry-run no-write | All `--dry-run` commands leave temp tree unchanged. |
| No model/provider calls | Product Phase 1 helpers contain no agent/model/provider subprocess or API paths. |
| Safe local check | `scripts/check_local_safety.py` remains no-write and passes. |

## 10. Safe Local Check Integration

Phase 1 implementation should add focused tests to the existing no-write local check path.

Planned additions:

- `scripts/test_product_intake_questions.py`
- `scripts/test_product_scope_lock.py`
- optional `scripts/test_product_phase1_registry.py` if schema migration logic becomes large

The safe local check must still state and preserve:

- no `ws` command execution
- no agents
- no models
- no providers
- no browser automation
- no apply workflows
- no writes to real workstation state
- only temp-directory writes for tests

Validation command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python scripts\check_local_safety.py
```

## 11. Risks and Mitigations

| Risk | Impact | Mitigation | Detection signal |
|---|---|---|---|
| Intake writes treated as read-only | Unsafe TUI or operator assumptions. | Classify durable artifact writes as `GUARDED_WRITE`. | Manifest validator and safety matrix review. |
| Scope lock can be overwritten | Loss of reviewable commitment. | Refuse overwrite and require future change record workflow. | Scope lock immutability test. |
| Static questions too generic | Weak scope and repeated clarification loops. | Product-type question bank with blocking/privacy questions. | Operator review and missing-answer tests. |
| Private product content leaks into handoff path | Personal material could leave workstation. | No cloud handoff in Phase 1; privacy questions and warnings are required. | Safety matrix and TUI labels. |
| Answer import reads unsafe files | Secret or large data inspection. | Accept only operator-specified markdown/plaintext path with size cap and extension allowlist. | Answer import validation tests. |
| State machine expands without migration policy | Existing products fail to load. | Add explicit schema compatibility tests. | Product registry test failures. |
| TUI exposes guarded writes too early | Operator can trigger mutation without preview/confirmation UX. | Keep guarded commands hidden/disabled in Phase 1. | TUI visibility tests. |

## 12. Implementation Order

1. Add static question bank data and tests.
2. Add Phase 1 state constants and schema validation changes in product registry helpers.
3. Add pure helpers for intake path resolution and artifact rendering.
4. Add no-write tests for question rendering and path boundaries.
5. Implement `ws product-questions --dry-run`.
6. Implement `ws product-intake --dry-run`.
7. Implement guarded `ws product-intake <product_id> --confirm`.
8. Implement guarded answer import helper and `ws product-answer-import`.
9. Add deterministic scope draft renderer and `ws product-scope --dry-run`.
10. Add canonical scope lock renderer/hash helper.
11. Implement guarded `ws product-lock-scope <product_id> --confirm`.
12. Add manifest entries and safety matrix rows for new commands.
13. Update manifest drift and known-command validation only as needed.
14. Add Phase 1 tests to `scripts/check_local_safety.py`.
15. Update operator docs after implementation.
16. Run `scripts/check_local_safety.py`.

## 13. Acceptance Criteria

Phase 1 planning is implementation-ready when:

- The command scope is limited to intake, static questions, answer import, scope dry-run, and scope lock.
- All planned commands use existing safety classes.
- No model, provider, browser, cloud, or agent behavior is planned for Phase 1 v1.
- Durable artifact writes are classified as `GUARDED_WRITE`.
- Dry-run commands write nothing.
- Product state transitions and guards are documented.
- Required artifacts and deferred artifacts are separated.
- Scope lock immutability and hash policy are specified.
- Product-type question coverage exists for all Phase 0 product types.
- Safe local check integration is planned.

## 14. Open Questions

| Question | Current recommendation |
|---|---|
| Should answer import accept external files outside the workstation root? | Allow only explicit operator-specified markdown/plaintext files with size cap; copy normalized content into `products/<product_id>/answers.md`. Final path policy should be decided during implementation. |
| Should `scope_draft.md` be written in Phase 1 or only previewed? | Start with `ws product-scope --dry-run` only. Add durable draft writes later if operators need saved drafts. |
| Should `phase` be a required schema field immediately? | Add as optional/backfilled field first to avoid breaking Phase 0 records. |
| Should scope lock use SHA-256 over markdown bytes or canonical structured fields? | Prefer SHA-256 over normalized UTF-8 markdown bytes for Phase 1; revisit if structured scope artifacts are added. |
| Should guarded writes support `--yes` aliases? | No. Use explicit `--confirm` only. |
