# M4-M6 Cleanup Dry Run Inventory - 2026-05-24

## Quarantine Destination
`archive/cleanup_candidates/20260524_M4_M6/`

## Exact Files/Folders Proposed for Quarantine

### Root Transient Reports
- `AGENT_RUN_CHANGED_FILE_REPORT_FIX.md`
- `AGENT_RUN_EXIT_STATE_FIX_REPORT.md`

### Scratch Probe/Test Junk
- `scratch/_probe_*` (1886 items)
- `scratch/_tmp_*` (4 items)
- `scratch/pd_lane_test_*` (1 item)
- `scratch/product_registry_test_*` (1 item)

## Total Count
- Files: 2
- Folders: 1892
- **Total Items**: 1894

## Total Approximate Size
- ~16.4 KB (metadata and small files within test directories)

## Excluded Folders
- `scratch/quant_ideas/`
- `scratch/quant_papers/`
- `scratch/quant_strategy_candidates/`
- `scratch/quant_data_sources/`
- `scratch/quant_data_imports/`
- `scratch/quant_approvals/`
- `reports/quant/`
- `docs/`
- `scripts/`
- `contracts/`
- `tests/`
- `registry/`
- `knowledge/`

## Rejected Cleanup Candidates
- None identified in the allowed patterns.

## Safety Notes
- No files will be deleted.
- All items will be moved to the dated quarantine folder.
- Preservation of relative paths (root items to `root/`, scratch items to `scratch/`).

## Rollback Plan
Items can be moved back to their original locations using the `M4_M6_QUARANTINE_MANIFEST.md` which will be generated after execution.

## Confirmation
- **NO DELETION WILL OCCUR.**
- **READ-ONLY VALIDATION WILL BE RUN POST-CLEANUP.**
