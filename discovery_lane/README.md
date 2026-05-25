# Discovery Lane

Discovery Lane starts only after phase-wise Deep Research reports already exist as Markdown files.

Before this lane, the operator manually discusses vague product ideas with ChatGPT or Gemini, answers discovery questions, creates a phase breakdown, runs Deep Research, and saves phase-wise reports as `.md` files. The workstation does not handle vague ideas, ask discovery questions, standardise prompts, run Deep Research, browse the web, or call external models.

Discovery Lane is a requirements compression and handoff layer:

```text
phase-wise research reports .md
-> research set intake
-> report validation
-> phase packets
-> worker prompts
-> human approval
-> execution handoff bundles
-> branch plans
-> later execution lane
```

It is not an execution lane. It does not run worker prompts, create branches, commit, push, merge, call providers, or browse.

## Version Scope

- v1: ingest individual research reports into phase packets, worker prompts, manifests, and `discovery_index.md`.
- v1.1: record human approval/rejection, create immutable handoff bundles, and plan branches without git actions.
- v1.2: expose Discovery Lane through `ws discovery ...`, add read-only audit checks, and improve status/review-list operation.
- v1.3: validate complete research sets before ingest using set-level manifests and intake reports.
- v1.4: ingest one `READY_FOR_INGEST` research set into set-prefixed phase packets and worker prompts.
- v1.5: plan set-level approval review without batch approval or execution.
- v1.6: list approved handoffs and build non-executing execution queue plans.
- v1.7: add an end-to-end positive-path fixture and freeze the lane boundary.

The canonical boundary summary is [DISCOVERY_LANE_FREEZE_REPORT.md](DISCOVERY_LANE_FREEZE_REPORT.md). It documents the completed non-executing Discovery Lane lifecycle and its handoff point to the future Execution Lane.

## Research Set Intake

A research set is a group of phase-wise Markdown research reports that belong to one product or project idea.

Supported input layouts:

```text
discovery_lane/inbox/product_idea_alpha/
  phase_01_foundation_research.md
  phase_02_runtime_research.md
  phase_03_ui_research.md
```

or a flat inbox:

```text
discovery_lane/inbox/phase_01_foundation_research.md
discovery_lane/inbox/phase_02_runtime_research.md
```

`intake-set` validates the set of reports. It does not generate phase packets, worker prompts, approvals, handoffs, branches, or execution.

Workstation command:

```powershell
ws discovery intake-set discovery_lane/inbox/product_idea_alpha
```

Raw fallback:

```powershell
python discovery_lane/tools/intake_research_set.py --input discovery_lane/inbox/product_idea_alpha --output discovery_lane --set-id product_idea_alpha
```

Generated set-level outputs:

```text
discovery_lane/research_sets/<set_id>/research_set.json
discovery_lane/research_set_manifests/<set_id>_manifest.json
discovery_lane/intake_reports/<set_id>_intake_report.md
```

The set manifest records source files, checksums, detected phase IDs/titles, validation statuses, duplicate phase IDs, unclear phase IDs, missing phase ordering, and recommended next action.

Set statuses:

- `READY_FOR_INGEST`: reports are structurally ready for normal Discovery Lane ingest.
- `NEEDS_HUMAN_DECISION`: the set is usable only after operator review of unclear metadata or decisions.
- `NOT_READY`: duplicate phase IDs, missing required report sections, missing reports, or other blockers need correction first.

## Research Set Ingest

`ingest-set` converts one `READY_FOR_INGEST` research set into phase packets and worker prompts. It reads only the source reports listed in the research-set manifest, recomputes SHA-256 checksums, and stops if any source report changed or is missing.

Workstation command:

```powershell
ws discovery ingest-set product_idea_alpha
```

Raw fallback:

```powershell
python discovery_lane/tools/ingest_research_set.py --set-id product_idea_alpha --root discovery_lane
```

Generated set-level ingest outputs:

