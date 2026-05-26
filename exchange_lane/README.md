# Exchange Lane v0.2

Exchange Lane is the structured packet layer between existing workstation artifacts and runtime sessions.

It is metadata-only in v0.2:
- No dispatch
- No execution
- No terminal control
- No model invocation

## What It Is

- A registry for exchange packets that reference canonical artifacts.
- A registry for result packet metadata (import contracts only).
- A routing policy and adapter routing contract.
- Read-only status/list/audit command surface for operators.

## What It Is Not

- Not a task dispatcher.
- Not a runtime session launcher.
- Not a model adapter executor.
- Not a browser automation layer.

## Lane Relationships

- Discovery Lane: provides queue/handoff artifacts used as packet sources.
- Product Development Lane: provides manifests/plans/review artifacts used as packet sources.
- Runtime Lane: tracks sessions, assignments, blockers, and workload.
- Execution Lane: future consumer for dispatch/execution decisions.

## Packet Lifecycle (v0.2)

`DRAFT` -> `READY_FOR_REVIEW` -> `APPROVED_FOR_DISPATCH_PLANNING` -> future `DISPATCH_PLANNED` -> future `RESULT_IMPORTED`

v0.2 stops before execution.

## Command Surface

Canonical Python:
- `python exchange_lane/tools/exchange_packet.py help`
- `python exchange_lane/tools/exchange_dispatch_plan.py help`
- `python exchange_lane/tools/exchange_command.py help`
- `python exchange_lane/tools/audit_exchange_lane.py --root exchange_lane`

Canonical ws:
- `ws exchange help`
- `ws exchange status`
- `ws exchange audit`
- `ws exchange packet-list`
- `ws exchange packet-status --packet-id <id>`
- `ws exchange approve-planning --packet-id <id> --note "..."`
- `ws exchange dispatch-plan --packet-id <id> --session-id <id> --assignment-id <id>`
- `ws exchange dispatch-plan-list`
- `ws exchange dispatch-plan-status --dispatch-plan-id <id>`
- `ws exchange fake-dispatch --dispatch-plan-id <id> --confirm`
- `ws exchange real-dispatch --dispatch-plan-id <id> --dry-run`
- `ws exchange real-dispatch --dispatch-plan-id <id> --confirm`
- `ws exchange import-result --capture-manifest <path> --confirm`
- `ws exchange result-list`
- `ws exchange result-status --result-id <id>`
- `ws exchange validate-result --result-id <id>`
- `ws exchange validation-status --validation-id <id>`
- `ws exchange decide-loop --validation-id <id>`
- `ws exchange loop-status`
- `ws exchange repair-plan --loop-decision-id <id>`
- `ws exchange adapter-list`

## Dispatch Planning

1. Create or identify exchange packet.
2. Mark packet `READY_FOR_REVIEW`.
3. Human approves packet for dispatch planning:
   `ws exchange approve-planning --packet-id <id> --note "..."`
4. Register or identify the target runtime session and assignment.
5. Create dispatch plan:
   `ws exchange dispatch-plan --packet-id <id> --session-id <id> --assignment-id <id>`
6. Review dispatch plan.
7. Future execution lane may consume dispatch plan later.

Dispatch planning does not dispatch.
Dispatch planning does not execute.
Dispatch planning does not start terminals.
Dispatch planning does not approve prompts.
Dispatch planning does not grant commit, push, or merge.

## Fake Dispatch and Result Import

1. Packet is approved for dispatch planning.
2. Dispatch plan is created.
3. Fake dispatch simulates adapter output:
   `ws exchange fake-dispatch --dispatch-plan-id <id> --confirm`
4. Result capture is written under `exchange_lane/outbox/<packet_id>/<dispatch_plan_id>/`.
5. Import result:
   `ws exchange import-result --capture-manifest <path> --confirm`
6. Result packet becomes `IMPORTED_PENDING_REVIEW`.
7. Automated validation and loop decision metadata decide the next safe control-plane step.

Fake dispatch does not run a CLI, model, provider, browser, worker prompt, or terminal.
Fake dispatch does not create branches, commits, pushes, or merges.
Imported output is untrusted.
Import does not apply code.
Import does not approve the result.
Import does not grant commit, push, or merge.

