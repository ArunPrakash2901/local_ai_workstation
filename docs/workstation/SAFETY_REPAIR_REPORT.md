# Workstation Safety Repair Report

## Observed Validation Errors
The `check_local_safety.py` script and `validate_ws_command_safety.py` identified several pre-existing issues in the workstation core logic during the Quant Q29 wrap-up:
1. `ERROR manifest references ws base not found in scripts/ws: ws product-tech-plan`
2. `ERROR manifest references ws base not found in scripts/ws: ws product-wireframe-review`
3. `ERROR: ws product-tech-plan --dry-run: missing fields: warning_label`
4. `FAIL: review status PASS for complete wireframe` (in `test_product_wireframe_review.py`)
5. `FAIL: missing scope_lock_hash should be rejected` (in `test_product_prd_review.py`)
6. `ValueError: active_prd hash mismatch` (in `test_product_prd_approval.py`)
7. `FAIL: preview uses TODO/UNKNOWN for uncertain details` (in `test_product_wireframe.py`)

## Root Cause
- **Manifest Drift:** Commands were defined in `ws_command_safety.yaml` but not registered in the `scripts/ws` router or help sections.
- **Incomplete Metadata:** Some manifest entries lacked the required `warning_label` field introduced in a previous architectural update.
- **Stale Tests:** Several product lane tests were relying on older metadata structures (e.g., missing `active_prd_hash` or `active_scope_lock_hash` in temporary product records) or failing to re-compute hashes after patching files.
- **Render Inconsistency:** The wireframe renderer had stopped outputting `TODO/UNKNOWN` markers for certain navigation and responsive sections, causing safety tests that assert their presence to fail.

## Files Modified
- `registry/ws_command_safety.yaml`: Added missing `warning_label` fields.
- `scripts/ws`: Registered `product-wireframe-review` and `product-tech-plan` subcommands and updated the help section.
- `scripts/product_wireframe_review.py`: Fixed a `NameError` in the precondition validator.
- `scripts/product_prd_review.py`: Fixed logic for retrieving scope lock hashes from the correct metadata version.
- `scripts/product_wireframe.py`: Restored `TODO/UNKNOWN` markers in the wireframe template and corrected markdown header nesting.
- `scripts/test_product_wireframe_review.py`: Fixed metadata setup and added missing `hashlib` import.
- `scripts/test_product_prd_review.py`: Improved metadata cleanup in test case #5.
- `scripts/test_product_prd_approval.py`: Fixed missing `hashlib` import and ensured `active_prd_hash` is refreshed after patching.
- `scripts/test_product_wireframe.py`: Refined test assertions for `TODO/UNKNOWN` presence.
- `scripts/test_product_tech_plan.py`: Updated test setup to ensure wireframes pass the review gate.

## Validation Results
- `python scripts/validate_ws_command_safety.py`: **PASS**
- `python scripts/check_local_safety.py`: **PASS**
- `Quant Regression Tests`: **PASS** (10 test suites, 95 tests total).

## Summary
The workstation core safety validation has been fully restored to a **PASS** state. No changes were made to Quant trading logic. No new product functionality was implemented; the repairs were strictly focused on synchronizing the manifest and fixing brittle test setups. 

It is now safe to proceed to Quant milestone Q30.
