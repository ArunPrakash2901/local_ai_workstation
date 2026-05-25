# Execution Lane

Execution Lane is not implemented yet.

This folder defines the v0.1 intake contract skeleton for a future execution system. The future lane will consume Discovery Lane execution queue manifests only after Discovery Lane has produced `READY_FOR_EXECUTION_LANE`.

## Boundary

Execution Lane starts only from:

```text
discovery_lane/execution_queues/<set_id>_execution_queue.json
```

with:

```text
queue_status: READY_FOR_EXECUTION_LANE
```

Execution Lane must not consume:

- vague product ideas
- raw research reports
- ChatGPT/Gemini discovery conversations
- Deep Research prompts
- non-ready queue manifests
- unapproved phase packets

Discovery Lane handoff bundles are the contract of record. Execution Lane must not reinterpret product requirements or expand scope beyond the approved handoff.

## Planned Future Responsibilities

Future guarded slices may implement:

- create or use phase branches
- run bounded worker prompts
- collect execution logs
- run validation commands
- produce execution reports
- prepare merge plans
- require human approval before commit, push, or merge unless explicitly allowed

## Not Implemented

Execution Lane currently does not:

- execute worker prompts
- create branches
- checkout branches
- run Codex, Gemini, local models, browsers, or providers
- run shell commands
- commit, push, or merge
- modify product/application source files

## Contracts

- `contracts/execution_queue_contract.md`
- `contracts/execution_run_contract.md`
- `contracts/branch_execution_contract.md`
