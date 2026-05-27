# Execution Lane

Execution Lane MVP Slice 1 is a preparation layer only.

It consumes Discovery queue manifests that are already
`READY_FOR_EXECUTION_LANE`, validates them, and creates bounded metadata
artifacts for later guarded dispatch.

## MVP Slice 1 Scope

Implemented:

- `ws execution status`
- `ws execution plan --queue <queue_manifest> --dry-run`
- `ws execution prepare --queue <queue_manifest> --confirm`
- `ws execution run-status --run <run_id>`
- `ws execution handoff-preview --run <run_id> --target <adapter> --dry-run`
- `ws execution audit`

Not implemented:

- worker prompt execution
- branch creation or checkout
- terminal/model/provider execution
- commit/push/merge
- app/source repository writes

## Safety Boundaries

- planning and preparation artifacts are metadata only
- execution remains disabled (`execution_allowed: false`)
- branch creation remains disabled (`branch_creation_allowed: false`)
- commit/push/merge remain disabled
- model/agent outputs remain untrusted until future import/review

## Normal Flow

1. `ws execution plan --queue <queue> --dry-run`
2. `ws execution prepare --queue <queue> --confirm`
3. `ws execution run-status --run <run_id>`
4. `ws execution handoff-preview --run <run_id> --target codex_cli --dry-run`

## Contracts

- `contracts/execution_queue_contract.md`
- `contracts/execution_run_contract.md`
- `contracts/worker_task_packet_contract.md`
- `contracts/execution_handoff_preview_contract.md`

## Artifact Naming

Execution run and worker task packet filenames use compact IDs for Windows-safe
paths. Full set/phase/objective context remains in artifact metadata content.
