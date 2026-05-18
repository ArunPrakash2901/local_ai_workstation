# Phase 8.1: TUI Read-Only Dashboard Implementation

Date: 2026-05-18

## Summary

Phase 8.1 adds the first operator cockpit entry point:

- `ws tui`
- `ws tui --snapshot`

The milestone is intentionally read-only. It only gathers the existing stable status outputs needed for an operator dashboard and does not expose learning, research, provider, mutation, browser, Graphify, or trading actions.

## Files Changed

- `scripts/ws`
- `scripts/ws_tui.sh`
- `tui/app.py`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_8_1_TUI_READ_ONLY_DASHBOARD_IMPLEMENTATION.md`

## Command Behavior

`ws tui` launches `tui/app.py` through the wrapper script.

The dashboard allowlists only:

- `ws ready`
- `ws stronghold-status`
- `ws handoff-status`
- `ws feature-status`
- `ws agent-hygiene`

The dashboard displays:

- workstation readiness summary
- stronghold list
- recent handoffs
- recent feature strongholds
- agent hygiene summary
- current safety mode: `READ_ONLY`
- disabled-action notes
- a visible in-memory command log

Keyboard bindings in interactive mode:

- `r` refresh
- `q` quit
- `?` toggle help

`python3 tui/app.py --snapshot` and `ws tui --snapshot` print the same data as plain text for smoke testing and non-interactive use.

## Textual Availability Behavior

The app prefers Textual when installed. No package installation is attempted.

If Textual is unavailable and interactive mode is requested, the app exits cleanly with:

```text
Textual is not installed. Install later with the approved dependency process.
```

The snapshot mode does not require Textual.

## Validation Run

Commands run:

```bash
bash -n scripts/ws
bash -n scripts/ws_tui.sh
python3 -m py_compile tui/app.py
python3 tui/app.py --snapshot
ws tui --snapshot
ws ready
ws stronghold-status
ws handoff-status
ws feature-status
ws agent-hygiene
git status --short
git diff --stat
```

Observed environment:

- `Textual` was not installed in the current WSL Python environment.
- Snapshot mode remained available and produced the read-only dashboard output.
- `ws tui --snapshot` successfully routed through the new dispatcher path.
- `ws tui` without `--snapshot` exited cleanly with the approved Textual-missing message.
- `ws ready`, `ws stronghold-status`, `ws handoff-status`, `ws feature-status`, and `ws agent-hygiene` all completed successfully.

## Current Limitations

- no Learning cockpit
- no Research cockpit
- no command execution buttons
- no provider or browser actions
- no Graphify UI
- no mutation/apply behavior
- no worktree actions
- no trading automation

The app does not read secrets or unsafe folders by default; it obtains dashboard state only through the allowlisted `ws` status commands.

## Next Recommended Phase

Phase 8.2: Learning cockpit design/implementation.
