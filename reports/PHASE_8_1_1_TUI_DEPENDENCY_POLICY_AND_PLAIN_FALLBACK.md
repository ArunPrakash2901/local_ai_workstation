# Phase 8.1.1 TUI Dependency Policy And Plain Fallback

## Option C Decision

Option C is now the explicit TUI policy:

- snapshot mode must always work
- plain mode must always work without third-party dependencies
- Textual remains optional
- no dependency installation is performed automatically

This keeps the operator dashboard available even when the richer TUI dependency is not installed, while preserving a future path for a better interface through an approved install process.

## Files Changed

- `tui/app.py`
- `tui/README.md`
- `scripts/ws_tui.sh`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_8_1_1_TUI_DEPENDENCY_POLICY_AND_PLAIN_FALLBACK.md`

## Command Behavior

- `ws tui --snapshot` prints the read-only dashboard and exits.
- `ws tui --plain` launches a stdlib-only line-based dashboard with:
  - `r` refresh
  - `h` help
  - `q` quit
- `ws tui` uses Textual when it is already installed and otherwise falls back to plain mode with a clear notice.
- `ws tui --textual` requires Textual and exits safely with a clear install-policy message when Textual is unavailable.

All modes continue to use the same explicit read-only allowlist:

- `ws ready`
- `ws stronghold-status`
- `ws handoff-status`
- `ws feature-status`
- `ws agent-hygiene`

## Why Plain And Snapshot Must Always Work

The cockpit is an operator surface for core workstation visibility. Health checks should not disappear merely because an optional presentation dependency is missing. Snapshot mode is also useful for scripting and smoke validation, while plain mode preserves interactive use in a minimal environment.

## Why Textual Is Optional

Textual improves ergonomics, but it is not required for correctness or safety. Keeping it optional prevents automatic package installation, avoids hidden dependency drift, and keeps the stable read-only path independent from future UI experimentation. The approved future path is a dedicated virtual environment or another documented install process.

## Validation Run

Completed:

- `bash -n scripts/ws`
- `bash -n scripts/ws_tui.sh`
- `python3 -m py_compile tui/app.py`
- `python3 tui/app.py --snapshot`
- `printf 'q\n' | python3 tui/app.py --plain`
- `python3 tui/app.py --textual`
- `ws tui --snapshot`
- `printf 'q\n' | ws tui --plain`
- `ws tui --textual`
- `printf 'q\n' | ws tui`
- `ws ready`
- `ws stronghold-status`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Observed results:

- Snapshot mode printed the full read-only dashboard.
- Plain mode opened, showed controls, and exited cleanly with `q`.
- Textual is not installed in the current environment; `--textual` returned the approved clear message without traceback.
- Default `ws tui` detected missing Textual and fell back to plain mode with a clear notice.
- Readiness, stronghold status, and agent hygiene commands all completed successfully after sequential rerun.

## Current Limitations

- The cockpit is still read-only.
- Plain mode is intentionally line-based rather than curses-based.
- Textual remains optional and unmanaged by the workstation.
- Learning, research, provider execution, mutation, browser automation, Graphify UI, and trading automation remain out of scope.

## Next Recommended Phase

Phase 8.2 should define and implement the Learning cockpit on top of the now-stable dependency policy, while keeping execution boundaries and human approval gates explicit.
