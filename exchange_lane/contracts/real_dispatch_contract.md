# Exchange Guarded Real Dispatch Contract

Guarded real dispatch is the first Exchange path that may launch a local
subscription CLI. It is disabled by default and exists only to capture CLI output
from an approved dispatch plan. Captured output must still be imported,
validated, and loop-decided separately.

## Preconditions

- Dispatch is allowed only from a dispatch plan with `planned_status:
  PLANNED_NOT_DISPATCHED`.
- Dispatch requires explicit `--confirm`.
- Dry-run requires explicit `--dry-run` and writes nothing.
- Dispatch target must be `codex_cli` or `gemini_cli` for this slice.
- Runtime session and assignment must exist.
- Runtime session, assignment, packet, and dispatch plan adapters must be
  compatible.
- Source artifact checksum must match the dispatch plan and packet record before
  a CLI is launched.
- Packet and dispatch plan `execution_allowed` fields must be validated; they
  must not grant broader uncontrolled execution authority.
- Adapter command config must be explicitly enabled.
- Packet and plan safety fields are validated so they do not grant branch,
  commit, push, or merge authority.

## Hard Boundaries

- No browser automation.
- No direct API calls.
- No arbitrary shell strings.
- No `shell=True`.
- No model-chosen shell commands.
- No branch creation.
- No checkout, commit, push, or merge.
- No automatic approval of CLI permission prompts.
- No unattended retry loop.
- No automatic import, validation, or loop decision.

## Adapter Command Source

Real dispatch must build the subprocess argv only from
`exchange_lane/adapter_commands/<adapter>_command.json`. The operator must
deliberately enable the config before real dispatch. Disabled configs must refuse
with:

`Adapter command is not enabled. Configure exchange_lane/adapter_commands/<adapter>_command.json deliberately before real dispatch.`

## Capture Location

Real dispatch writes captures under:

`exchange_lane/outbox/<packet_id>/<dispatch_plan_id>/`

Required capture files:

- `raw_output.md`
- `parsed_result.json`
- `validation.md`
- `operator_report.md`
- `capture_manifest.json`
- `stdout.txt`
- `stderr.txt`
- `command_manifest.json`

## capture_manifest.json Fields

- `capture_id`
- `packet_id`
- `dispatch_plan_id`
- `source_dispatch_plan`
- `source_packet`
- `target_adapter`
- `fake_execution: false`
- `real_cli_execution: true`
- `model_or_provider_called: true` if the CLI subprocess launched
- `terminal_started: false`
- `execution_occurred: true` only if the subprocess command ran
- `branch_created: false`
- `commit_performed: false`
- `push_performed: false`
- `merge_performed: false`
- `app_source_modified: false` unless detected or declared by a later policy
- `timeout_seconds`
- `return_code`
- `command_manifest_path`
- `raw_output_path`
- `parsed_result_path`
- `validation_path`
- `operator_report_path`
- `stdout_path`
- `stderr_path`
- `import_status: NOT_IMPORTED`
- `generated_by`

Imported output remains untrusted until the existing
`import-result -> validate-result -> decide-loop` pipeline completes.
