# Open Design Daemon Render Contract v0.1

This contract defines two Open Design workstation modes:

- Mode A: managed runtime lifecycle through Open Design's supported `pnpm tools-dev` entry point.
- Mode B: experimental headless daemon render through `node apps/daemon/dist/cli.js`.

Mode A is the primary local usage path. Mode B remains guarded and experimental until a real headless run succeeds safely.

## Scope
- Workstation repository: `D:\_ai_brain`
- Open Design source checkout: `/mnt/d/open_design_eval/open-design`
- Tool path policy: use explicit `node apps/daemon/dist/cli.js ...`
- Global `od`/`open-design` binaries are not trusted for execution routing in this slice.

## Execution Model
Open Design is not a one-shot render CLI. The documented local lifecycle is a managed daemon/web runtime.

### Mode A: Managed Runtime Mode

Supported lifecycle command family:

- `pnpm tools-dev status --namespace workstation --tools-dev-root <runtime_root> --json`
- `pnpm tools-dev check --namespace workstation --tools-dev-root <runtime_root> --json`
- `pnpm tools-dev start web --namespace workstation --tools-dev-root <runtime_root> --json`
- `pnpm tools-dev stop --namespace workstation --tools-dev-root <runtime_root> --json`

Workstation commands:

- `ws product-design-runtime-status --tool open-design`
- `ws product-design-runtime-start --tool open-design --dry-run`
- `ws product-design-runtime-start --tool open-design --confirm`
- `ws product-design-runtime-stop --tool open-design --dry-run`
- `ws product-design-runtime-stop --tool open-design --confirm`

Mode A starts/checks/stops the Open Design managed daemon/web runtime only. It does not submit design requests, spawn local code-agent CLIs, call providers for generation, apply files, or trust outputs.

Managed runtime paths:

- Open Design checkout: `/mnt/d/open_design_eval/open-design`
- tools-dev root: `product_development_lane/runtime/open_design/managed_runtime/tools_dev/`
- OD_DATA_DIR: `product_development_lane/runtime/open_design/managed_runtime/open_design_data/`
- lifecycle captures: `product_development_lane/runtime/open_design/managed_runtime/captures/`

Mode A must use explicit argv with `pnpm tools-dev ...`; it must not use global `od`, global `open-design`, `/usr/bin/od`, or shell wrappers.

### Mode B: Experimental Headless Daemon Mode

The existing guarded render confirm path uses the daemon CLI directly. It is experimental until proven by a real safe run.

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
- No `/usr/bin/od`; it is the Unix octal dump utility on this host and must never be treated as Open Design.
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
