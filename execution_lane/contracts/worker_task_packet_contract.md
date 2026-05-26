# Worker Task Packet Contract

Execution Lane worker task packets are bounded metadata artifacts prepared from a
Discovery execution queue. They do not execute prompts and do not grant write or
git permissions.

## Required Fields

- `task_packet_id`
- `run_id`
- `phase_id`
- `phase_title`
- `source_phase_packet`
- `source_worker_prompt`
- `source_handoff_bundle`
- `source_branch_plan`
- `linked_product_dev_artifacts`
- `bounded_objective`
- `allowed_write_roots`
- `forbidden_paths`
- `forbidden_actions`
- `expected_outputs`
- `validation_expectations`
- `target_adapters_allowed`
- `human_approval_required`
- `execution_allowed`
- `commit_allowed`
- `push_allowed`
- `merge_allowed`

## Required Conservative Values

- `human_approval_required: true`
- `execution_allowed: false`
- `commit_allowed: false`
- `push_allowed: false`
- `merge_allowed: false`

## Safety Notes

- A worker task packet is preparation metadata only.
- A worker task packet does not execute worker prompts.
- A worker task packet does not create branches.
- A worker task packet does not commit, push, or merge.
