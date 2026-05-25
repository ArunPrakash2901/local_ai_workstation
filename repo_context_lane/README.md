# Repo Context Lane

Bounded, dry-run-first repository intelligence layer for token minimisation using Graphify artifacts.

## v0.3 Status
- Formal context packet review and approval metadata.
- Approval scope limited to `CONTEXT_ONLY`.
- Audit validation of approval signatures.

## Goal
Generate compact repo maps, Graphify run plans, summaries of existing `graph.json` outputs, and task-specific context packets so downstream agents have bounded, high-signal context without scanning raw project files.

## Workflow
1. `ws repo-context inventory --project <path>`: Shallow directory scan.
2. `ws repo-context graphify-plan --project <path>`: Generate command to build the graph.
3. (External) Run `graphify`: Build the actual `graph.json`.
4. `ws repo-context summarize --graph <path>`: Distill `graph.json` into a readable summary.
5. `ws repo-context packet --project <id> --task <name>`: Generate context packet from inventory + summary.
6. `ws repo-context packet-list`: List generated packets.
7. `ws repo-context packet-review --packet <path>`: Review packet for safety issues.
8. `ws repo-context packet-approve --packet <path> --confirm`: Formally approve for context use.

## Structure
- `project_inventories/`: Shallow directory/file metadata reports.
- `graphify_plans/`: Proposed Graphify commands and safety checks.
- `graph_summaries/`: Summaries of existing `graph.json` artifacts.
- `context_packets/`: Compact context for downstream models.
- `review_reports/`: Human review reports for context artifacts.
- `schemas/`: JSON schemas for lane artifacts.
- `tools/`: Implementation tools.

## Doctrine
- Deterministic.
- Human-approved.
- No uncontrolled autonomous execution.
- Dry-run first.
- Local report writes before mutation.
- No Graphify execution in v0.1/v0.2/v0.3.
- Approval is strictly `CONTEXT_ONLY`.
