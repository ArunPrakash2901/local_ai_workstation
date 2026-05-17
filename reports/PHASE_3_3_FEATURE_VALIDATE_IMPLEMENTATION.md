# Phase 3.3: Feature Validate Implementation

Date: 2026-05-17

## Summary

Phase 3.3 adds the first local-only feature validation command:

- `ws feature-validate <feature_id_or_path>`

The command inspects an existing Feature Stronghold plus local repository/readiness evidence only. It does not run providers, agents, browser automation, apply behavior, worktree execution, or project mutations.

## Files Changed

- `scripts/ws`
- `scripts/ws_feature_validate.sh`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_3_3_FEATURE_VALIDATE_IMPLEMENTATION.md`

## Command Added

```bash
ws feature-validate <feature_id_or_path>
```

## Behavior Implemented

`ws feature-validate`:

- resolves a stronghold by direct path or exact feature id under `features/<project>/<feature>/`
- reads:
  - `state.json`
  - `feature_contract.md`
  - `acceptance_criteria.md`
  - `allowed_files.md`
  - `validation_plan.md`
  - `current_plan.md`
- validates:
  - required feature files exist
  - state is `CREATED` or `LOCAL_PLAN_READY`
  - allowed files are explicit
  - source task exists
  - repo path exists
  - repo is a Git repo
  - repo status is clean
  - current branch and commit are recorded
  - a local readiness report exists
  - `provider_invocation` remains `false`
  - `browser_automation` remains `false`
- writes:
  - `evidence/validation_<timestamp>.md`
- appends a validation event to `loop_log.md`
- updates `state.json` with:
  - `current_state: VALIDATED_LOCAL` on pass
  - `current_state: BLOCKED` on fail
  - `last_validated_at`
  - `validation_result`

The command prints the validation result, feature path, evidence path, final state, and the next safe action.

## Validation Run

Commands run:

```bash
bash -n scripts/ws
bash -n scripts/ws_feature_validate.sh
ws feature-validate /mnt/d/_ai_brain/features/workstation_control_plane/stabilize-ws-command-documentation
ws feature-status
ws ready
ws agent-hygiene
ws worktree-status
git status --short
git diff --stat
```

Observed results:

- both shell syntax checks passed
- `ws feature-validate` created:
  - `D:\_ai_brain\features\workstation_control_plane\stabilize-ws-command-documentation\evidence\validation_20260517_222554.md`
- validation result was `FAIL`
- the stronghold moved from `LOCAL_PLAN_READY` to `BLOCKED`
- the only failed check was `repo status is clean`
- that failure was expected during this implementation run because the workstation repo had uncommitted Phase 3.3 changes:
  - `WORKSTATION_MANUAL.md`
  - `scripts/ws`
  - `scripts/ws_feature_validate.sh`
- all other structural and safety checks passed, including:
  - required files present
  - explicit allowed files
  - source task exists
  - repo path/Git validity
  - recorded branch and commit
  - local readiness report exists
  - provider invocation disabled
  - browser automation disabled
- `loop_log.md` recorded the validation event
- `ws feature-status` showed `BLOCKED`
- `ws ready` passed and wrote `READINESS_20260517_222610.md`
- `ws agent-hygiene` reported `0` unresolved `CODEX_RUNNING` folders
- `ws worktree-status` reported `2` active worktrees and `0` stale-looking directories

## Limitations

- no feature execution loop yet
- no targeted test runner yet
- no acceptance-criteria evaluation beyond contract/readiness checks
- no provider handoff/import path
- no browser automation
- no apply path
- no worktree execution
- after a blocking validation, the current safe recovery path is to resolve the blocker, run `ws feature-plan` again, then re-run validation

## Next Step

Add the next supervised feature-level command later:

- `ws feature-report`

It should summarize the current stronghold state, latest evidence, and next human decision without enabling execution.
