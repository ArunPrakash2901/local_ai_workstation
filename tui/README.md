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
- **Plain-Mode Visual Shell**: Header, sidebar, breadcrumbs, cards, human-readable actions, hidden backend-command drawer, and confirmation prompts built with the Python standard library only.
- **Learning Cockpit**: Dedicated view for learning strongholds, including progress tracking, artifact provenance, freshness-aware decision selection, stale-decision warnings, read-only artifact viewing, and plain-mode execution of allowlisted BLUE dry-run planners only.
- **Agent Hygiene**: Summary of Git worktrees and auto-run folders.
- **Handoff Status**: List of recent frontier escalation packets.

## Safety
Snapshot mode remains strictly **READ-ONLY**. Plain mode keeps human actions in the foreground and backend `ws` commands hidden until the operator asks to reveal them. It can execute only the hardcoded safe dry-run planner actions `learning-run --session --dry-run` and `learning-review-session --dry-run`; model execution, assessment, import, and advancement remain disabled. Learning Cockpit previews suppress stale advancement suggestions when normal and review artifacts are out of order.
