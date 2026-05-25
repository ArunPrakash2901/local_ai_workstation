# Stale File Classification - 2026-05-24

## A. Active / Keep
Files actively used by current command surface, tests, contracts, or reports.

| Path | Reason |
| :--- | :--- |
| `scripts/quant/` | Core Quant lane logic. |
| `contracts/quant/` | Schemas and templates for all Quant artifacts. |
| `tests/quant/` | Verification suite for Quant lane. |
| `registry/ws_command_safety.yaml` | Safety policy enforcement. |
| `docs/quant_mvp/QUANT_OPERATOR_CHEATSHEET.md` | Operator reference. |
| `scratch/quant_ideas/` | Source inputs for idea intake. |
| `scratch/quant_papers/` | Source inputs for paper replication. |
| `scratch/quant_approvals/` | Draft approvals and evidence packs. |

## B. Historical / Keep
Old milestone reports and design docs that are useful for traceability.

| Path | Reason |
| :--- | :--- |
| `docs/quant_mvp/Q3_SYNTHESIS_REPORT.md` (and others) | Milestone history. |
| `_ai_brain/EXCHANGE_LANE_MASTER_PLAN.md` | Root record of Exchange lane design. |
| `_ai_brain/LEARNING_ADVANCEMENT_READINESS_PLANNER_V1.md` | Root record of Learning lane state. |

## C. Generated Artifact / Keep
`reports/quant/` artifacts that preserve lineage.

| Path | Reason |
| :--- | :--- |
| `reports/quant/*/*.json` | Deterministic outputs of Quant commands. |
| `reports/quant/*/*.md` | Human-readable versions of Quant reports. |

## D. Scratch Example / Review
Example files under `scratch/` that may be useful but should be reviewed.

| Path | Reason |
| :--- | :--- |
| `scratch/quant_ideas/example_vwap_research_paper_idea.md` | Reference example. |

## E. Candidate Stale / Do Not Delete Yet
Files that appear superseded, duplicated, or no longer referenced.

| Path | Reason | Evidence |
| :--- | :--- | :--- |
| `_ai_brain/AGENT_RUN_CHANGED_FILE_REPORT_FIX.md` | Appears to be a one-off fix report. | File name and content (transient fix). |
| `_ai_brain/AGENT_RUN_EXIT_STATE_FIX_REPORT.md` | Appears to be a one-off fix report. | File name and content (transient fix). |

## F. Safe-to-Quarantine Candidate
Only files that are clearly temporary, duplicate, generated test leftovers, or obsolete failed attempts.

| Path | Reason | Evidence | Risk if Deleted | Recommended Action | Human Decision Required |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scratch/_probe_*` | Temporary probe directories from agent runs. | 2000+ folders with hash-like names. | Minimal; transient agent state. | Quarantine to `archive/cleanup_candidates/`. | No |
| `scratch/_tmp_*` | Temporary test directories. | Folder names start with `_tmp_`. | Minimal; test leftovers. | Quarantine to `archive/cleanup_candidates/`. | No |
| `scratch/pd_lane_test_*` | Temporary PD lane test folders. | Folder names start with `pd_lane_test_`. | Minimal; test leftovers. | Quarantine to `archive/cleanup_candidates/`. | No |
| `scratch/product_registry_test_*` | Temporary product registry test folders. | Folder names start with `product_registry_test_`. | Minimal; test leftovers. | Quarantine to `archive/cleanup_candidates/`. | No |

## G. Unknown / Needs Human Decision
Anything unclear.

| Path | Reason |
| :--- | :--- |
| `_ai_brain/EXCHANGE_IMPORT_PARTIAL_TRIAGE.md` | May be a temporary working file or important history. |
| `_ai_brain/OPEN_DESIGN_INTEGRATION_PLAN.md` | Status of the "Open Design" integration is unknown. |
