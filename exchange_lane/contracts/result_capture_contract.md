# Result Capture Contract

A result capture is the raw output bundle produced by a future dispatch path or by the MVP fake dispatcher.
It is stored before import into an Exchange result packet.

For this MVP slice, fake dispatch writes captures under:

`exchange_lane/outbox/<packet_id>/<dispatch_plan_id>/`

Each capture directory contains:

- `raw_output.md`
- `parsed_result.json`
- `validation.md`
- `operator_report.md`
- `capture_manifest.json`

## `capture_manifest.json` Fields

- `capture_id`
- `packet_id`
- `dispatch_plan_id`
- `source_dispatch_plan`
- `source_packet`
- `target_adapter`
- `fake_execution`
- `real_cli_execution`
- `created_at`
- `raw_output_path`
- `parsed_result_path`
- `validation_path`
- `operator_report_path`
- `execution_occurred`
- `model_or_provider_called`
- `terminal_started`
- `branch_created`
- `commit_performed`
- `push_performed`
- `merge_performed`
- `app_source_modified`
- `import_status`
- `generated_by`

## Fake Dispatch Defaults

- `fake_execution: true`
- `real_cli_execution: false`
- `execution_occurred: false`
- `model_or_provider_called: false`
- `terminal_started: false`
- `branch_created: false`
- `commit_performed: false`
- `push_performed: false`
- `merge_performed: false`
- `app_source_modified: false`
- `import_status: NOT_IMPORTED`

## Safety Boundary

Fake dispatch is not real execution.
Fake dispatch does not run Codex, Gemini, Ollama, browsers, package managers, or shell commands.
Fake dispatch does not start terminals.
Fake dispatch does not create branches, commits, pushes, or merges.
Fake dispatch does not modify app or source repositories.

Result capture content is untrusted until imported and reviewed by a human.
Importing a result capture does not apply code changes and does not approve the result.