```text
discovery_lane/research_set_ingests/<set_id>_ingest_manifest.json
discovery_lane/research_set_ingest_reports/<set_id>_ingest_report.md
```

Generated phase outputs stay in the existing compatibility folders, but file names are prefixed with the set id:

```text
discovery_lane/phase_packets/<set_id>__phase_01_foundation_packet.md
discovery_lane/worker_prompts/<set_id>__phase_01_foundation_worker_prompt.md
discovery_lane/manifests/<set_id>__phase_01_foundation_manifest.json
```

Ingest statuses:

- `INGESTED`
- `NOT_INGESTED_SOURCE_CHANGED`
- `NOT_INGESTED_SET_NOT_READY`
- `NOT_INGESTED_MISSING_SOURCE`
- `NOT_INGESTED_VALIDATION_FAILED`

`ingest-set` does not approve packets, create handoff bundles, create branches, execute worker prompts, call models, commit, push, or merge.

## Set Approval Review

`approve-set --dry-run` reviews one ingested research set and reports which generated packets are ready for human approval. It is a review planner only.

Workstation command:

```powershell
ws discovery approve-set product_idea_alpha --dry-run
```

Raw fallback:

```powershell
python discovery_lane/tools/approve_research_set.py --set-id product_idea_alpha --root discovery_lane --dry-run
```

Optional advisory report:

```powershell
ws discovery approve-set product_idea_alpha --dry-run --write-report
```

The optional report is written to:

```text
discovery_lane/approval_records/<set_id>_approval_review_plan.md
```

The approval review plan includes packet status, worker prompt path, phase manifest path, approval status, handoff status, and recommended action for each generated packet.

`approve-set --dry-run` does not approve packets. It does not create handoff bundles, branch plans, git branches, commits, pushes, merges, model calls, or worker execution. Individual approval remains the human gate:

```powershell
ws discovery approve <phase_or_packet_id>
```

## Execution Queue Planning

After individual packets are approved, Discovery Lane can list handoff bundles and build a set-level execution queue plan. This is still planning only.

Read-only handoff list:

```powershell
ws discovery handoff-list
```

Queue plan:

```powershell
ws discovery queue-plan product_idea_alpha
```

Queue plan with Markdown report:

```powershell
ws discovery queue-plan product_idea_alpha --write-report
```

Raw fallback:

```powershell
python discovery_lane/tools/build_execution_queue.py --set-id product_idea_alpha --root discovery_lane --write-report
```

Generated queue outputs:

```text
discovery_lane/execution_queues/<set_id>_execution_queue.json
discovery_lane/execution_queue_reports/<set_id>_execution_queue_report.md
```

Queue statuses:

- `READY_FOR_EXECUTION_LANE`
- `EMPTY_NO_APPROVED_HANDOFFS`
- `BLOCKED_MISSING_HANDOFFS`
- `BLOCKED_INVALID_BRANCH_PLANS`
- `BLOCKED_INVALID_APPROVALS`

`queue-plan` creates a planning artifact only. It does not execute worker prompts, create or checkout branches, approve packets, create handoff bundles, commit, push, merge, or grant new permissions.

Discovery Lane v1.7 includes an end-to-end positive-path fixture under `discovery_lane/examples/positive_path/`. The fixture proves that example Markdown research can reach a `READY_FOR_EXECUTION_LANE` queue without executing worker prompts or creating branches.

## Normal Operator Flow

