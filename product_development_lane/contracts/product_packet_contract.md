# Product Packet Contract

A product packet is the main Product Development Lane artifact generated from a Discovery Lane execution queue.

## Required Source

- `source_execution_queue`
- Queue status must be `READY_FOR_EXECUTION_LANE`.
- Source handoff bundles are the contract of record.
- Raw research reports are not valid direct inputs.

## Required Fields

- `set_id`
- `source_execution_queue`
- `source_handoffs`
- `source_phase_packets`
- `source_worker_prompts`
- `product_context`
- `product_objectives`
- `user_workflows`
- `functional_requirements`
- `non_functional_requirements`
- `UI/UX requirements`
- `wireframe needs`
- `feature list`
- `acceptance criteria`
- `risks`
- `open decisions`
- `downstream artifacts generated`

## Conservative Defaults

When the Discovery handoff does not specify a requirement, the product packet must use `NEEDS_HUMAN_DECISION` or `NOT_SPECIFIED_IN_DISCOVERY_HANDOFF`.

The product packet must not claim that worker prompts were executed, branches were created, or code was generated.

