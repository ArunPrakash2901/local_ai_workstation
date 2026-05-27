# Workstation ID and Path Policy

## Why This Exists

Windows and NTFS path-length constraints can break deep nested artifact writes when IDs and filenames are too verbose.

This policy keeps the MVP spine reliable by using compact IDs and short filenames while preserving full traceability in metadata fields.

## Rules

- IDs must be short enough for nested artifact paths.
- Long human-readable labels belong inside JSON/Markdown content, not filenames.
- Filenames should use compact IDs, not full source descriptions.
- Artifacts must preserve traceability through manifest fields, not filename length.
- Generated names should prefer:
- short prefix
- timestamp
- short hash

The source of truth is metadata inside artifacts, not verbose filenames.

## Naming Pattern

- runtime session: `rt_<short_hash>`
- runtime assignment: `asn_<short_hash>`
- exchange packet: `xp_<short_hash>`
- dispatch plan: `dp_<short_hash>`
- result packet: `res_<short_hash>`
- validation: `val_<short_hash>`
- loop decision: `loop_<short_hash>`
- execution run: `run_<short_hash>`
- worker task packet: `task_<short_hash>`

## Length Targets

- filename stem target: <= 64 characters
- absolute maximum filename stem: <= 96 characters
- full artifact path warning threshold: > 180 characters
- full artifact path hard-fail/shorten threshold: > 220 characters

## Implementation Guidance

- Use compact IDs for filenames and directories.
- Store full semantic context in fields such as:
- `objective`
- `source_artifact_path`
- `source_lane`
- `task_type`
- `phase_id`
- `set_id`
- `operator_notes`
- Keep old artifacts readable; apply compact naming to new writes.