1. Manually create phase-wise Deep Research reports in ChatGPT/Gemini.
2. Save reports as `.md` files.
3. Put reports into `discovery_lane/inbox/` or a grouped folder under `discovery_lane/inbox/<set_id>/`.
4. Run `ws discovery intake-set discovery_lane/inbox/<set_id>`.
5. Review the intake report in VS Code.
6. Fix missing, duplicate, or unclear phase report issues if needed.
7. If the set is `READY_FOR_INGEST`, run `ws discovery ingest-set <set_id>`.
8. Run `ws discovery approve-set <set_id> --dry-run`.
9. Open the approval review plan or listed packet and worker prompt files in VS Code.
10. Approve individual packets with `ws discovery approve <phase_or_packet_id>`.
11. Reject individual packets if needed with `ws discovery reject <phase_or_packet_id> --reason "..."`.
12. Run `ws discovery handoff-list`.
13. Run `ws discovery queue-plan <set_id> --write-report`.
14. Run `ws discovery audit`.
15. Later, the execution lane consumes execution queue plans.

## Ingest Reports

Workstation command:

```powershell
ws discovery ingest
```

Raw command:

```powershell
python discovery_lane/tools/ingest_research_reports.py --input discovery_lane/inbox --output discovery_lane
```

Local dispatcher:

```powershell
python discovery_lane/tools/discovery_command.py ingest
```

Target slash command:

```text
/discovery ingest
```

The command reads `.md` files from the input directory and writes generated phase-level files under the Discovery Lane root. It does not delete or move source reports.

## Input Report Contract

Each phase-wise research report should include these sections or clear equivalents:

- Phase ID
- Phase Title
- Product Context
- Objective
- Scope
- Non-Goals
- Assumptions, if applicable
- User / Operator Workflow
- Functional Requirements
- Technical Requirements
- Architecture Guidance
- Data / File / State Requirements
- UI / UX / Wireframe Guidance, if applicable
- Implementation Tasks
- Suggested Parallel Workstreams, if applicable
- Dependencies
- Risks
- Validation / Test Strategy
- Acceptance Criteria
- Open Questions
- Sources / References, if applicable

Heading names may vary. For example, `Out of Scope` can satisfy `Non-Goals`, and `Success Criteria` can partially satisfy `Acceptance Criteria`. If meaning is unclear, the ingest tool flags the gap instead of inventing missing requirements.

## Generated Outputs

For an input report:

```text
discovery_lane/inbox/phase_01_foundation_research.md
```

the generated v1 outputs are:

```text
discovery_lane/phase_packets/phase_01_foundation_packet.md
discovery_lane/worker_prompts/phase_01_foundation_worker_prompt.md
discovery_lane/manifests/phase_01_foundation_manifest.json
discovery_lane/discovery_index.md
```

After approval, v1.1 outputs are:

```text
discovery_lane/approval_records/phase_01_foundation_approval_record.json
discovery_lane/branch_plans/phase_01_foundation_branch_plan.json
discovery_lane/approved_packets/phase_01_foundation_phase_packet.md
discovery_lane/execution_handoffs/phase-01-foundation/
```

The handoff bundle contains:

- `HANDOFF.md`
- `phase_packet.md`
- `worker_prompt.md`
- `approval_record.json`
- `branch_plan.json`
- `manifest_snapshot.json`, if available
- `README.md`

## Status Values

Validation statuses:

- `READY_FOR_HUMAN_REVIEW`: core implementation guidance is present and no human decision flags were detected.
- `NEEDS_HUMAN_DECISION`: enough structure exists for review, but one or more gaps, open questions, or inferred fields need operator approval.
- `NOT_EXECUTION_READY`: required implementation guidance is missing. The generated worker prompt is explicitly marked as not ready for execution.

Approval statuses:

- `APPROVED_FOR_EXECUTION_HANDOFF`
- `REJECTED_BY_HUMAN`
- `APPROVED_WITH_OVERRIDES`
- `BLOCKED_NEEDS_REVISION`

Branch status:

- `PLANNED_NOT_CREATED`

## Handoff Folders Vs Branches

Discovery Lane uses this model:

- Handoff folder = immutable approved contract of record.
- Git branch = mutable implementation workspace for that phase.

Discovery Lane plans branch names and records branch metadata. It does not create, checkout, merge, push, or delete branches.

