# Phase 8.3.1 Learning Cockpit Decision Freshness Fix

## Problem

The first Learning Cockpit preview treated normal and review decision reports as one globbed set. Because `learning_review_decision_*` sorts after `learning_decision_*` lexically, an older review-cycle `ADVANCE_TO_NEXT_TASK` artifact could be displayed and used ahead of a newer normal-cycle decision for the current task.

Observed unsafe preview before the fix:

- current task: `Format dataset as JSONL`
- latest normal assessment: `assessment_20260518_155142.md`
- latest normal decision: `learning_decision_20260518_155149.md`
- older review decision incorrectly surfaced: `learning_review_decision_20260518_142127.md`
- previewed command: `ws learning-advance fine-tuning-small-open-source-models`

## Changes Made

- Split normal and review decision handling into separate artifact lanes.
- Resolve decision reports from `state.json` timestamps first, with filename scanning only as a fallback.
- Added freshness comparison for:
  - tutor session
  - imported answers
  - normal assessment
  - normal decision
  - review tutor session
  - review answers
  - review assessment
  - review decision
- Suppress `learning-advance` unless the review decision is:
  - `ADVANCE_TO_NEXT_TASK`
  - newer than its review assessment
  - newer than the latest normal-cycle artifacts
- Prefer `Run learning decision` when a normal assessment is newer than its normal decision.
- Prefer `Generate targeted review session` when the latest normal decision is `REVIEW_CURRENT_TASK` and there is no fresh review cycle for that decision.
- Added visible stale-decision warning text:
  - `Decision artifact may be stale; advancement preview suppressed.`

## Files Changed

- `tui/app.py`
- `tui/README.md`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_8_3_1_LEARNING_COCKPIT_DECISION_FRESHNESS_FIX.md`

## Validation Run

Completed:

- `python3 -m py_compile tui/app.py`
- `ws tui --snapshot`
- `ws tui --plain`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Observed results:

- Snapshot mode now shows the normal decision report `learning_decision_20260518_155149.md`.
- The older review decision remains visible separately as `learning_review_decision_20260518_142127.md`.
- The cockpit prints `Decision artifact may be stale; advancement preview suppressed.`
- The current recommendation is `Generate targeted review session`.
- The current preview is `ws learning-review-session fine-tuning-small-open-source-models --dry-run`.
- Plain mode inspection of the Learning Cockpit produced the same recommendation and no `learning-advance` preview.

## Expected Current-State Result

For `fine-tuning-small-open-source-models`, the cockpit should now show:

- normal decision: `learning_decision_20260518_155149.md`
- stale older review decision as a separate artifact
- warning that the old review decision may be stale
- recommended next action: `Generate targeted review session`
- command preview: `ws learning-review-session fine-tuning-small-open-source-models --dry-run`

## Limitations

- The cockpit remains read-only plus command preview only.
- It does not execute learning commands.
- It still reads existing stronghold metadata rather than introducing a dedicated backend JSON status command.

## Next Step

After this freshness fix is validated, Phase 8.3 can continue to harden the read-only cockpit surface before any future phase considers action execution.
