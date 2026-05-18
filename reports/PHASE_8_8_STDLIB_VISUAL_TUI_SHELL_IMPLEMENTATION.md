# Phase 8.8 Stdlib Visual TUI Shell Implementation

## Summary

Phase 8.8 keeps the existing backend safety boundary intact and improves only the stdlib plain-mode presentation. The TUI now behaves more like an application shell and less like a formatted command transcript.

## Files Changed

- `tui/app.py`
- `tui/README.md`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_8_8_STDLIB_VISUAL_TUI_SHELL_IMPLEMENTATION.md`

## Behavior Implemented

- Added a visual plain-mode shell with:
  - application header
  - safety badges
  - navigation sidebar
  - breadcrumbs
  - card-style content blocks
  - bottom status/log drawer
- Added Home, Learning, Handoffs, and System Health plain-mode screens.
- Reworked the Learning screen into operator-facing cards:
  - Current Task
  - Recommended Action
  - Provenance
  - Latest Artifacts
  - Safety
- Replaced command-first controls with numbered human actions:
  - Run Safe Dry-Run
  - View Latest Plan
  - View Latest Assessment
  - Show Backend Command
  - Refresh
  - Back
- Hid backend commands by default and exposed them only through an explicit drawer action.
- Updated the confirmation flow so the backend command is hidden until the operator asks to reveal it.
- Added a safe markdown artifact viewer for the latest plan or assessment.
- Restricted artifact viewing to markdown files that resolve inside the selected learning stronghold and reject blocked path segments.
- Preserved stale-decision warnings, provenance state, snapshot behavior, and the existing dry-run-only execution allowlist.

## What Did Not Change

- No new backend command was added.
- No execution path was widened.
- The only executable learning actions remain:
  - `ws learning-run <id> --session --dry-run`
  - `ws learning-review-session <id> --dry-run`
- Model-backed actions, assessment, import, decision, advance, provider calls, browser automation, and research cockpit actions remain disabled.

## Validation Run

Completed:

- `python3 -m py_compile tui/app.py`
- `ws tui --snapshot`
- `ws tui --plain`
  - opened Learning
  - revealed the backend command drawer
  - viewed the latest plan
  - confirmed the current non-allowlisted action remains disabled
  - quit safely
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Observed:

- Snapshot mode remained text/report oriented and read-only.
- Plain mode now presents an app shell instead of a command dump.
- The currently recommended action is preview-only, so the run control correctly reports:
  - `Action requires manual command / future phase`
- No new TUI execution report was generated during this validation because the current recommendation was not in the allowlist.

## Limitations

- Plain mode still focuses on the first discovered learning stronghold.
- Navigation is line-input based rather than widget based.
- Artifact viewing is markdown-only and terminal-print based.
- Textual remains optional and unchanged.

## Next Recommended Phase

Design the next Learning Cockpit interaction milestone around richer selection and form flows before enabling any new action classes.
