# Phase 3.1: Feature Stronghold MVP

Date: 2026-05-17

## Summary

Phase 3.1 adds the first local-only Feature Stronghold surface:

- `ws feature-new`
- `ws feature-status`

The MVP creates and inspects feature folders only. It does not run agents, apply changes, call providers, automate browsers, create worktrees, or mutate project repositories.

## Files Changed

- `.gitignore`
- `scripts/ws`
- `scripts/ws_feature_new.sh`
- `scripts/ws_feature_status.sh`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_3_1_FEATURE_STRONGHOLD_MVP.md`

## Commands Added

```bash
ws feature-new <project_key> --title "<title>" --from-task <task_file>
ws feature-status
```

## Behavior Implemented

`ws feature-new`:

- resolves the project from `registry/projects.yaml`
- validates the source task file
- derives a stable feature id slug from the title
- captures branch and commit metadata from the registered repo
- extracts:
  - objective
  - acceptance criteria
  - allowed files
  - denied files
  - risk
- creates:
  - `feature_contract.md`
  - `acceptance_criteria.md`
  - `allowed_files.md`
  - `validation_plan.md`
  - `state.json`
  - `loop_log.md`
  - `current_plan.md`
  - `final_report.md`
  - `evidence/`
  - `prompts/`
  - `responses/`
  - `runs/`
  - `handoffs/`
- records:
  - `current_state: CREATED`
  - `provider_invocation: false`
  - `browser_automation: false`

`ws feature-status`:

- scans feature strongholds under `features/<project>/<feature>/`
- reads `state.json`
- lists feature id, project, title, state, and path

`features/` is now ignored by Git because feature strongholds are runtime workspaces that can later contain prompts, responses, run references, and evidence.

## Validation Run

Commands run:

```bash
bash -n scripts/ws
bash -n scripts/ws_feature_new.sh
bash -n scripts/ws_feature_status.sh
ws feature-new workstation_control_plane --title "Stabilize ws command documentation" --from-task /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md
ws feature-status
ws ready
ws agent-hygiene
ws worktree-status
git status --short
git diff --stat
```

Observed results:

- all three shell syntax checks passed
- `ws feature-new` created:
  - `D:\_ai_brain\features\workstation_control_plane\stabilize-ws-command-documentation`
- generated state was `CREATED`
- generated metadata recorded:
  - `provider_invocation: false`
  - `browser_automation: false`
  - feature id `stabilize-ws-command-documentation`
- the generated stronghold contained every required top-level file and subfolder
- `feature_contract.md` included title, objective, source task, acceptance criteria, allowed files, denied files, risk, and stop conditions
- `validation_plan.md` stayed conservative and listed future checks only
- `loop_log.md` recorded the creation event
- `ws feature-status` listed the new stronghold
- `ws ready` passed and wrote `READINESS_20260517_221104.md`
- `ws agent-hygiene` passed with `0` unresolved `CODEX_RUNNING` folders
- `ws worktree-status` reported `2` active worktrees and `0` stale-looking directories
- `git check-ignore -v` confirmed generated strongholds are ignored through `features/`

## Limitations

- no feature planning yet
- no feature execution loop
- no validation runner
- no provider or browser handoff integration
- no run or handoff linking yet
- duplicate feature ids are refused rather than versioned
- validation plans are scaffolded only; no checks are executed

## Next Step

Implement the next safe feature-level command:

- `ws feature-plan`

It should link a feature stronghold to the existing local-plan lane without enabling apply, providers, browser automation, or worktree execution.
