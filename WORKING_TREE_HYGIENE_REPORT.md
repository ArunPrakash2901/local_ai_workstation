# Working Tree Hygiene Report

Generated: 2026-05-23

## Summary

This report inventories the current working tree using path-level Git summaries only. It does not inspect private configuration, heavyweight data, model files, raw generated graph outputs, or raw MatFinOg files.

Observed state before writing this report:

| Metric | Count |
| --- | ---: |
| Modified tracked files | 17 |
| Untracked files | 273 |

After this report is created, the expected untracked-file count increases by one unless the report is staged or committed.

Assessment:

- The working tree is broad and multi-lane. It contains Product Lane implementation and real product artifacts, Exchange Lane implementation and smoke-test artifacts, Runtime Session implementation and planned session records, Quant contracts/scripts/reports/tests, Knowledge planning docs, and safety/routing metadata changes.
- It appears safe to continue only with caution. The tree is not clean, and hot safety/routing files are modified.
- A commit should happen before more implementation, but not as one blind all-files commit. The safer strategy is to split commits by lane after a review pass.

## Change Groups by Lane

### Product Lane

Likely Product Lane changes include:

- Modified tracked product metadata/artifacts:
  - `products/portfolio-website-redesign/action_log.md`
  - `products/portfolio-website-redesign/product.yaml`
- Modified tracked Product Lane scripts/tests:
  - `scripts/product_prd.py`
  - `scripts/product_prd_approval.py`
  - `scripts/product_prd_review.py`
  - `scripts/product_prd_status.py`
  - `scripts/product_wireframe.py`
  - `scripts/test_product_prd_approval.py`
  - `scripts/test_product_prd_review.py`
  - `scripts/test_product_prd_status.py`
  - `scripts/test_product_wireframe.py`
  - `scripts/ws_product_prd_review.py`
  - `scripts/ws_product_wireframe.py`
- Untracked Product Lane scripts/tests:
  - `scripts/product_implementation_plan.py`
  - `scripts/product_prd_revision.py`
  - `scripts/product_tech_plan.py`
  - `scripts/product_tech_plan_review.py`
  - `scripts/product_wireframe_review.py`
  - `scripts/test_product_implementation_plan.py`
  - `scripts/test_product_prd_revision.py`
  - `scripts/test_product_prd_revision_confirm.py`
  - `scripts/test_product_tech_plan.py`
  - `scripts/test_product_tech_plan_review.py`
  - `scripts/test_product_wireframe_review.py`
  - `scripts/ws_product_implementation_plan.py`
  - `scripts/ws_product_prd_revision.py`
  - `scripts/ws_product_tech_plan.py`
  - `scripts/ws_product_tech_plan_review.py`
  - `scripts/ws_product_wireframe_review.py`
- Untracked real product artifacts:
  - `products/portfolio-website-redesign/decisions/prd_approval_v2.md`
  - `products/portfolio-website-redesign/prds/prd_v2.md`
  - `products/portfolio-website-redesign/scope_locks/scope_lock_v2.md`
  - `products/portfolio-website-redesign/technical_plans/technical_plan_v1.md`
  - `products/portfolio-website-redesign/wireframes/wireframe_v1.md`
- Planning docs:
  - `PRODUCT_PRD_REVISION_AFTER_SCOPE_CHANGE_PLAN.md`

### Exchange Lane

Likely Exchange Lane changes include:

- Planning and triage docs:
  - `EXCHANGE_IMPORT_PARTIAL_TRIAGE.md`
  - `EXCHANGE_LANE_MASTER_PLAN.md`
- Exchange docs and smoke-test packet artifacts:
  - `exchange/README.md`
  - `exchange/codex-cli-review-review-product-lane-scope-revision-workflow/*`
- Exchange scripts/tests:
  - `scripts/exchange_adapter_preview.py`
  - `scripts/exchange_codex_adapter.py`
  - `scripts/exchange_dispatch.py`
  - `scripts/exchange_registry.py`
  - `scripts/exchange_result_import.py`
  - `scripts/test_exchange_adapter_preview.py`
  - `scripts/test_exchange_cli.py`
  - `scripts/test_exchange_codex_adapter.py`
  - `scripts/test_exchange_dispatch.py`
  - `scripts/test_exchange_registry.py`
  - `scripts/test_exchange_result_import.py`
  - `scripts/test_exchange_session_preview.py`
  - `scripts/ws_exchange_adapter_preview.py`
  - `scripts/ws_exchange_dispatch.py`
  - `scripts/ws_exchange_import_result.py`
  - `scripts/ws_exchange_list.py`
  - `scripts/ws_exchange_new.py`
  - `scripts/ws_exchange_status.py`
- Temporary exchange result:
  - `tmp_exchange_result_review_scope_revision.md`

### Runtime / Sessions

Likely Runtime Session changes include:

- Planning docs:
  - `EXCHANGE_RUNTIME_SESSION_PLAN.md`
- Runtime docs and planned session records:
  - `runtime/README.md`
  - `runtime/sessions/codex-exchange-lane/*`
  - `runtime/sessions/codex-product-lane/*`
  - `runtime/sessions/gemini-product-lane/*`
- Session scripts/tests:
  - `scripts/session_registry.py`
  - `scripts/test_session_cleanup_preview.py`
  - `scripts/test_session_cli.py`
  - `scripts/test_session_plan.py`
  - `scripts/test_session_plan_confirm.py`
  - `scripts/test_session_registry.py`
  - `scripts/test_session_start_preview.py`
  - `scripts/ws_session_cleanup.py`
  - `scripts/ws_session_list.py`
  - `scripts/ws_session_plan.py`
  - `scripts/ws_session_start.py`
  - `scripts/ws_session_status.py`

