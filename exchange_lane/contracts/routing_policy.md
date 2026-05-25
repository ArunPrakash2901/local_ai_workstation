# Exchange Routing Policy

## Core Rules

- Exchange packets must reference canonical artifacts by path and checksum.
- Exchange packets must not contain vague product ideas.
- Exchange packets must not bypass Discovery or Product Development approvals.
- Runtime sessions are tracked by Runtime Lane, not Exchange Lane.
- Dispatch is future work and out of scope for v0.1.
- Browser automation is out of scope.
- Missing context must be marked `BLOCKED`, never guessed.
- Human approval remains the gate.
- No adapter may execute work unless a future guarded execution command explicitly allows it.

## v0.1 Boundary

- Packet registry only.
- Status/list/audit only.
- No dispatch, execution, terminal control, or model invocation.
