# Open Design Daemon Render Contract v0.1

This contract defines the guarded workstation integration for Open Design render execution.

## Scope
- Workstation repository: `D:\_ai_brain`
- Open Design source checkout: `/mnt/d/open_design_eval/open-design`
- Tool path policy: use explicit `node apps/daemon/dist/cli.js ...`
- Global `od`/`open-design` binaries are not trusted for execution routing in this slice.

## Execution Model
Open Design render is a two-step daemon lifecycle, not a one-shot render command.

1. Build prerequisite (manual/operator or pre-validated):
- `pnpm --filter @open-design/daemon build`

2. Headless daemon start:
- `node apps/daemon/dist/cli.js daemon start --headless --port <port> --host 127.0.0.1`

3. Daemon status check:
- `node apps/daemon/dist/cli.js status --json --daemon-url http://127.0.0.1:<port>`

4. Project create:
- `node apps/daemon/dist/cli.js project create --name "<name>" --json --daemon-url http://127.0.0.1:<port>`

5. Run start:
- `node apps/daemon/dist/cli.js run start --project <project_id> --message "<design_prompt_text>" --follow --daemon-url http://127.0.0.1:<port>`

6. File inspection (optional guarded read):
- `node apps/daemon/dist/cli.js files list <project_id> --json --daemon-url http://127.0.0.1:<port>`
- `node apps/daemon/dist/cli.js files read ...` (if required later)

7. UI/GenUI surface handling:
- If run events require UI response/surface input, execution is blocked and handed to operator.
- No invented answers are allowed in this slice.

## Environment Policy
- Required env vars: none if `--daemon-url` is passed.
- Optional env vars:
  - `OD_DAEMON_URL`
  - `OD_DATA_DIR`
- Workstation-controlled env:
  - `OD_DATA_DIR` is forced inside prepared run `allowed_write_root`.

## Output and Capture Policy
All render outputs and captures stay inside the prepared run root:
- `products/<product_id>/design_runs/open_design/<run_id>/`

Planned captures:
- `stdout.txt`
- `stderr.txt`
- `daemon_stdout.txt`
- `daemon_stderr.txt`
- `raw_output/run_events.ndjson`
- `command_manifest.json`
- `render_manifest.json`
- `output_file_list.json`
- `render_review.md`

## Safety Boundaries
- No `shell=True`.
- No shell wrapper execution (`cmd`, `powershell`, `bash`, `wsl`) as adapter command contract.
- Explicit argv list only.
- Capture/output paths must remain under prepared `allowed_write_root`.
- Generated output is untrusted until operator review pipeline accepts it.
- No source/app repository mutation.
- No browser automation.
- No hidden provider calls.

## Provider/Network Behavior
- `run start` may call external providers depending on agent/provider mode.
- Provider mode/requirements must be explicitly known before confirm.
- If provider prerequisites are unknown/unsatisfied, confirm is refused.

## Timeout and Blocking
- Guarded timeout is required and enforced.
- Timeout or daemon readiness failure results in blocked/failed run metadata.
- UI surface/question prompt requirement results in `BLOCKED_NEEDS_OPERATOR_UI_RESPONSE`.

## Refusal Conditions
Confirm execution is refused when any of the following is true:
- Prepared run packet missing or not `PREPARED_NOT_EXECUTED`.
- `allowed_write_root` missing or outside run sandbox.
- Source checkout missing/invalid.
- `node` missing.
- `apps/daemon/dist/cli.js` missing.
- Runtime contract readiness below `RENDER_CONTRACT_FOUND`.
- Provider requirements unknown/unsatisfied.
- Any capture/output path escapes sandbox.
- Timeout configuration invalid.
