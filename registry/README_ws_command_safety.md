# WS Command Safety Manifest

`ws_command_safety.yaml` is the machine-readable command safety registry for the Local AI Workstation.

The file is JSON-compatible YAML so the TUI can parse it with Python stdlib `json` and still allow YAML tooling to read it.

Source of truth for the current entries: `../WS_COMMAND_SAFETY_MATRIX.md`.

Scope:
- Advisory/display-layer metadata for TUI labels and action visibility.
- Does not change `ws` routing or command behavior.
- Does not authorize execution by itself.
- Unknown, provider-capable, and destructive commands must remain hidden unless future code adds explicit gated modes.

### LOCAL_REPORT_WRITE Boundary Policy

To safely run `LOCAL_REPORT_WRITE` actions directly from the TUI, the manifest uses three specific metadata fields to enforce strict routing boundaries:

- **`tui_dispatch_policy`**: Controls exactly where and how the action can be dispatched from the TUI (`safe_local_report`, `preview_only`, `hidden_local_report`, `system_only`, `learning_only`).
- **`tui_dispatch_allowed`**: A strict boolean override. If `false`, the dispatcher will block execution regardless of the policy.
- **`report_write_scope`**: Defines the blast radius/scope of the report being written (e.g. `readiness`, `hygiene`, `stronghold`, `worktree`). Must be explicit; `unknown` or empty values will block execution.

These fields ensure that broad or unclear report writes are kept strictly as `preview_only` or `hidden_local_report` and that context-specific actions (like system hygiene) cannot be accidentally invoked from unrelated TUI screens.

Required command fields are documented in the manifest and validated by the TUI loader.

Validation:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python scripts/validate_ws_command_safety.py
```

Safe local check path:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python scripts/check_local_safety.py
```
