# Execution Handoff Preview Contract

Execution handoff previews describe what Exchange packet metadata would be built
from prepared execution task packets. They are preview-only and non-executing.

## Required Fields

- `preview_id`
- `run_id`
- `target_adapter`
- `source_worker_task_packets`
- `exchange_packet_preview_path`
- `prompt_preview_path`
- `allowed_actions`
- `forbidden_actions`
- `execution_allowed`
- `dispatch_allowed`
- `note`

## Required Conservative Values

- `execution_allowed: false`
- `dispatch_allowed: false`
- `note: preview only`

## Safety Notes

- A handoff preview does not create Exchange packets.
- A handoff preview does not dispatch.
- A handoff preview does not call models, CLIs, terminals, or browsers.
