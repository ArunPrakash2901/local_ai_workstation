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

## Slash Planning (Documentation Only)

- `/exchange status` -> `ws exchange status`
- `/exchange audit` -> `ws exchange audit`
- `/exchange packets` -> `ws exchange packet-list`
- `/exchange approve` -> `ws exchange approve-planning --packet-id <id> --note "..."`
- `/exchange plan` -> `ws exchange dispatch-plan --packet-id <id> --session-id <id> --assignment-id <id>`
- `/exchange plans` -> `ws exchange dispatch-plan-list`

No slash dispatcher is implemented in this lane.

## Safety Boundary

- Packet creation/updates write metadata only.
- No packet execution.
- No dispatch.
- No branch/commit/push/merge.
- Human approval remains the gate.

## Future Work

- Guarded dispatch execution contracts.
- Result import command integration.
