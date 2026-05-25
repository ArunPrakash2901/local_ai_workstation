# Runtime Session Lane v0.1

Runtime Session Lane is a non-executing visibility layer for local workstation sessions.

It tracks manually operated terminal and CLI sessions:
- PowerShell terminal windows
- WSL terminal sessions
- Codex CLI sessions
- Gemini CLI sessions
- local Ollama/Qwen model sessions
- human approval blockers
- quota/session notes
- logs/checkpoints/status metadata

It does not automate browser ChatGPT or Gemini. The browser discovery flow remains manual and upstream of the workstation. Discovery Lane starts only after strict phase-wise Markdown research reports exist.

Runtime Session Lane v0.2 adds assignment metadata and workload visibility on top of the session/blocker registry. It still does not execute anything.

## Boundary

Runtime Session Lane does not:
- start terminals
- run Codex, Gemini, Ollama, or other CLIs
- inject keystrokes
- approve prompts automatically
- execute worker prompts
- create branches
- commit, push, or merge
- call APIs
- assign tasks to an execution engine

Codex CLI and Gemini CLI are treated as human-authenticated subscription CLI tools, not API workers. The workstation records sessions and blockers, but it does not assume API access or unlimited quota.

## Commands

Canonical workstation commands:
- `ws runtime help`
- `ws runtime adapter-list`
- `ws runtime status`
- `ws runtime register --session-id <id> --adapter <adapter_id> --label "<label>" --cwd <path> --lane <lane> --task "<task>"`
- `ws runtime update-status --session-id <id> --status <status> --note "<note>"`
- `ws runtime report-blocker --session-id <id> --type <blocker_type> --description "<description>"`
- `ws runtime resolve-blocker --blocker-id <id> --resolution "<resolution>"`
- `ws runtime assign --session-id <id> --task-source <path> --label "<label>" --type <task_source_type>`
- `ws runtime assignment-list`
- `ws runtime assignment-status --assignment-id <id>`
- `ws runtime update-assignment --assignment-id <id> --status <status> --note "<note>"`
- `ws runtime workload [--write-report]`
- `ws runtime unassigned`
- `ws runtime audit`

Python fallback:
- `python runtime_lane/tools/runtime_session.py help`
- `python runtime_lane/tools/runtime_session.py adapter-list`
- `python runtime_lane/tools/runtime_session.py status --root runtime_lane`
- `python runtime_lane/tools/runtime_session.py workload --root runtime_lane`
- `python runtime_lane/tools/runtime_session.py unassigned --root runtime_lane`
- `python runtime_lane/tools/audit_runtime_lane.py --root runtime_lane`

## Slash Planning

Short operator shortcuts are documented only:
- `/sessions` -> `ws runtime status`
- `/sessions register` -> `ws runtime register ...`
- `/sessions blocker` -> `ws runtime report-blocker ...`
- `/sessions assignments` -> `ws runtime assignment-list`
- `/sessions workload` -> `ws runtime workload`
- `/sessions assign` -> `ws runtime assign ...`
- `/sessions unassigned` -> `ws runtime unassigned`
- `/sessions audit` -> `ws runtime audit`

No slash dispatcher is implemented by this lane.

## Assignment Registry

Assignments are ownership metadata only. They tell the operator which runtime session owns which task source.

Use `ws runtime assign ...` to register an assignment, `ws runtime assignment-list` to list them, and `ws runtime assignment-status --assignment-id <id>` to inspect one record.

Assignments do not execute the task source and do not grant branch, commit, push, or merge permission.

## Workload Dashboard

Use `ws runtime workload` to see sessions, assignments, blocker state, pending-review work, and conservative attention hints.

Use `ws runtime workload --write-report` only when you want a local markdown report at `runtime_lane/workload_reports/runtime_workload_report.md`.

Use `ws runtime unassigned` to scan conservative candidate task sources that have not yet been assigned.

## Artifacts

Session records:
- `runtime_lane/sessions/<session_id>.json`

Blocker records:
- `runtime_lane/blockers/<blocker_id>.json`

Assignment records:
- `runtime_lane/assignments/<assignment_id>.json`

Workload reports:
- `runtime_lane/workload_reports/runtime_workload_report.md`

Reports:
- reserved for future human-readable summaries

## Normal Operator Flow

1. Operator opens and controls terminal/CLI sessions manually.
2. Operator registers a session with `ws runtime register ...`.
3. Operator updates status as the session changes.
4. If a session blocks on quota, auth, approvals, errors, or context, operator records a blocker.
5. Operator assigns task sources to sessions with `ws runtime assign ...`.
6. `ws runtime workload` gives the current session/blocker/assignment view.
7. `ws runtime unassigned` shows conservative candidate task sources that are not yet owned.
8. `ws runtime audit` verifies metadata integrity.
