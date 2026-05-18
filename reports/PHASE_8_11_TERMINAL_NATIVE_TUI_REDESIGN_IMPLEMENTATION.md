# Phase 8.11 Terminal-Native TUI Redesign Implementation

## Summary

Phase 8.11 redesigns stdlib plain mode to feel more like a terminal-native operator console and less like a web dashboard rendered as text. The backend execution boundary remains unchanged.

## Files Changed

- `tui/app.py`
- `tui/README.md`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_8_11_TERMINAL_NATIVE_TUI_REDESIGN_IMPLEMENTATION.md`

## Behavior Implemented

- Added responsive layout selection using `shutil.get_terminal_size()`:
  - wide: status line with sidebar plus main content
  - medium: compact menu plus main content
  - narrow: single-column compact layout
- Removed fixed terminal width assumptions from the main plain-mode shell.
- Reworked the Learning screen around terminal-native sections:
  - current focus
  - next action
  - evidence / provenance
  - artifact shortcuts
  - recent learning events
  - human actions
- Replaced website-like dashboard card language with compact terminal sections and status-oriented copy.
- Added icon policy with `WS_TUI_ICONS=ascii|unicode|auto`.
- Preserved ASCII-safe fallbacks for conservative terminals and captured logs.
- Kept backend commands hidden by default and exposed them only through the command drawer.
- Shortened normal evidence display to relative artifact names and paths where practical.
- Updated home controls to feel like app navigation:
  - `[1] Learning`
  - `[2] Artifacts`
  - `[3] System`
  - `[r] Refresh`
  - `[?] Help`
  - `[q] Quit`
- Kept disabled actions human-readable:
  - local-model actions explain that they require a future phase
  - answer imports explain the missing file-picker dependency
  - advancement explains the approval boundary

## Safety Preserved

- No backend command was added.
- The execution allowlist was not expanded.
- The current non-allowlisted `Start review tutor` action remains disabled.
- Existing confirmation flow for approved dry-runs is preserved:
  - human action first
  - risk class
  - expected writes
  - backend command hidden until requested
  - explicit `y/N`
- Snapshot mode still works.

## Validation Run

Completed:

- `python3 -m py_compile tui/app.py`
- direct local syntax compile of `tui/app.py`
- direct local icon-policy probe for `ascii` and `unicode`
- direct local layout probe for widths `120`, `90`, and `60`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Attempted but blocked by WSL service instability during this run:

- `WS_TUI_ICONS=ascii ws tui --plain`
- `WS_TUI_ICONS=unicode ws tui --plain`
- `ws tui --snapshot`
- live narrow-width `COLUMNS=60` validation
- `ws ready`

Observed blocker:

- repeated `wsl bash` launches hung or timed out after earlier concurrent validation attempts
- `wsl --shutdown` also timed out while trying to clear the stalled WSL state

Because of that environment issue, the live interactive redraw path still needs to be re-run once WSL is healthy again.

## Limitations

- Stdlib plain mode still redraws full screens rather than using retained widgets.
- The artifact browser remains line-input driven.
- Long backend commands can still be verbose when intentionally revealed.
- Textual remains a future optional enhancement, not part of this phase.

## Next Step

Run a short usability review on the terminal-native shell before considering any expansion into local tutor execution.

## Validation Addendum: Phase 8.11 Live Plain-Mode Startup Fix

### Root Cause

- `run_plain_mode()` collected all dashboard status commands before printing the first screen.
- `run_status_command()` had no subprocess timeout, so if any status command stalled (`ws ready` was the highest-risk path), plain mode could appear blank/stuck.
- During this validation window, the host also had shell-runtime degradation:
  - WSL `bash` calls returned `Bash/Service/CreateInstance/E_ACCESSDENIED`.
  - Git Bash launches also failed with Win32 error 5.
- Result: both a real TUI startup-path risk (fixed) and an environment/runtime issue (external).

### Exact Fix Applied

- Updated `tui/app.py`:
  - print immediate visible startup text in plain mode before status collection:
    - `plain mode [READ_ONLY] initializing dashboard...`
    - `Collecting status commands with timeout protection.`
  - add per-command timeout for dashboard status commands via `subprocess.run(..., timeout=...)`
  - add timeout classification:
    - command result returns code `124`
    - stderr includes `[TIMEOUT] ws <command> did not complete within <N>s`
    - timeout event is appended to the command log
  - add launch-failure classification for command startup errors (`OSError`) without crashing the TUI
  - add debug mode `WS_TUI_DEBUG=1` with phase traces:
    - starting app
    - parsing args
    - rendering header
    - collecting status
    - entering plain loop
    - waiting for input
  - add clean KeyboardInterrupt exits:
    - startup interrupt path
    - input-loop interrupt path
    - top-level safe exit
  - harden icon rendering:
    - if `WS_TUI_ICONS=unicode` is set but stdout encoding cannot render unicode, automatically fall back to ASCII instead of crashing

### Timeout Behavior

- Status command timeout is now bounded and configurable with:
  - `WS_TUI_STATUS_TIMEOUT` (seconds, default `12`, clamped to `1..120`)
- A stalled status command no longer blocks the whole dashboard indefinitely.

### Validation Commands And Results

Executed successfully in current environment:

- `python3 -m py_compile D:\_ai_brain\tui\app.py` (using `PYTHONPYCACHEPREFIX=%TEMP%` due pycache ACL)
- `python D:\_ai_brain\tui\app.py --snapshot`
- `echo q | python D:\_ai_brain\tui\app.py --plain`
- `WS_TUI_ICONS=ascii` plain probe (direct Python): pass
- `WS_TUI_ICONS=unicode` plain probe (direct Python): pass with safe ASCII fallback on CP1252 console
- `WS_TUI_DEBUG=1` plain probe (direct Python): pass; phase trace printed

Attempted but blocked by shell runtime (external):

- `bash -n scripts/ws`
- `bash -n scripts/ws_tui.sh`
- `bash scripts/ws tui --snapshot`
- `echo q | bash scripts/ws tui --plain`
- `WS_TUI_ICONS=ascii/unicode` via `bash scripts/ws ...`
- `ws ready`
- `ws agent-hygiene`

Observed external blocker on blocked commands:

- `Bash/Service/CreateInstance/E_ACCESSDENIED` (WSL bash path)
- Git Bash process startup failures (Win32 error 5)

### Remaining Gaps

- End-to-end wrapper-path validation (`ws tui --plain`) still needs one clean rerun after shell runtime health is restored.
- Timeout branch was implemented and verified by code path inspection; live timeout-case simulation was not possible in this degraded shell state because bash failed immediately rather than hanging.

## Addendum: Phase 8.11.1 Readiness Badge And Timeout Output Cleanup

### Bugs Confirmed

- Readiness badge bug:
  - top cockpit status could display `READY` when `ws ready` returned `[FAIL]` lines, because the badge logic only checked `returncode == 0`.
- Timeout output bug:
  - timeout partial output could render as raw Python byte repr values like `b'Running daily readiness check...\n'`.

### Fix Applied

- Updated `tui/app.py`:
  - added readiness classifier used by both plain header and snapshot readiness section:
    - `TIMEOUT` when `ws ready` timed out (`returncode 124`)
    - `CHECK` when `ws ready` exited nonzero
    - `DEGRADED` when `ws ready` exited zero but output contained `[FAIL]`
    - `READY` only when `ws ready` exited zero and had no `[FAIL]`
  - added subprocess output normalization for `stdout`/`stderr` and timeout partial buffers, decoding bytes safely before display
  - updated timeout rendering so readiness output starts with:
    - `[TIMEOUT] ws ready did not complete within <N>s`
    - followed by clean partial output when available
  - normalized status command log entries to include timestamp + outcome + command:
    - `OK`, `FAIL`, or `TIMEOUT`

### Validation Results (2026-05-18)

- `python3 -m py_compile tui/app.py` passed (run with `PYTHONPYCACHEPREFIX=%TEMP%` due existing `__pycache__` ACLs).
- Healthy readiness path:
  - `ws ready` returned `[OK]`/`[INFO]` and no `[FAIL]`.
  - `ws tui --snapshot` showed `Workstation Readiness (READY)`.
  - `printf 'q\n' | timeout 30s ws tui --plain` showed `Operator Cockpit | ✓ READY`.
- Timeout path (forced via `WS_TUI_STATUS_TIMEOUT=1`):
  - snapshot showed `Workstation Readiness (TIMEOUT)`.
  - plain mode showed `Operator Cockpit | ⚠ TIMEOUT` (not `READY`).
  - readiness section showed clean timeout message plus partial output.
- No raw `b'...'` byte repr appeared in timeout output.
- Direct classifier check with synthetic zero-exit readiness output containing `[FAIL]` returned `DEGRADED` (not `READY`).
