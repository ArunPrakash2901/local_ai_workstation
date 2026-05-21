# Product Lane Phase 0 Implementation Plan

## 1. Objective

Build the smallest useful Product Development Lane foundation:

- Create a local product registry under `products/`.
- Define a durable `product.yaml` schema.
- Add registry helpers for safe path resolution, slug validation, schema validation, listing, and status reads.
- Implement only `ws product-new`, `ws product-list`, and `ws product-status`.
- Add command safety metadata and no-write validation coverage.

Phase 0 should prove the registry and safety model without introducing intake, PRD generation, model calls, cloud handoffs, or apply workflows.

## 2. Non-goals

- Do not extend the stronghold state machine.
- Do not implement product intake or brief import.
- Do not implement PRD generation.
- Do not implement scope lock or artifact apply flows.
- Do not implement local model calls.
- Do not implement provider/cloud/browser handoffs.
- Do not add Figma, Excalidraw, or other design-tool integrations.
- Do not expose product creation as an executable TUI action unless guarded-write UX is explicitly implemented.
- Do not introduce a second safety taxonomy.

## 3. Files/directories to create

Planned implementation files:

| Path | Purpose |
|---|---|
| `products/` | Product registry root. |
| `products/<product_id>/product.yaml` | Product source of truth. |
| `products/<product_id>/action_log.md` | Append-only human-readable history for product registry events. |
| `scripts/ws_product_registry.py` | Product registry helpers and schema validation. |
| `scripts/ws_product_new.py` or `scripts/ws_product_new.sh` | CLI implementation for `ws product-new`. |
| `scripts/ws_product_list.py` or `scripts/ws_product_list.sh` | CLI implementation for `ws product-list`. |
| `scripts/ws_product_status.py` or `scripts/ws_product_status.sh` | CLI implementation for `ws product-status`. |
| `scripts/test_product_registry.py` | No-write/unit-style product registry validation using temp directories. |

Existing files to update during implementation:

| Path | Planned change |
|---|---|
| `scripts/ws` | Add routes for `product-new`, `product-list`, and `product-status` only. |
| `registry/ws_command_safety.yaml` | Add three command entries using manifest safety classes. |
| `WS_COMMAND_SAFETY_MATRIX.md` | Add matching human safety matrix rows. |
| `scripts/check_ws_manifest_drift.py` | No logic change expected; should pass once manifest covers new routes. |
| `scripts/validate_ws_command_safety.py` | Add known-command checks only if useful. |
| `scripts/check_local_safety.py` | Add `scripts/test_product_registry.py` to the no-write check path. |
| `tui/app.py` | Optional small read-only product list/status readout only if low risk. |
| `tui/README.md` or `WORKSTATION_MANUAL.md` | Minimal command documentation after implementation. |

## 4. Product registry schema

`product.yaml` v0:

```yaml
schema_version: 0
product_id: example-product
title: Example Product
type: app
state: DRAFT
private: false
created_at: "2026-05-20T00:00:00Z"
updated_at: "2026-05-20T00:00:00Z"
summary: ""
owner: operator
source:
  created_by: ws product-new
links: []
promotion:
  stronghold_id: null
  promoted_at: null
```

Required fields:

| Field | Rule |
|---|---|
| `schema_version` | Integer, initially `0`. |
| `product_id` | Slug matching `^[a-z0-9][a-z0-9-]{1,80}$`. |
| `title` | Non-empty string. |
| `type` | Non-empty string from an initial allowlist. |
| `state` | One of Product state machine v0 values. |
| `private` | Boolean. Defaults to `true` for `job-pack`, `cover-letter`, and `interview-prep`; otherwise defaults to `false` unless specified. |
| `created_at` | ISO-like timestamp string. |
| `updated_at` | ISO-like timestamp string. |
| `summary` | String, may be empty. |
| `owner` | String, defaults to `operator`. |
| `source` | Mapping with creation metadata. |
| `links` | List of reference links only; no external tool integration. |
| `promotion` | Mapping reserved for later stronghold promotion metadata. |

Initial product type allowlist:

| Type | Notes |
|---|---|
| `app` | General software product. |
| `site` | Website or web experience. |
| `tool` | Local tool or utility. |
| `content` | General content product. |
| `job-pack` | Private by default. |
| `cover-letter` | Private by default. |
| `interview-prep` | Private by default. |
| `other` | Explicit fallback when type is not yet modeled. |

## 5. Product state machine v0

Phase 0 state values:

| State | Meaning | Allowed transitions in Phase 0 |
|---|---|---|
| `DRAFT` | Product exists but has not gone through intake or scope lock. | Initial state only. |
| `PAUSED` | Product is intentionally inactive. | Not implemented by command in Phase 0. |
| `ARCHIVED` | Product is retained but no longer active. | Not implemented by command in Phase 0. |

Phase 0 does not implement state transitions beyond initial creation. Later phases may add `INTAKE_READY`, `SCOPE_LOCKED`, `PRD_READY`, or promotion states, but those are explicitly out of scope until the registry is stable.

## 6. Commands to implement

| Command | Purpose | Expected behavior |
|---|---|---|
| `ws product-new --title "<title>" [--type <type>] [--id <product_id>] [--private true|false]` | Create a product registry entry. | Validate slug and schema, create `products/<product_id>/product.yaml`, create `action_log.md`, refuse overwrite unless a future explicit flag is designed. |
| `ws product-list` | List products. | Read `products/*/product.yaml`, summarize id/title/type/state/private/updated timestamp, handle empty registry calmly. |
| `ws product-status <product_id>` | Show one product. | Read only that product's `product.yaml` and print status; missing product exits non-zero with clear message. |

