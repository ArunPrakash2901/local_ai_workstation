# Operator TUI

The operator TUI is intentionally read-only. It uses the same allowlisted workstation status commands in every mode:

- `ws ready`
- `ws stronghold-status`
- `ws handoff-status`
- `ws feature-status`
- `ws agent-hygiene`

## Dependency Policy

Option C is the current policy:

- `--snapshot` and `--plain` must remain dependency-free and available with the Python standard library alone.
- Textual is optional and must not be installed automatically.
- `ws tui` should use Textual when it is already available and otherwise fall back to plain mode.
- `ws tui --textual` may require Textual, but it must fail safely with a clear message if the dependency is missing.
- Any future Textual installation should use a dedicated virtual environment or another documented, approved dependency process.

The dashboard does not read unsafe folders by default, including `.env`, credentials, raw datasets, model files, archives, or `.git`.

## Features
- **Workstation Readiness**: Live check of Ollama, RTX GPU, and environment.
- **Stronghold Status**: Overview of active cognitive workspaces.
- **Learning Cockpit**: Dedicated read-only view for learning strongholds, including progress tracking, artifact provenance, and next-action command previews.
- **Agent Hygiene**: Summary of Git worktrees and auto-run folders.
- **Handoff Status**: List of recent frontier escalation packets.

## Safety
The dashboard is strictly **READ-ONLY**. It does not invoke providers, mutate project files, or execute automated tasks. Command previews are provided for convenience but must be run manually by the operator.
