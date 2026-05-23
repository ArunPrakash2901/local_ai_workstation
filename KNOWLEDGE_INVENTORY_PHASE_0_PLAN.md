# Knowledge Inventory Phase 0 Implementation Plan

## 1. Goal
Establish a non-destructive, metadata-only inventory command to audit the `knowledge/` directory, specifically targeting the `matfinog_youtube` dataset. This inventory serves as the foundational "snapshot" required by the `KNOWLEDGE_RAW_DATA_RETENTION_POLICY.md` before any future migration or retention changes.

## 2. Command Specification

| Property | Value |
| --- | --- |
| **Command** | `ws knowledge-inventory` |
| **Target Argument** | `--target <directory_name>` (e.g., `matfinog_youtube`) |
| **Safety Mode** | `--dry-run` (Required for Phase 0) |
| **Safety Classification** | `DRY_RUN_ONLY` |
| **TUI Visibility** | `visible` |

### Proposed Syntax:
```powershell
ws knowledge-inventory --target matfinog_youtube --dry-run
```

## 3. Phase 0 Behavior (No-Write)

Phase 0 is strictly a reporting tool. It MUST NOT write any files, modify Git configuration, or parse the content of raw data files (transcripts/JSON payloads).

### Core Features:
1. **Target Validation**: Verify the existence of `knowledge/<target>/`.
2. **File Counting**: Recursively count files in the target directory.
3. **Extension Grouping**: Report counts and total sizes grouped by file extension (e.g., `.vtt`, `.json`, `.md`).
4. **Size Aggregation**: Report total directory size and average file size.
5. **Outlier Detection**: List the top 10 largest files (names and sizes only).
6. **Folder Classification**: Identify and report the presence of standard subdirectories:
    - `raw/` (Captured data)
    - `processed/` (Cleaned data)
    - `summaries/` (Derived text)
    - `logs/` (Pipeline logs)
7. **Git Tracking Status**: Use `git ls-files --error-unmatch <path>` (safely) to determine if raw files are currently tracked by Git.

### Constraints:
- **No Parsing**: Do not open or read the content of `.vtt` or `.json` files beyond filesystem metadata.
- **No Writes**: Do not create `inventory.json` or any other artifacts in this phase.
- **No Network**: Do not attempt to fetch metadata from external APIs (e.g., YouTube).
- **No Embeddings**: Do not trigger any vectorization or indexing workflows.

## 4. Implementation Strategy

### A. Registry Entry
Add the following to `registry/ws_command_safety.yaml` (Planned, not applied):
```yaml
knowledge-inventory:
  route: knowledge-inventory
  safety_class: DRY_RUN_ONLY
  tui_exposure: visible
  description: "Audit raw knowledge data metadata and Git tracking status."
  allowed_args: ["--target", "--dry-run"]
```

### B. Python Logic (`scripts/ws_knowledge_inventory.py`)
- Use `os.walk` or `pathlib` for metadata gathering.
- Use `subprocess.run(['git', 'ls-files', ...])` for tracking checks.
- Format results into a clean terminal table.

## 5. Test Plan

| Test Case | Description | Expected Outcome |
| --- | --- | --- |
| **Dry-Run Guarantee** | Run with `--dry-run`. | Zero file modifications; Terminal output only. |
| **Metadata Accuracy** | Run on `matfinog_youtube`. | Matches known counts (~564 files) and extensions (vtt, json). |
| **Largest Files** | Verify outlier list. | Lists `.info.json` files correctly. |
| **Missing Target** | Run on non-existent directory. | Graceful error: "Target not found in knowledge/". |
| **Empty Directory** | Run on an empty folder. | Report 0 files, 0 bytes. |
| **Git Status** | Check `raw/` tracking. | Correctly identifies if files are in Git index. |
| **Content Privacy** | Mock a file with "SECRET" content. | Inventory logic does not read or leak content. |
| **Safety Integration** | Run `check_local_safety.py`. | PASS (No manifest drift or AST violations). |

## 6. Safety & Governance Alignment

- **Alignment**: This plan fulfills the "Inventory-first" requirement of `KNOWLEDGE_RAW_DATA_RETENTION_POLICY.md`.
- **Pre-requisite**: This command must be functional and validated before any `ws knowledge-raw-migrate` or `.gitignore` changes are proposed.
- **Phase 1 Preview**: Future phases will implement `--confirm` to write `manifest/inventory.json` containing cryptographic hashes (SHA-256) of each raw file.

## 7. Validation Result (Phase 0 Planning)

Workstation safety check (`scripts/check_local_safety.py`) performed on 2026-05-23: **PASS**.
Inventory scope for `matfinog_youtube`: **~90MB across 564 files**.
Implementation risk: **Zero (No-write)**.
