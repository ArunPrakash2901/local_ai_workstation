# Exchange Lane (Phase 0)

`exchange/` is the canonical root for Exchange Lane packet artifacts.

Phase 0 scope:

- Create deterministic packet files.
- Preview packet metadata in dry-run mode.
- List and inspect packet status.

Phase 0 does not:

- Dispatch packets.
- Execute shell commands from packet content.
- Call Codex, Gemini, Ollama, browser automation, MCP, providers, or agents.

Phase 1 Slice 1 adds a no-execution dispatch gate:

- `ws exchange-dispatch --exchange <exchange_id> --dry-run`

Dispatch preview behavior:

- Validates packet dispatch readiness only.
- Does not execute adapters or allowed commands.
- Does not call models, providers, agents, browser automation, or MCP.
- Does not write result artifacts (`raw_output.md`, `parsed_result.json`, `validation.md`, `operator_report.md`).

Phase 1 Slice 3 adds a Codex adapter preview gate:

- `ws exchange-adapter-preview --exchange <exchange_id> --target codex_cli --dry-run`
- Preview-only invocation planning; Codex CLI is not executed.
- Shows planned prompt/input path and planned future output capture path.
- Includes runtime-session integration preview metadata when matching planned sessions exist.
- Validates packet/target safety preconditions and `allowed_commands` manifest coverage.
- Writes no files and does not execute adapters, models, providers, browser automation, or MCP.

Phase 1 Slice 4 adds guarded Codex REVIEW_ONLY dispatch:

- `ws exchange-dispatch --exchange <exchange_id> --target codex_cli --confirm`
- REVIEW_ONLY only, codex_cli only, and blocked unless strict preconditions pass.
- Writes bounded adapter run artifacts under `exchange/<exchange_id>/adapter_runs/codex_cli/<run_id>/`.
- Does not write `raw_output.md`, `parsed_result.json`, `validation.md`, or `operator_report.md`.
- Does not auto-import results; `ws exchange-import-result --confirm` remains explicit and separate.
- Does not execute commands from model output and does not write product artifacts.

Result import behavior (Phase 1 Slice 2):

- `ws exchange-import-result --exchange <exchange_id> --file <result_file> --dry-run` validates import and planned writes.
- `ws exchange-import-result --exchange <exchange_id> --file <result_file> --confirm` writes result artifacts under `exchange/<exchange_id>/`.
- Imported text is untrusted and never executed.
- No model/provider/agent/browser/MCP calls occur during import.

Packet directory layout for Phase 0:

- `exchange/<exchange_id>/exchange.yaml`
- `exchange/<exchange_id>/prompt.md`
- `exchange/<exchange_id>/source_artifacts.md`
- `exchange/<exchange_id>/allowed_commands.md`
- `exchange/<exchange_id>/forbidden_actions.md`
- `exchange/<exchange_id>/expected_outputs.md`
- `exchange/<exchange_id>/run_log.md`

Operator role:

- Approve/reject packet creation and packet content.
- Manual copy/paste between platforms is not the target workflow.
- Future adapters will read packet artifacts and write bounded results back.
