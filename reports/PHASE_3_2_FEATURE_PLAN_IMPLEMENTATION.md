# Phase 3.2: Feature Plan Implementation

Date: 2026-05-17

## Summary

Phase 3.2 adds the first feature-level planning command:

- `ws feature-plan <feature_id_or_path>`

The command updates an existing Feature Stronghold from local evidence only. It does not run providers, agents, browser automation, apply behavior, worktree creation, or project mutations.

## Files Changed

- `scripts/ws`
- `scripts/ws_feature_plan.sh`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_3_2_FEATURE_PLAN_IMPLEMENTATION.md`

## Command Added

```bash
ws feature-plan <feature_id_or_path>
```

## Behavior Implemented

`ws feature-plan`:

- resolves a feature stronghold by direct path or exact feature id under `features/<project>/<feature>/`
- refuses missing or ambiguous feature ids
- reads:
  - `state.json`
  - `feature_contract.md`
  - `acceptance_criteria.md`
  - `allowed_files.md`
  - `validation_plan.md`
- gathers local-only evidence:
  - repository branch
  - repository commit
  - Git status summary
  - latest readiness report path
  - latest agent hygiene report path
  - latest worktree-status report path
  - source task path
- rewrites `current_plan.md`
- appends a planning entry to `loop_log.md`
- updates `state.json` with:
  - `current_state: LOCAL_PLAN_READY`
  - `last_planned_at`
  - refreshed branch and commit metadata
  - `provider_invocation: false`
  - `browser_automation: false`

The generated plan includes the feature objective, acceptance criteria, allowed files, local evidence, the next safe action, and an explicit statement that no provider or apply path ran.

## Validation Run

Commands run:

```bash
bash -n scripts/ws
bash -n scripts/ws_feature_plan.sh
ws feature-plan /mnt/d/_ai_brain/features/workstation_control_plane/stabilize-ws-command-documentation
ws feature-status
ws ready
ws agent-hygiene
ws worktree-status
git status --short
git diff --stat
```

Observed results:

- both shell syntax checks passed
- `ws feature-plan` updated:
  - `D:\_ai_brain\features\workstation_control_plane\stabilize-ws-command-documentation\current_plan.md`
- `state.json` moved from `CREATED` to `LOCAL_PLAN_READY`
- `state.json` retained:
  - `provider_invocation: false`
  - `browser_automation: false`
- `current_plan.md` now includes:
  - objective
  - acceptance criteria
  - allowed files
  - local Git/report evidence
  - no-provider/no-apply safety statement
- `loop_log.md` recorded local planning events
- `ws feature-status` showed `LOCAL_PLAN_READY`
- `ws ready` passed and wrote `READINESS_20260517_221854.md`
- `ws agent-hygiene` reported `0` unresolved `CODEX_RUNNING` folders
- `ws worktree-status` reported `2` active worktrees and `0` stale-looking directories

## Limitations

- no feature execution loop yet
- no validation runner yet
- no provider handoff or import path yet
- no browser automation
- no apply path
- no worktree execution
- repeated local planning appends another loop-log entry instead of replacing prior history

## Next Step

Add the next supervised feature-level step later:

- `ws feature-validate`

It should evaluate syntax/tests/allowlists and evidence without enabling provider execution or autonomous apply behavior.
