# Runtime Sessions (Phases 1-3)

`runtime/` stores managed runtime session metadata and logs for Exchange Lane orchestration.

Phase 1 scope is manifest/status only:

- session manifest schema and validation
- read-only session listing
- read-only session status inspection

Phase 1 does not start processes:

- no PowerShell process start
- no WSL process start
- no Codex/Gemini/Ollama execution
- no browser automation
- no MCP execution

Phase 2 adds dry-run planning:

- `ws session-plan --session <id> --runtime <type> --adapter <adapter> --dry-run`
- validates runtime/adapter compatibility and previews a managed session manifest
- writes no files and starts no processes

Phase 3 adds guarded planned-session creation:

- `ws session-plan --session <id> --runtime <type> --adapter <adapter> --confirm`
- writes only planned session metadata under `runtime/sessions/<session_id>/`
- creates `session.yaml` plus placeholder logs/heartbeat
- does not start any process and does not run any adapter

`session-start` remains future work.

Runtime readiness preview slice adds dry-run-only previews:

- `ws session-start --session <id> --dry-run` previews preconditions and conceptual runtime invocation.
- `ws session-cleanup --dry-run` previews cleanup candidates and keep/no-action sessions.
- Both remain no-write/no-process execution paths for managed runtime readiness checks.

PowerShell is treated as a managed runtime surface, not arbitrary shell access.

Future phases will treat PowerShell/WSL/browser/Ollama as controlled runtime layers.
The long-term workflow is managed session orchestration, not manual terminal-window coordination by the operator.
