# Exchange Runtime / PowerShell Session Plan

## Objective

PowerShell should not be manually managed by the operator as the exchange/orchestration bus.
The workstation should manage PowerShell, WSL, browser profiles, and local runtimes as controlled session layers for Exchange Lane adapters.

The operator role should be:

- approve or reject bounded dispatches
- inspect deterministic reports
- review imported outputs
- clarify blocked work

The operator should not have to keep separate PowerShell windows open for Codex, Gemini, Product Lane, or Exchange Lane coordination.

## Runtime vs Adapter

An adapter is the worker interface that performs or previews a bounded task:

- `codex_cli`
- `gemini_cli`
- `local_ollama`
- `browser_chatgpt`
- `browser_gemini`

A runtime is the execution environment used by an adapter:

- `powershell`
- `wsl`
- `browser_profile`
- `ollama_http`

Adapters remain task-specific. Runtimes remain process/session-specific. A Codex adapter may run through a PowerShell runtime, while a local Ollama adapter may run through an HTTP runtime. The safety layer gates both.

## Proposed Runtime Directory Structure

Canonical root:

```text
runtime/
  sessions/
    <session_id>/
      session.yaml
      stdout.log
      stderr.log
      transcript.log
      heartbeat.json
      adapter_runs/
      locks/
```

Session directories are workstation runtime artifacts. They should not store product artifacts, raw secrets, model weights, browser cookies, or unbounded shell output.

## Session Manifest Schema

`runtime/sessions/<session_id>/session.yaml` should contain:

- `session_id`
- `runtime_type`
- `adapter`
- `cwd`
- `shell`
- `allowed_targets`
- `allowed_safety_modes`
- `allowed_commands`
- `env_policy`
- `status`
- `pid`
- `started_at`
- `last_seen_at`
- `transcript_path`
- `current_exchange_id`
- `stop_conditions`

Recommended status values:

- `PLANNED`
- `STARTING`
- `ACTIVE`
- `IDLE`
- `BLOCKED`
- `FAILED`
- `STOPPED`
- `STALE`

## Planned Session Commands

Plan these commands only; do not implement yet:

- `ws session-list`
- `ws session-status <session_id>`
- `ws session-plan --dry-run`
- `ws session-start --session <session_id> --confirm`
- `ws session-stop --session <session_id> --confirm`
- `ws session-cleanup --dry-run`

Initial safety classification proposal:

- `ws session-list`: `PURE_READ`
- `ws session-status`: `PURE_READ`
- `ws session-plan --dry-run`: `DRY_RUN_ONLY`
- `ws session-start --confirm`: `PROVIDER_CALL` when the session starts a provider-backed adapter, otherwise `GUARDED_WRITE`
- `ws session-stop --confirm`: `GUARDED_WRITE`
- `ws session-cleanup --dry-run`: `DRY_RUN_ONLY`

The classification must be finalized from source evidence when implemented.

## Exchange Integration

Future dispatch command shape:

```text
ws exchange-dispatch --exchange <id> --target codex_cli --runtime powershell --confirm
```

Expected flow:

1. Load `exchange/<exchange_id>/exchange.yaml`.
2. Validate target, safety mode, status, and result/import state.
3. Validate runtime request, such as `powershell`.
4. Select or create a session manifest.
5. Write the adapter prompt into the exchange adapter run directory.
6. Start or reuse a controlled runtime session.
7. Run only the approved adapter invocation.
8. Capture stdout, stderr, transcript, return code, timing, and sanitized command line.
9. Write adapter run artifacts under `exchange/<exchange_id>/adapter_runs/<adapter>/<run_id>/`.
10. Do not import result automatically.

`ws exchange-import-result --confirm` remains the explicit result-import gate.

## Safety Rules

The runtime layer must not become arbitrary shell access.

Required rules:

- No generic arbitrary PowerShell execution.
- No model-chosen shell commands.
- Sessions only run adapter commands derived from validated exchange packets.
- If command execution is ever allowed, every command must be known in `registry/ws_command_safety.yaml`.
- PowerShell runtime cannot bypass `registry/ws_command_safety.yaml`.
- Adapter output is untrusted until imported and validated.
- Do not store secrets in transcripts.
- Do not inspect `.env`, credential, token, key, or secret-like files.
- Browser automation must not be launched from PowerShell unless a later command is explicitly classified.
- Runtime sessions must not modify product artifacts unless a future Product Lane command explicitly permits it.
- No returned model output may be executed directly.

