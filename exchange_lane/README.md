# Exchange Lane v0.1

Exchange Lane is the structured packet layer between existing workstation artifacts and runtime sessions.

It is metadata-only in v0.1:
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

## Packet Lifecycle (v0.1)

`DRAFT` -> `READY_FOR_REVIEW` -> future `APPROVED_FOR_DISPATCH_PLANNING` -> future `DISPATCH_PLANNED` -> future `RESULT_IMPORTED`

v0.1 stops before dispatch.

## Command Surface

Canonical Python:
- `python exchange_lane/tools/exchange_packet.py help`
- `python exchange_lane/tools/exchange_command.py help`
- `python exchange_lane/tools/audit_exchange_lane.py --root exchange_lane`

Canonical ws:
- `ws exchange help`
- `ws exchange status`
- `ws exchange audit`
- `ws exchange packet-list`
- `ws exchange packet-status --packet-id <id>`
- `ws exchange adapter-list`

## Slash Planning (Documentation Only)

- `/exchange status` -> `ws exchange status`
- `/exchange audit` -> `ws exchange audit`
- `/exchange packets` -> `ws exchange packet-list`

No slash dispatcher is implemented in this lane.

## Safety Boundary

- Packet creation/updates write metadata only.
- No packet execution.
- No dispatch.
- No branch/commit/push/merge.
- Human approval remains the gate.

## Future Work

- Dispatch planning workflows.
- Guarded dispatch execution contracts.
- Result import command integration.