## 7. Commands explicitly not implemented

| Command or capability | Reason deferred |
|---|---|
| `ws product-intake` | Phase 1; requires intake artifact model. |
| `ws product-intake-import` | Phase 1; requires import validation and mutation policy. |
| `ws product-prd` | Later; requires PRD artifact schema and likely dry-run/report classification. |
| `ws product-scope-lock` | Later; requires explicit confirmation and diff/preview UX. |
| `ws product-wireframe` | Later; v1 should be text/ASCII only. |
| `ws product-handoff` | Later; privacy, redaction, and provider confirmation model required. |
| `ws product-promote-stronghold` | Later; depends on product-to-stronghold promotion design. |
| Model-backed product generation | Later; would be `AGENT_RUN` or local model classified behavior. |
| Cloud/provider product execution | Later; would require `PROVIDER_CALL` classification and explicit confirmation. |

## 8. TUI changes

Phase 0 TUI scope is optional and read-only:

- If small and safe, add a product list/status readout to an existing screen.
- The TUI may display `product-list` and `product-status` information only after their manifest entries exist.
- The TUI must not execute `product-new` by default.
- If `product-new` appears in the TUI, it must be disabled or hidden until guarded-write confirmation UX is designed.
- Rendering changes must not bypass `registry/ws_command_safety.yaml`, `tui/next_action.py`, or `tui/action_dispatcher.py` gates.

## 9. Safety classification for each new command

| Command | Safety class | Writes local files? | Writes project files? | Model/provider use? | READ_ONLY_STRICT | SAFE_DRY_RUN | TUI exposure | Confirmation |
|---|---|---:|---:|---|---:|---:|---|---|
| `ws product-list` | `PURE_READ` | No | No | No | Yes | Yes | `visible` if readout is added | `none` |
| `ws product-status` | `PURE_READ` | No | No | No | Yes | Yes | `visible` if readout is added | `none` |
| `ws product-new` | `GUARDED_WRITE` | Yes | No | No | No | No | `hidden` or `disabled` in Phase 0 | `explicit` |

`ws product-new` creates product registry files, so it must not be classified as `PURE_READ`. It is also not `LOCAL_REPORT_WRITE` because it creates durable product state rather than a bounded status/report artifact.

## 10. Tests

Add no-write tests that use temporary directories and do not execute workstation commands:

| Test | Expected result |
|---|---|
| Product schema validation | Valid schema passes; missing required fields fail. |
| Product id slug validation | Invalid ids are rejected. |
| No write outside `products/<product_id>` | Path traversal and absolute target attempts are rejected under a fake temp registry root. |
| `product-list` empty registry | Returns an empty/calm result without crashing. |
| `product-status` missing product | Fails safely with a clear message. |
| Private defaults | `job-pack`, `cover-letter`, and `interview-prep` default to `private: true`. |
| Manifest drift after route addition | `scripts/check_ws_manifest_drift.py` passes after routes and manifest entries are added. |
| Safe local check | `scripts/check_local_safety.py` passes. |

No test should run `ws`, agents, models, providers, browser automation, or apply workflows.

## 11. Safe local check integration

After implementing `scripts/test_product_registry.py`, update `scripts/check_local_safety.py` to include it in the no-write validation path.

The resulting safe local check should still state and preserve:

- no `ws` commands
- no agents
- no models
- no providers
- no browser automation
- no apply flows
- no reports/caches/artifacts written by the check itself

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python scripts\check_local_safety.py
```

## 12. Rollback plan

If Phase 0 implementation fails validation:

- Remove the three `product-*` routes from `scripts/ws`.
- Remove product command entries from `registry/ws_command_safety.yaml`.
- Remove matching rows from `WS_COMMAND_SAFETY_MATRIX.md`.
- Remove product registry helper and product command scripts.
- Remove product registry tests from `scripts/check_local_safety.py`.
- Leave existing products only if explicitly created during manual testing; automated tests must use temp directories.

No rollback step should use destructive git reset or discard unrelated user changes.

## 13. Acceptance criteria

Phase 0 is acceptable when:

- `products/` exists or is created by the first guarded product creation path.
- `product.yaml` schema v0 is documented and validated.
- `ws product-new`, `ws product-list`, and `ws product-status` are the only new product routes.
- `ws product-list` and `ws product-status` are `PURE_READ`.
- `ws product-new` is `GUARDED_WRITE` with explicit confirmation if exposed.
- Manifest entries exist for all three commands.
- Human safety matrix rows match the manifest.
- Product registry tests pass without writing outside temp directories.
- `scripts/check_ws_manifest_drift.py` passes after route addition.
- `scripts/check_local_safety.py` passes.
- No agent/model/provider/browser/apply behavior is introduced.
- Existing READ_ONLY and SAFE_DRY_RUN behavior remains unchanged.

## 14. Implementation order

1. Add product registry helper module with schema, slug validation, and safe path resolution.
2. Add no-write product registry tests using temp directories.
3. Add `product-list` and `product-status` scripts against the helper.
4. Add `product-new` script with explicit creation semantics and no overwrite behavior.
5. Add `scripts/ws` routes and help text for only the three Phase 0 commands.
6. Add manifest entries using `PURE_READ` for list/status and `GUARDED_WRITE` for new.
7. Add matching rows to `WS_COMMAND_SAFETY_MATRIX.md`.
8. Update manifest validation known-command checks only if it adds useful regression value.
9. Update `scripts/check_local_safety.py` to run product registry tests.
10. Optionally add a small read-only product readout to the TUI after command metadata exists.
11. Run the safe local check with `PYTHONDONTWRITEBYTECODE=1`.

