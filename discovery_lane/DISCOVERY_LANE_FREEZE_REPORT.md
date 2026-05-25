# Discovery Lane Freeze Report

Current implemented version: v1.7

Discovery Lane is frozen as a complete non-executing handoff system. It starts only after phase-wise Deep Research Markdown reports already exist and ends at `READY_FOR_EXECUTION_LANE` execution queue manifests.

## Lifecycle Boundary

```text
manual Deep Research .md reports
-> intake-set
-> ingest-set
-> approve-set --dry-run
-> VS Code review
-> approve individual packet
-> handoff bundle
-> branch plan
-> queue-plan
-> READY_FOR_EXECUTION_LANE
-> future Execution Lane
```

Discovery Lane approval does not mean execution approval.

Discovery Lane queue planning does not create branches.

Discovery Lane queue planning does not run worker prompts.

Discovery Lane ends at `READY_FOR_EXECUTION_LANE` queue manifests.

## What Discovery Lane Does

- Accepts already-created phase-wise Markdown research reports.
- Validates research report structure.
- Validates complete research sets.
- Generates deterministic phase packets.
- Generates bounded worker prompts.
- Records human approval or rejection of individual packets.
- Creates immutable handoff bundles for approved packets.
- Creates planned branch metadata without touching git branches.
- Builds non-executing execution queue manifests and reports.
- Audits Discovery Lane structure and safety boundaries.

## What Discovery Lane Does Not Do

- It does not handle vague ideas.
- It does not ask discovery questions.
- It does not standardize prompts.
- It does not run Deep Research.
- It does not browse the web.
- It does not call ChatGPT, Gemini, Codex, local models, APIs, or providers.
- It does not execute worker prompts.
- It does not create, checkout, push, merge, or delete git branches.
- It does not commit code.
- It does not approve packets automatically.

## Operator Workflow

1. Manually create phase-wise Deep Research reports in ChatGPT/Gemini.
2. Save reports as `.md` files.
3. Place reports under `discovery_lane/inbox/<set_id>/` or an example set.
4. Run `ws discovery intake-set discovery_lane/inbox/<set_id>`.
5. Review the intake report in VS Code.
6. If ready, run `ws discovery ingest-set <set_id>`.
7. Run `ws discovery approve-set <set_id> --dry-run --write-report`.
8. Review packet and worker prompt files in VS Code.
9. Approve individual packets with `ws discovery approve <phase_or_packet_id>`.
10. Run `ws discovery handoff-list`.
11. Run `ws discovery queue-plan <set_id> --write-report`.
12. Run `ws discovery audit`.
13. Pass only `READY_FOR_EXECUTION_LANE` queue manifests to the future Execution Lane.

## Command Surface

- `ws discovery intake-set <path>`
- `ws discovery ingest-set <set_id>`
- `ws discovery approve-set <set_id> --dry-run`
- `ws discovery approve <phase_or_packet_id>`
- `ws discovery reject <phase_or_packet_id> --reason "..."`
- `ws discovery handoff-list`
- `ws discovery queue-plan <set_id>`
- `ws discovery queue-plan <set_id> --write-report`
- `ws discovery status`
- `ws discovery review-list`
- `ws discovery audit`
- `ws discovery help`

## Artifact Flow

- Source reports: `discovery_lane/inbox/<set_id>/*.md` or `discovery_lane/examples/<set_id>/*.md`
- Research set manifests: `discovery_lane/research_set_manifests/<set_id>_manifest.json`
- Intake reports: `discovery_lane/intake_reports/<set_id>_intake_report.md`
- Research set ingest manifests: `discovery_lane/research_set_ingests/<set_id>_ingest_manifest.json`
- Phase packets: `discovery_lane/phase_packets/<set_id>__*_packet.md`
- Worker prompts: `discovery_lane/worker_prompts/<set_id>__*_worker_prompt.md`
- Phase manifests: `discovery_lane/manifests/<set_id>__*_manifest.json`
- Approval records: `discovery_lane/approval_records/*_approval_record.json`
- Handoff bundles: `discovery_lane/execution_handoffs/<phase_slug>/`
- Branch plans: `discovery_lane/branch_plans/*_branch_plan.json`
- Execution queue manifests: `discovery_lane/execution_queues/<set_id>_execution_queue.json`
- Execution queue reports: `discovery_lane/execution_queue_reports/<set_id>_execution_queue_report.md`

## Safety Boundaries

- Missing requirements are surfaced as `NEEDS_HUMAN_DECISION`, not invented.
- `approve-set --dry-run` does not approve anything.
- Individual approval writes handoff artifacts only.
- Branch plans use `PLANNED_NOT_CREATED`.
- Queue plans use `NOT_STARTED` execution status.
- Queue planning does not grant commit, push, or merge permission.
- Queue planning is only an input contract for future execution.

## Positive-Path Fixture

Discovery Lane v1.7 includes a dedicated positive-path example set:

```text
discovery_lane/examples/positive_path/
```

Set id:

```text
positive_path_example
```

The fixture validates this path:

```text
example research report
-> intake-set
-> ingest-set
-> individual approval
-> handoff bundle
-> branch plan
-> queue-plan
-> READY_FOR_EXECUTION_LANE
```

The generated queue manifest is:

```text
discovery_lane/execution_queues/positive_path_example_execution_queue.json
```

## Validation Commands

```powershell
python discovery_lane\tools\audit_discovery_lane.py --root discovery_lane
python scripts\test_discovery_lane.py
python scripts\validate_ws_command_safety.py
python scripts\check_ws_manifest_drift.py
python scripts\test_tui_action_visibility.py
python scripts\check_local_safety.py
```

## Current Limitations

- Execution Lane is not implemented.
- Queue manifests are not execution approval.
- Branch plans are not branch creation.
- Worker prompts remain inert Markdown until a future guarded execution lane consumes them.
- No merge planning or branch lifecycle transitions are implemented in Discovery Lane.

## Future Execution Lane Integration

Execution Lane v0.1 contract skeleton exists at `execution_lane/`.

The future Execution Lane must consume only `READY_FOR_EXECUTION_LANE` queue manifests. It must treat handoff bundles as the contract of record and must refuse vague ideas, raw research reports, non-ready queues, or unapproved packets.