Approval for handoff does not mean automatic execution, commit, push, or merge. It only means the packet is approved as an execution input for a later lane.

## Approval Commands

Workstation approve command:

```powershell
ws discovery approve phase_01_foundation --branch work/discovery/phase-01-foundation
```

Approve a ready packet:

```powershell
python discovery_lane/tools/approve_phase_packet.py --packet discovery_lane/phase_packets/phase_01_foundation_packet.md --output discovery_lane
```

Reject a packet:

```powershell
python discovery_lane/tools/approve_phase_packet.py --packet discovery_lane/phase_packets/phase_01_foundation_packet.md --output discovery_lane --reject --reason "Acceptance criteria need revision."
```

Optional permission flags only record future permissions:

- `--allow-commit`
- `--allow-push`
- `--allow-merge`

These flags do not perform git actions.

## Status, Review List, And Audit

Status summarizes inbox reports, research sets, set manifests, intake reports, set ingest reports, approval review plans, execution queue manifests/reports, generated packets, worker prompts, approval records, handoffs, rejected packets, branch plans, validation statuses, and approval statuses:

```powershell
ws discovery status
```

Review list shows research sets and packets needing human attention, including duplicate phase IDs, missing phase IDs, unclear phase titles, `NOT_READY` sets, `NEEDS_HUMAN_DECISION` sets, ingested sets needing approval review, approved sets needing queue plans, blocked queue plans, handoff issues, unapproved ready packets, and packets approved with overrides:

```powershell
ws discovery review-list
```

Audit checks Discovery Lane structure and generated records without writing files:

```powershell
ws discovery audit
```

Raw fallback:

```powershell
python discovery_lane/tools/audit_discovery_lane.py --root discovery_lane
```

## Slash Command Interface

Slash syntax is the target operator interface. Slash commands are documented aliases to executable `ws discovery ...` commands, and `discovery_lane/tools/discovery_command.py` remains the Python fallback.

Examples:

```text
/discovery intake-set discovery_lane/inbox/product_idea_alpha
/discovery ingest-set product_idea_alpha
/discovery approve-set product_idea_alpha --dry-run
/discovery handoff-list
/discovery queue-plan product_idea_alpha --write-report
/discovery ingest
/discovery review-list
/discovery approve phase_01_foundation --branch work/discovery/phase-01-foundation
/discovery audit
/discovery status
```

Equivalent executable commands:

```powershell
ws discovery intake-set discovery_lane/inbox/product_idea_alpha
ws discovery ingest-set product_idea_alpha
ws discovery approve-set product_idea_alpha --dry-run
ws discovery handoff-list
ws discovery queue-plan product_idea_alpha --write-report
ws discovery ingest
ws discovery review-list
ws discovery approve phase_01_foundation --branch work/discovery/phase-01-foundation
ws discovery audit
ws discovery status
```

## Example Validation Flow

Example data should stay under `discovery_lane/examples/` and should not pollute production inbox, handoff, or branch-plan folders.

```powershell
python discovery_lane/tools/intake_research_set.py --input discovery_lane/examples --output discovery_lane/examples/generated --set-id example_product
python discovery_lane/tools/ingest_research_reports.py --input discovery_lane/examples --output discovery_lane/examples/generated
python discovery_lane/tools/audit_discovery_lane.py --root discovery_lane --state-root discovery_lane/examples/generated
```

## Boundaries

Discovery Lane does not:

- handle vague product ideas
- ask discovery questions
- standardise prompts
- run Deep Research
- browse the web
- call ChatGPT, Gemini, local models, or external APIs
- execute worker prompts
- create, checkout, push, merge, or delete git branches
- commit code

Discovery Lane does:

- validate already-created Markdown research reports
- surface missing or unclear requirements as `NEEDS_HUMAN_DECISION`
- generate deterministic phase packets and worker prompts
- record human approval or rejection
- create immutable handoff bundles
- plan branch names for later execution lanes
