# Manual Dataset Import Template

**Import ID:** {IMPORT_ID}
**Linked Decision ID:** {LINKED_DATA_SOURCE_DECISION_ID}
**Date Created:** {CREATED_AT}
**Status:** {IMPORT_STATUS}

---

## Safety Boundary
**WARNING:** This document validates a local dataset metadata. **No data has been downloaded by the system, this does not approve backtesting, and this does not approve a strategy or trading.**

Safety Flags:
- Data Downloaded By System: FALSE
- Financial Advice Generated: FALSE
- Trading Signal Generated: FALSE
- Bot Logic Generated: FALSE
- Live Trading Logic Generated: FALSE

---

## 1. File Metadata
- **Source File Path:** {SOURCE_FILE_PATH}
- **File Exists:** {FILE_EXISTS}
- **File Size (Bytes):** {FILE_SIZE_BYTES}
- **File Format:** {FILE_FORMAT}
- **Row Count:** {ROW_COUNT}
- **Column Names:** {COLUMN_NAMES}

## 2. Validation
- **Required Columns Present:** {REQUIRED_COLUMNS_PRESENT}
- **Missing Required Columns:** {MISSING_REQUIRED_COLUMNS}
- **Schema Validation Status:** {SCHEMA_VALIDATION_STATUS}
- **Synthetic Fixture:** {SYNTHETIC_FIXTURE}
- **Human Provided:** {HUMAN_PROVIDED}

## 3. Analysis
- **Data Quality Checks Required:** {DATA_QUALITY_CHECKS}
- **Known Gaps:** {KNOWN_GAPS}

---
## Human Review Checkpoint
- [ ] I confirm this dataset is valid for future backtesting.
