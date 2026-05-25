# Safe Cleanup Plan - 2026-05-24

## Cleanup Principles
1. **No Direct Deletion**: No files will be deleted during the automated cleanup phase.
2. **Quarantine First**: All cleanup candidates will be moved to a dated quarantine folder.
3. **Traceability**: A log of all moved files will be maintained.
4. **Human Approval**: The final move action requires explicit human review of the `STALE_FILE_CLASSIFICATION.md`.

## Proposed Quarantine Folder
`archive/cleanup_candidates/20260524/`

## Proposed Actions (Dry Run Only)
The following actions are recommended but **must not be run without explicit confirmation**:

```powershell
# Create quarantine directory
mkdir -p archive/cleanup_candidates/20260524/

# Move scratch probes
mv scratch/_probe_* archive/cleanup_candidates/20260524/

# Move scratch test junk
mv scratch/_tmp_* archive/cleanup_candidates/20260524/
mv scratch/pd_lane_test_* archive/cleanup_candidates/20260524/
mv scratch/product_registry_test_* archive/cleanup_candidates/20260524/
```

## Files Recommended for Human Review
- `_ai_brain/*.md` files in the root (e.g., `AGENT_RUN_...`, `LEARNING_...`).
- `scratch/quant_approvals/` old draft files.

## Files Recommended to Keep
- Everything in `scripts/`, `contracts/`, `tests/`, `registry/`.
- All `reports/quant/` artifacts.
- `docs/` content.

## Files That Must NEVER Be Deleted Automatically
- Any `.py`, `.yaml`, `.json` (except in scratch/tmp), or `.md` files that are part of the core command surface or lineage reports.
- `.git` directory.
- `contracts/` directory.

## Rollback Plan
If a quarantine action causes a failure:
1. Identify the missing file from the quarantine log.
2. Move the file back from `archive/cleanup_candidates/20260524/` to its original location.
3. Update `STALE_FILE_CLASSIFICATION.md` to reclassify the file as "Active".

## Validation Steps After Cleanup
1. Run `python scripts/validate_ws_command_safety.py`.
2. Run `python scripts/check_local_safety.py`.
3. Run `python tests/quant/test_ws_quant_operator_smoke.py`.
4. Run `ws quant status` to verify the command surface remains functional.

## Status Statement
- **NO FILES WERE DELETED** in this milestone.
- Cleanup requires explicit human approval before any move/delete action.
