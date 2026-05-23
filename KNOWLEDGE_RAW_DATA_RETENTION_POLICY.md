# Knowledge Raw Data Retention Policy

## 1. Summary

`knowledge/matfinog_youtube/raw/` appears to contain public YouTube caption and metadata captures for the MatFinOg knowledge pipeline.

Observed inventory, based on names, extensions, counts, and sizes only:

| Area | Value |
| --- | ---: |
| Raw subdirectories | 232 |
| Raw files | 564 |
| `.info.json` files | 232 |
| `.json` total size | 87.89 MB |
| `.vtt` files | 332 |
| `.vtt` total size | 1.58 MB |
| Total raw size observed | 89.47 MB |

The repository audit previously estimated about 93.8 MB, which is consistent with filesystem and reporting differences. The raw files matter because they appear to be grounding sources for downstream MatFinOg summaries, prompt-library material, workflow extraction, and quant-learning research. They also preserve the exact capture state that later processed artifacts may depend on.

## 2. Current Risk Assessment

| Risk | Assessment |
| --- | --- |
| Secret risk | Low based on the prior commit audit and the apparent source type: public YouTube captions and `.info.json` metadata. This policy does not claim every raw field has been reviewed. |
| Repo-weight risk | Real. Raw captures are relatively large for normal source control, and future captures could compound clone size, diff noise, and repository maintenance cost. |
| Reproducibility value | High. Keeping the exact raw captures makes downstream research, prompt-library outputs, and deterministic processing easier to reproduce. |
| Source-of-truth ambiguity | Real. Without an inventory manifest, it is unclear whether Git, a local cache, YouTube, processed outputs, or future external storage is the authoritative source for each capture. |

The existing `knowledge/matfinog_youtube/README.md` says the pipeline downloads public captions/subtitles and video metadata, not video or audio. That supports the low secret-risk assessment, but does not remove the need for careful inventory before migration.

## 3. Retention Options

### A. Keep Raw Files in Git

Benefits:
- Preserves the exact current raw capture with the rest of the workstation.
- Makes processed outputs easier to reproduce without a separate fetch step.
- Avoids immediate history rewrite or migration risk.

Costs:
- Keeps a large raw-data footprint in normal source control.
- Future captures could bloat the repository further.
- Git is not ideal as the long-term storage layer for repeated raw corpus captures.

### B. Move Raw Files Out of Git Later

Benefits:
- Reduces repository size and long-term clone cost.
- Separates source code and deterministic metadata from bulky raw data.
- Allows raw data to move to a cache, archive, object store, or Git LFS-style system later.

Costs:
- Requires careful migration planning.
- History rewrite is risky and should not be done casually after files are already pushed.
- Any downstream scripts or docs that assume raw files are present must be updated deliberately.

### C. Keep Raw Files as Local Cache

Benefits:
- Keeps local reproducibility for the operator while reducing future Git growth.
- Matches the likely behavior of downloaded captions and metadata as rebuildable capture artifacts.
- Supports faster iteration on local knowledge workflows.

Costs:
- Requires a manifest so cache completeness and integrity can be checked.
- New machines need a controlled fetch/rebuild step.
- Local-only files can drift if cache policy is not explicit.

### D. Use Manifest + Rebuild/Fetch Workflow Later

Benefits:
- Makes the source of truth explicit: committed manifest plus verified local cache.
- Allows deterministic inventory, hashes, capture timestamps, URLs/video IDs, and expected output paths.
- Creates a safer foundation for future migration without deleting first.

Costs:
- Requires new commands and tests.
- Rebuild may depend on external availability and YouTube metadata/caption changes.
- Some historical captures may not be perfectly reproducible from upstream sources alone, so backup/archive may still be required.

## 4. Recommendation

Keep the currently committed raw files for now.

Do not rewrite history, delete raw files, or move them out of Git impulsively. The data has reproducibility value, and the immediate safety risk appears low. The repo-weight concern is real, but it should be addressed with an inventory-first migration rather than an ad hoc cleanup.

Before any migration:
- Create a manifest/inventory of the current raw files.
- Include relative path, extension, size, hash, video/source identifier where available, and capture role.
- Create a backup or archive of the current raw tree.
- Add dry-run validation that proves downstream processed artifacts can still be explained.
- Require explicit confirmation before deletion or movement.

For future large raw captures, prefer local cache plus committed manifest. New raw captures should not automatically expand the Git history unless there is a clear reproducibility reason and an explicit retention decision.

## 5. Proposed Future Directory Model

Use `knowledge/matfinog_youtube/` as the stable dataset root:

```text
knowledge/matfinog_youtube/
  manifest/
    raw_inventory_v1.json
    raw_inventory_v1.sha256
    source_manifest_v1.yaml
  processed/
    ...
  summaries/
    ...
  raw/
    ...
```

Policy intent:
- `manifest/` records what raw data exists, where it came from, and how to verify it.
- `processed/` contains deterministic cleaned or derived artifacts.
- `summaries/` contains human- or model-facing summaries when those exist.
- `raw/` remains the local raw capture location, but may later become cache-managed rather than Git-managed.

## 6. Proposed Future Commands

These commands are planning targets only and are not implemented by this policy:

| Command | Mode | Purpose |
| --- | --- | --- |
| `ws knowledge-inventory --dry-run` | No-write | Inspect knowledge raw directories and preview an inventory of counts, sizes, extensions, and candidate manifest records. |
| `ws knowledge-raw-policy --dry-run` | No-write | Evaluate raw-data retention status and recommend whether a directory should remain Git-tracked, become cache-managed, or require migration planning. |
| `ws knowledge-raw-migrate --dry-run` | No-write | Preview a bounded migration plan, including files affected, manifest records, backup target, and downstream validation checks. |
| `ws knowledge-raw-migrate --confirm` | Guarded write | Execute a prevalidated migration only after inventory, backup, dry-run, and explicit operator confirmation. |

Future command rules:
- Do not fetch, delete, or move raw data in inventory/policy dry-runs.
- Do not migrate without a manifest and backup.
- Do not treat external source availability as proof that local historical raw data can be discarded.

## 7. Safety Policy

No deletion or migration of `knowledge/**/raw/` data should occur without:

1. Inventory manifest
2. Backup or archive
3. Dry-run preview
4. Explicit confirmation
5. Post-check validation

Minimum migration preconditions:
- Every candidate file has a recorded relative path, size, and cryptographic hash.
- The migration target is bounded and path-checked.
- Downstream processed artifacts and summaries are either unaffected or explicitly marked stale.
- The operator can distinguish source raw data from processed, summarized, or manually curated artifacts.
- The final report lists files moved, files retained, files ignored, and validation status.

Prohibited without a future guarded command:
- Manual deletion of raw files as cleanup.
- History rewrite to remove raw data.
- Silent `.gitignore` changes that make existing tracked raw files ambiguous.
- Re-fetching or re-indexing as a side effect of policy review.

## 8. Current Decision

Current policy decision:
- Keep current raw files in place.
- Do not modify `.gitignore` in this task.
- Do not delete, move, or edit `knowledge/matfinog_youtube/raw/`.
- Treat future raw captures as candidates for local-cache-plus-manifest handling.
- Implement any migration as a separate, tested, guarded workflow.