### Design Adapter

Likely Design Adapter / design-integration planning changes include:

- `OPEN_DESIGN_INTEGRATION_PLAN.md`
- `PRODUCT_DESIGN_ADAPTER_PHASE_0_PLAN.md`
- `PRODUCT_DESIGN_ADAPTER_SPEC.md`

No implementation scripts were identified from the path inventory for this lane beyond the Product Lane wireframe-related scripts already grouped above.

### Knowledge / MatFinOg

Likely Knowledge Lane changes include:

- `KNOWLEDGE_INVENTORY_PHASE_0_PLAN.md`
- `KNOWLEDGE_RAW_DATA_RETENTION_POLICY.md`
- `docs/quant_mvp/MATFINOG_INSPIRED_REQUIREMENTS.md`

No raw files under `knowledge/matfinog_youtube/raw/` are listed as modified or untracked by the inventory. They were not opened.

### Quant

Likely Quant Lane changes are extensive and include:

- Contract schemas/templates under `contracts/quant/`
- Quant MVP docs under `docs/quant_mvp/`
- Quant reports under `reports/quant/`
- Quant implementation scripts under `scripts/quant/`
- Quant tests under `tests/quant/`

This lane is large enough to merit its own review and commit sequence rather than being bundled with Product, Exchange, or Runtime changes.

### Documentation / Reports

Likely documentation/report changes include:

- `LOCAL_AI_WORKSTATION_CURRENT_STATE_AND_NEXT_QUEUE.md`
- `LEARNING_REVIEW_CHECKLIST_STATE_V1.md`
- `LEARNING_TUI_REVIEW_PACKET_VISIBILITY_AUDIT_V1.md`
- `docs/workstation/*`
- `KNOWLEDGE_RAW_DATA_RETENTION_POLICY.md`
- `WORKING_TREE_HYGIENE_REPORT.md`

Some documentation files are lane-specific and should travel with their implementation commit if they describe the same milestone.

### Safety / Registry / Routing

Safety and routing changes are present and should be reviewed before any commit:

- `WS_COMMAND_SAFETY_MATRIX.md`
- `registry/ws_command_safety.yaml`
- `scripts/check_local_safety.py`
- `scripts/ws`

These files are central integration points. They likely span Product, Exchange, Runtime, and Quant route/safety additions, so they may need either a single integration commit after lane commits or careful split commits that keep validation passing.

### Unknown / Needs Review

Needs explicit review before commit:

- `tmp_exchange_result_review_scope_revision.md`: appears to be a temporary smoke-test input. It may not belong in source control unless intentionally retained as evidence.
- `LEARNING_REVIEW_CHECKLIST_STATE_V1.md`, `LEARNING_TUI_REVIEW_PACKET_VISIBILITY_AUDIT_V1.md`, and `scripts/learning_review_checklist_state.py`: likely Learning Lane, which is not one of the current implementation targets and should be reviewed separately.
- Any real generated product, exchange, runtime, and quant report artifacts should be intentionally classified as either durable workstation history or disposable smoke-test output before staging.

## Hot-File Warning

Hot files currently modified:

- `scripts/ws`
- `registry/ws_command_safety.yaml`
- `WS_COMMAND_SAFETY_MATRIX.md`
- `scripts/check_local_safety.py`

Hot files not modified according to `git diff --name-only`:

- `scripts/validate_ws_command_safety.py`
- `scripts/check_ws_manifest_drift.py`
- `scripts/test_tui_action_visibility.py`

Impact:

- Because routing, safety manifest, safety matrix, and local safety gate files are modified, any commit strategy should keep these files synchronized with the lane commands they classify.
- These files should not be committed without running `validate_ws_command_safety.py`, `check_ws_manifest_drift.py`, and `check_local_safety.py` as part of the final commit preparation.

## Commit Recommendation

Recommendation: split into multiple commits by lane.

Suggested sequence:

1. Safety/routing integration baseline: only if it can pass local safety independently, otherwise keep safety/routing changes with each lane commit.
2. Product Lane milestone: Product scripts/tests/docs plus intentional real `portfolio-website-redesign` artifacts.
3. Exchange Lane milestone: Exchange scripts/tests/docs plus intentional exchange smoke-test artifacts.
4. Runtime Session milestone: session scripts/tests/docs plus intentional planned session records.
5. Quant Lane milestone: quant contracts, docs, scripts, tests, and reports after a dedicated review for generated outputs.
6. Knowledge/docs milestone: retention/inventory docs and workstation reports.
7. Learning/unknown milestone: only after reviewing whether these files are intentional.

Do not make one broad commit unless the goal is explicitly to snapshot the entire workstation state. The current tree is too broad for a low-risk single commit.

## Files Not Inspected

The following were not opened:

- Raw transcripts and raw caption/metadata files under `knowledge/matfinog_youtube/raw/`
- Heavyweight data folders
- Private configuration files
- `.env` files
- Credentials, tokens, and secret-like files
- Model files and model weights
- Raw generated Graphify outputs

This report is based on path names, Git status summaries, Git diff summaries, and untracked file lists only.

## Validation

Validation command planned if the repo appears stable:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python scripts\check_local_safety.py
```

Result: PASS.

Notes:

- `check_local_safety.py` completed successfully.
- The command safety manifest validation reported one non-failing warning: `could not locate command matrix section for cross-check`.
- Manifest drift validation reported zero warnings and zero errors.
- No remediation was performed as part of this report.
