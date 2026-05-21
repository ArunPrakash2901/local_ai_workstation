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
- **Terminal-Native Plain Mode**: Compact status line, active focus panel, next-action section, recent-event stream, artifact shortcuts, hidden backend-command drawer, and keyboard-first actions built with the Python standard library only.
- **Learning Cockpit**: Dedicated view for learning strongholds, including progress tracking, artifact provenance, freshness-aware decision selection, stale-decision warnings, a read-only artifact catalog with paged markdown viewing, and plain-mode execution of allowlisted BLUE dry-run planners only.
- **Agent Hygiene**: Summary of Git worktrees and auto-run folders.
- **Handoff Status**: List of recent frontier escalation packets.

## Safety
Snapshot mode remains strictly **READ-ONLY**. Plain mode keeps human actions in the foreground and backend `ws` commands hidden until the operator asks to reveal them. It can execute only the hardcoded safe dry-run planner actions `learning-run --session --dry-run` and `learning-review-session --dry-run`; model execution, assessment, import, and advancement remain disabled. Learning Cockpit previews suppress stale advancement suggestions when normal and review artifacts are out of order.

The plain-mode Learning artifact viewer lists available session, review, decision, and log artifacts with existence state, relative paths, and timestamps when available. It only opens markdown files under the selected learning stronghold and never reads blocked folders such as `.env`, credentials, raw datasets, model files, archives, or `.git`.

### Safety validation before TUI changes

TUI action visibility, safety labels, warning labels, and confirmation labels are backed by `registry/ws_command_safety.yaml`. Rendering changes must not bypass the existing execution gates: hardcoded status commands and allowlisted learning dry-runs still control what can run.

After changing TUI visibility or safety-label behavior, run the no-write local safety check.

PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python scripts\check_local_safety.py
```

Bash/WSL:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/check_local_safety.py
```

This check validates the command safety manifest, safety invariants, and TUI helper visibility behavior. It uses AST parsing instead of `py_compile`; it does not execute `ws` commands, run agents, run models, call providers, run apply flows, or write reports, caches, or artifacts. Do not use `ws ready` as a strict no-write substitute because it may write local readiness/status reports.

## Terminal-Native Policy

- The TUI should foreground human actions and terminal workflows, not dashboard-style web layout patterns.
- Cockpit information architecture rule: **signal first, details on demand**.
  - Keep top-level screens decision-oriented and compact.
  - Keep verbose diagnostics behind dedicated detail views (for example System Health or artifact viewer).
- Plain mode adapts using `shutil.get_terminal_size()`:
  - wide terminals use a sidebar plus main content area
  - medium terminals collapse to a compact menu plus main content
  - narrow terminals use a single-column layout
- Long text wraps or truncates to avoid horizontal spill where practical.
- Icons are optional and controlled by `WS_TUI_ICONS=ascii|unicode|auto`.
  - `auto` chooses Unicode only when the output encoding supports it.
  - ASCII always remains available for conservative terminals and logs.
