# Phase 8.10 Learning Artifact Viewer Implementation

## Summary

Phase 8.10 improves the plain-mode Learning Cockpit evidence workflow without changing the workstation execution boundary. The Learning screen now includes a read-only artifact catalog and a paged markdown viewer so the operator can inspect learning evidence inside the TUI.

## Files Changed

- `tui/app.py`
- `tui/README.md`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_8_10_LEARNING_ARTIFACT_VIEWER_IMPLEMENTATION.md`

## Behavior Implemented

- Added a Learning artifact catalog covering:
  - latest session plan
  - latest tutor session
  - latest answer template
  - latest human answers
  - latest assessment
  - latest decision
  - latest review plan
  - latest review tutor session
  - latest review answer template
  - latest review answers
  - latest review assessment
  - latest review decision
  - progress log
  - practice log
- Each catalog row now shows:
  - human label
  - `exists` or `missing`
  - relative path
  - derived timestamp when available
- Added a paged read-only markdown viewer:
  - default page size: 80 lines
  - `n` next page
  - `p` previous page
  - `a` show all
  - `b` back
- Added a visible manual copy-path instruction without introducing clipboard automation.
- Routed the existing latest-plan and latest-assessment quick actions through the same improved viewer path.

## Safety Preserved

- No backend command capability was added.
- The execution allowlist was not expanded.
- The viewer only opens markdown files under the selected learning stronghold.
- Paths outside the selected stronghold are refused.
- Unsafe paths remain blocked:
  - `.env`
  - credentials
  - raw datasets
  - model files
  - archives
  - `.git`

## Validation Run

Completed:

- `python3 -m py_compile tui/app.py`
- `ws tui --plain`
  - opened Learning
  - opened Artifact Viewer
  - viewed latest plan
  - paged through an artifact
  - viewed latest assessment
  - inspected the artifact catalog for missing entries
  - backed out and quit
- `ws tui --snapshot`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

## Limitations

- Plain mode still targets the first discovered learning stronghold.
- The viewer is line-oriented and markdown-aware only by convention, not by rich rendering.
- Artifact selection is numeric rather than cursor-driven.
- Copy-path support is instructional only; no clipboard behavior was added.
- The current learning stronghold had no missing artifact slot during validation, so missing-entry behavior was not exercised interactively in this run.

## Next Step

Review whether the improved evidence workflow is sufficient before designing any local tutor execution path.
