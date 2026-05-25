# Repo Context Lane

Bounded, dry-run-first repository intelligence layer for token minimisation using Graphify artifacts.

## v0.8 Status
- Pipeline status reporting and next-step recommendations.
- Freeze readiness reporting.
- Consolidated project discovery across all artifact types.

## Goal
Generate compact repo maps, Graphify run plans, summaries of existing `graph.json` outputs, task-specific context packets, and bounded handoff artifacts so downstream agents have high-signal context without scanning raw project files.

## Workflow
1. `ws repo-context inventory --project <path>`: Shallow directory scan.
2. `ws repo-context graphify-plan --project <path>`: Generate command to build the graph.
3. `ws repo-context graphify-plan-list`: List generated Graphify plans.
4. `ws repo-context graphify-plan-review --plan <path>`: Review plan for safety issues.
5. `ws repo-context graphify-plan-approve --plan <path> --confirm`: Formally approve for execution.
6. `ws repo-context graphify-run --plan <path> --confirm`: Execute approved Graphify plan.
7. `ws repo-context graphify-run-status --plan <path>`: Check execution result.
8. `ws repo-context graphify-intake --run <path>`: Process run results into summaries.
9. `ws repo-context summarize --graph <path>`: (Optional manual) Distill `graph.json` into a readable summary.
10. `ws repo-context status`: Show pipeline status for all projects.
11. `ws repo-context freeze-report`: Generate a formal lane readiness report.
12. `ws repo-context packet --project <id> --task <name>`: Generate context packet from inventory + summary.
13. `ws repo-context packet-list`: List generated packets.
14. `ws repo-context packet-review --packet <path>`: Review packet for safety issues.
15. `ws repo-context packet-approve --packet <path> --confirm`: Formally approve for context use.
16. `ws repo-context handoff --packet <path> --target <target>`: Build a bounded handoff prompt.

## Structure
- `project_inventories/`: Shallow directory/file metadata reports.
- `graphify_plans/`: Proposed Graphify commands and safety checks.
- `graphify_runs/`: Execution logs and manifests for Graphify runs.
- `graphify_intake_reports/`: Records of run result intake and verification.
- `graph_summaries/`: Summaries of existing `graph.json` artifacts.
- `context_packets/`: Compact context for downstream models.
- `handoff/`: Generated Markdown prompts for target agents.
- `handoff_manifests/`: JSON manifests for generated handoffs.
- `review_reports/`: Human review reports for context, plan, run, and intake artifacts.
- `schemas/`: JSON schemas for lane artifacts.
- `tools/`: Implementation tools.

## Doctrine
- Deterministic.
- Human-approved.
- No uncontrolled autonomous execution.
- Dry-run first.
- Local report writes before mutation.
- Graphify execution requires explicit plan approval (`GRAPHIFY_RUN_ONLY`).
- Intake verifies execution results before summarization.
- Status commands recommend the next safe human-guided step.
- Approval is strictly scoped.
- Handoff artifacts are `NOT_EXECUTED` and require manual operator action to send to a model.