## Automated Result Validation and Loop Decisions

1. Fake or future real dispatch produces a result capture.
2. Import result:
   `ws exchange import-result --capture-manifest <path> --confirm`
3. Validate automatically:
   `ws exchange validate-result --result-id <id>`
4. Decide loop:
   `ws exchange decide-loop --validation-id <id>`
5. Check loop status:
   `ws exchange loop-status`

Validation is automated metadata inspection. Arun does not manually accept or
reject every result. Human escalation is required only for permission prompts,
quota/auth blockers, forbidden file/path changes, failed validation beyond retry
budget, ambiguous or contradictory output, branch/commit/push/merge requests,
and final daily/final merge gates.

For the MVP fake-dispatch flow, a conservative fake result validates as
`VALIDATION_PASSED` and usually produces `COMPLETED_PENDING_DAILY_REVIEW`.
Auto-continue and auto-repair are future real-dispatch capabilities and must stay
bounded by retry budget. Validation still does not trust output, apply code,
dispatch packets, start terminals, call providers, or grant commit/push/merge.

## Guarded Real CLI Dispatch

Real CLI dispatch is disabled by default. Adapter command templates live under
`exchange_lane/adapter_commands/` and both `codex_cli` and `gemini_cli` ship with
`enabled: false`. The operator must deliberately configure and enable an adapter
command before `--confirm` can launch anything.

Only `codex_cli` and `gemini_cli` are supported initially. The dispatcher builds
argv from adapter command JSON only, uses `shell=False`, sends the packet prompt
through stdin, captures stdout/stderr, and writes capture artifacts only. It does
not start interactive terminals, automate browsers, accept arbitrary shell
commands, auto-approve permission prompts, create branches, commit, push, or
merge.

Flow:

1. Ensure a `PLANNED_NOT_DISPATCHED` dispatch plan exists.
2. Run dry-run:
   `ws exchange real-dispatch --dispatch-plan-id <id> --dry-run`
3. Enable adapter command config deliberately after verifying the local CLI
   syntax and auth/quota behavior.
4. Run guarded dispatch:
   `ws exchange real-dispatch --dispatch-plan-id <id> --confirm`
5. Import result:
   `ws exchange import-result --capture-manifest <path> --confirm`
6. Validate:
   `ws exchange validate-result --result-id <id>`
7. Decide loop:
   `ws exchange decide-loop --validation-id <id>`

CLI output is captured only and remains untrusted. Quota/auth/permission prompt
signals are treated as blockers; the operator owns CLI auth and quota recovery.

## Slash Planning (Documentation Only)

- `/exchange status` -> `ws exchange status`
- `/exchange audit` -> `ws exchange audit`
- `/exchange packets` -> `ws exchange packet-list`
- `/exchange approve` -> `ws exchange approve-planning --packet-id <id> --note "..."`
- `/exchange plan` -> `ws exchange dispatch-plan --packet-id <id> --session-id <id> --assignment-id <id>`
- `/exchange plans` -> `ws exchange dispatch-plan-list`
- `/exchange results` -> `ws exchange result-list`
- `/exchange validate` -> `ws exchange validate-result --result-id <id>`
- `/exchange loop` -> `ws exchange loop-status`
- `/exchange repair` -> `ws exchange repair-plan --loop-decision-id <id>`
- `/dispatch fake` -> `ws exchange fake-dispatch --dispatch-plan-id <id> --confirm`
- `/dispatch dry-run` -> `ws exchange real-dispatch --dispatch-plan-id <id> --dry-run`
- `/dispatch real` -> `ws exchange real-dispatch --dispatch-plan-id <id> --confirm`
- `/import` -> `ws exchange import-result --capture-manifest <path> --confirm`

No slash dispatcher is implemented in this lane.

## Safety Boundary

- Packet creation/updates write metadata only.
- No packet execution.
- No dispatch.
- No branch/commit/push/merge.
- Automated validation determines safe next metadata steps.
- Human escalation remains the gate for blockers, risk, and final review.

## Future Work

- Guarded dispatch execution contracts.
- Result import command integration.