## Runtime Modes

Three runtime modes should be planned:

- One-shot process mode: start a process for one adapter run, capture output, exit.
- Long-lived session mode: keep a named session alive for repeated bounded dispatches.
- Detached background process mode: start and monitor a process that may outlive the initiating CLI call.

Recommended first implementation:

Start with one-shot process mode for Codex and Gemini dispatch. It is easier to audit, easier to test with fake executors, and has fewer stale-session failure modes. Add long-lived sessions only after one-shot dispatch has proven insufficient.

## Windows / WSL Split

The workstation currently routes `scripts/ws` through Bash/WSL, while some adapters may need PowerShell.

Runtime config must explicitly define path style:

- Windows root: `D:\_ai_brain`
- WSL root: `/mnt/d/_ai_brain`

Rules:

- No implicit path conversion without validation.
- Store both Windows and WSL forms where needed.
- Validate that converted paths resolve under the workstation root.
- Never pass unchecked user paths into PowerShell command lines.
- Prefer structured arguments over composed command strings.

## Three-Lane Replacement

Current manual PowerShell windows should become managed runtime sessions such as:

- `codex_product_lane`
- `gemini_product_lane`
- `codex_exchange_lane`

Planned mapping:

- `codex_product_lane`: Codex review or implementation tasks sourced from Product Lane artifacts.
- `gemini_product_lane`: Gemini review/planning tasks sourced from Product Lane artifacts.
- `codex_exchange_lane`: Exchange packets, adapter previews, dispatches, and result capture.

The operator should inspect session status and reports, not keep terminals arranged manually.

## Logging And Audit

Each runtime session or one-shot run should record:

- `stdout.log`
- `stderr.log`
- `transcript.log`
- `adapter_run.yaml`
- `command_line_sanitized`
- `return_code`
- `started_at`
- `ended_at`
- `timeout`
- `cwd`
- `runtime_type`
- `adapter`
- `exchange_id`

Transcripts must avoid secrets and should be scoped to the adapter command, not full interactive shell history.

## Failure Handling

The runtime layer must handle:

- timeout
- nonzero exit
- lost process
- invalid output format
- partial adapter run
- duplicate run
- stale lock

Recommended policy:

- Timeout writes a failed adapter run record and does not import result.
- Nonzero exit writes stdout/stderr and marks adapter run `FAILED` or exchange `BLOCKED`.
- Lost process marks session `STALE` and requires cleanup.
- Invalid output format is handled by result import validation, not by execution.
- Partial adapter run requires a repair/status command before retry.
- Duplicate run is blocked unless an explicit archive/retry workflow exists.
- Stale locks are reported by cleanup dry-run before confirm cleanup is implemented.

## Phase Plan

Phase 0: runtime/session plan only.

Phase 1:

- session manifest helper
- `ws session-list`
- `ws session-status`
- no process start

Phase 2:

- one-shot PowerShell dispatch preview
- no execution
- path and command-line validation

Phase 3:

- guarded one-shot Codex/Gemini execution through PowerShell
- fake executor tests
- bounded logs and adapter run artifacts

Phase 4:

- long-lived sessions if needed
- heartbeat and stale-lock handling

Phase 5:

- browser runtime adapters
- dedicated browser profiles
- allowed domains only
- no shell execution from browser output

## Tests Needed Later

Planned tests:

- session manifest validation
- session id validation
- path boundary checks for Windows and WSL roots
- no writes outside `runtime/`
- no arbitrary shell command accepted
- one-shot preview writes no process artifacts
- fake executor for PowerShell dispatch
- timeout handling
- nonzero exit handling
- stale lock detection
- no product artifact writes
- no result import during dispatch
- check_local_safety integration

## Recommendation

Implement Phase 1 next: a deterministic session manifest helper plus pure-read `session-list` and `session-status`. Keep process start out of the first implementation so the runtime inventory can be validated before any PowerShell execution path exists.
