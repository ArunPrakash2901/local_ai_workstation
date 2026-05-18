# Phase 8.6 Learning Cockpit Safe Dry-Run Execution Implementation

## Summary

Phase 8.6 adds the first controlled execution path to the Learning Cockpit in plain mode only. The TUI can now execute exactly two allowlisted BLUE actions:

- `ws learning-run <id> --session --dry-run`
- `ws learning-review-session <id> --dry-run`

Everything else remains preview-only.

## Files Changed

- `tui/app.py`
- `tui/README.md`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_8_6_LEARNING_COCKPIT_SAFE_DRY_RUN_EXECUTION_IMPLEMENTATION.md`

## Behavior Implemented

- Added `x` in plain mode for the currently recommended safe learning dry-run action.
- Added a hardcoded allowlist for the two approved dry-run planners only.
- Added structured action metadata with:
  - label
  - exact command
  - risk class
  - expected writes
  - executable flag
- Added a refresh-before-execute guard:
  - recompute recommendation
  - compare the refreshed command to the approved preview
  - block if it changed
- Added explicit `y/N` confirmation with:
  - action label
  - exact command
  - `BLUE` risk class
  - expected runtime-only file changes
- Added stdout/stderr capture and visible result display.
- Added visible plain-mode execution log lines.
- Added local execution reports under `reports/TUI_EXECUTION_<timestamp>.md`.
- Added post-execution dashboard refresh and refreshed next-action display.

## What Remains Disabled

- tutor/model-backed learning runs
- assessments
- answer imports
- learning decisions
- learning advance
- providers, browser automation, agent execution, and arbitrary shell commands

## Validation Run

Completed:

- `python3 -m py_compile tui/app.py`
- `ws tui --snapshot`
- `ws tui --plain`
- inspect generated `reports/TUI_EXECUTION_*.md`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Observed results:

- Snapshot mode remained read-only and only rendered state.
- Plain mode exposed `x` and showed the confirmation screen for the allowlisted review-session dry-run.
- Choosing `n` cancelled without execution.
- Choosing `y` executed only:
  - `ws learning-review-session fine-tuning-small-open-source-models --dry-run`
- The backend returned `LEARNING_REVIEW_SESSION_READY`.
- The TUI wrote:
  - `reports/TUI_EXECUTION_20260518_192505.md`
- Post-execution refresh exposed the newly created review session plan and the cockpit now recommends the next preview-only PURPLE step:
  - `Start review tutor`
- Pressing `x` after that state change correctly reports that the recommended action is preview-only and execution is not enabled.

## Limitations

- Execution is plain-mode only.
- The cockpit currently operates on the first discovered learning stronghold.
- The execution report is local Markdown rather than structured JSONL.
- Only BLUE dry-run planner actions are executable.

## Next Step

Run the first dry-run execution validation cycle, then review whether the confirmation, logging, and refresh behavior are sufficient before considering any PURPLE local-model action.
