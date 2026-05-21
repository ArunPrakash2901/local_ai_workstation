# Product Lane Decision Record

Status: Accepted for Phase 0 planning.

Date: 2026-05-20

## Context

This decision record resolves the Product Development Lane open questions before Phase 0 implementation. The expected primary input, `PRODUCT_DEVELOPMENT_LANE_MASTER_PLAN.md`, was not present at the project root and was not found by title search for "Product Development Lane" across markdown files inspected during this review. This record therefore uses the requested open questions plus repository evidence from:

- `PRD_LOCAL_AI_WORKSTATION.md`
- `WS_COMMAND_SAFETY_MATRIX.md`
- `registry/ws_command_safety.yaml`
- `scripts/check_local_safety.py`
- `scripts/ws`
- `tui/next_action.py`
- `tui/action_dispatcher.py`
- `tui/app.py`
- `WORKSTATION_MANUAL.md`
- `tui/README.md`
- `prompts/product_builder.md`
- `strongholds/product/local-ai-workstation-control-plane/state.json`

Relevant current evidence:

- `scripts/ws` has no `product-new`, `product-list`, or `product-status` routes today.
- `WORKSTATION_MANUAL.md` documents generic product strongholds through `ws stronghold-new --type product`, not a separate product registry.
- `strongholds/product/local-ai-workstation-control-plane/state.json` shows an existing product-type stronghold in `INTAKE_IN_PROGRESS`.
- `registry/ws_command_safety.yaml` is the command safety metadata source used by the TUI for labels and action visibility.
- `tui/action_dispatcher.py` blocks `UNKNOWN`, `PROVIDER_CALL`, `DESTRUCTIVE`, `GUARDED_WRITE`, and `AGENT_RUN` classes from default TUI execution.
- `scripts/check_local_safety.py` is the no-write verification path for manifest, TUI visibility, manifest drift, next-action, and dispatcher tests.

## Decisions

| Question | Decision | Rationale | Phase 0 impact |
|---|---|---|---|
| Q1 - Product vs stronghold relationship | Products start in a separate registry under `products/`. Products may later be promoted to strongholds. Do not extend the stronghold state machine in Phase 0. | The existing generic stronghold system already supports `product`, but the proposed Product Lane needs a lighter product registry before it has enough state to become a durable stronghold. Keeping it separate avoids coupling early product intake/status work to the mature stronghold state machine. | Create `products/<product_id>/product.yaml` as the Product Lane source of truth. Do not modify stronghold states or stronghold commands. |
| Q2 - Artifact write confirmation UX | Scope lock requires explicit confirmation and diff/preview. Other artifact writes use preview plus summary in early phases. TUI exposure of `--apply` commands remains guarded. | The workstation safety model distinguishes dry-run/report writes from guarded mutation. Scope lock is a semantic commitment and should not happen invisibly. | Phase 0 does not implement scope lock. Future scope lock must be `GUARDED_WRITE` with explicit confirmation and preview. |
| Q3 - Multi-session products | `product-status` and `product.yaml` are the source of truth. `action_log.md` records history. No special multi-session system in Phase 0. | The workstation already relies on simple durable files and state artifacts. A session system would add ceremony before the product registry model is proven. | Phase 0 product commands read `product.yaml`; `product-new` may append initial history to `action_log.md`. |
| Q4 - Intake import vs interactive | Phase 0 supports `product-new`, `product-status`, and `product-list` only. Phase 1 supports interactive intake. Import brief can be planned, not built in Phase 0. | `scripts/ws` already has several intake/import patterns for strongholds and learning. Product Lane should first establish safe registry semantics before adding more artifact mutation. | No intake commands, no imported briefs, no model calls, and no generated PRD artifacts in Phase 0. |
| Q5 - Wireframe tool | Text/ASCII wireframes only in v1. External links are allowed as references. No Figma or Excalidraw integration in v1. | External design-tool integration adds provider, browser, and artifact synchronization risk. Text wireframes are locally reviewable and fit the existing artifact model. | Phase 0 does not implement wireframes. Later wireframe artifacts should stay local markdown/plain text unless explicitly classified. |
| Q6 - Privacy model for content products | Add `private: true` default for `job-pack`, `cover-letter`, and `interview-prep`. Cloud handoff for private products requires explicit warning and confirmation. Do not implement cloud handoff in Phase 0. | Content products may contain personal employment material. The workstation principle is local-first before cloud escalation. | Phase 0 schema includes `private`. Product types with personal content default to private. No cloud handoff commands are added. |
| Q7 - Safety class alignment | Product Lane command design must use the manifest safety classes: `PURE_READ`, `LOCAL_REPORT_WRITE`, `DRY_RUN_ONLY`, `GUARDED_WRITE`, `AGENT_RUN`, `PROVIDER_CALL`, `DESTRUCTIVE`, `UNKNOWN`. Do not introduce a second safety taxonomy. | The safety matrix, manifest, TUI visibility helpers, drift check, and dispatcher already use this taxonomy. A separate `READ_ONLY` / `SAFE` / `GUARDED` vocabulary would create policy drift. | Phase 0 command planning and future manifest entries must use the manifest safety classes directly. |

## Consequences

- `products/` becomes the Product Lane registry root.
- Product Lane is not a replacement for strongholds. It is a lighter registry that can later feed or promote into stronghold workflows.
- `ws product-new` is not read-only. It creates product files and must be classified as `GUARDED_WRITE` unless implementation semantics change to preview-only.
- `ws product-list` and `ws product-status` are intended as `PURE_READ`.
- No model, provider, browser, or cloud handoff behavior belongs in Phase 0.
- No TUI execution path for product creation should be added until the dispatcher has an explicit guarded-write UX for confirmation and preview.

## Deferred Questions

| Topic | Deferred decision |
|---|---|
| Product-to-stronghold promotion | Define after several products exist and the registry schema stabilizes. |
| Scope lock schema | Define with artifact preview/diff UX in a later phase. |
| Product intake import | Phase 1 design item. |
| PRD generation | Not in Phase 0; likely local-first and dry-run/report-backed when introduced. |
| Cloud handoff for private products | Not in Phase 0; requires provider warning, redaction policy, and explicit confirmation. |
| TUI product creation | Keep disabled/CLI-only until guarded-write dispatch UX is designed and tested. |

## Implementation Gate

Phase 0 implementation may start only if it preserves these constraints:

- No new provider calls.
- No new agent/model invocations.
- No cloud/browser handoff execution.
- No stronghold state-machine extension.
- No TUI bypass of existing manifest and dispatcher safety gates.
- `scripts/check_local_safety.py` must pass after implementation.

