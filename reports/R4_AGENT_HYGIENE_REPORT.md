# R4 Agent Hygiene Report

## Files Changed
- `scripts/ws_agent_hygiene.sh`
- `scripts/ws`
- `scripts/ws_agent_validate.sh`
- `WORKSTATION_MANUAL.md`
- `reports/R4_AGENT_HYGIENE_REPORT.md`

## Checks Added
- Current branch, main branch, `agent/*` branches, and relation to `main`.
- Read-only worktree listing.
- `auto_runs/` status counts and detailed folder inventory.
- Stale `CODEX_RUNNING` folders with artifact presence checks.
- Whether `auto_runs/` is ignored by Git.
- Whether `AGENT_CONTRACT_VALIDATION_*.md` reports are ignored or likely to become untracked noise.

## Findings
- Latest hygiene report:
  - `reports/AGENT_HYGIENE_20260516_152608.md`
- Branches:
  - `18` `agent/*` branches.
  - `6` local branches point to the same commit as `main`.
  - `63` local branches point to commits that differ from `main`.
- Worktrees:
  - One active worktree was reported for `D:\_ai_brain`.
- Run folders:
  - `169` folders scanned under `auto_runs/`.
  - `79` `PLAN_ONLY` runs.
  - `1` `CODEX_COMPLETED` run.
  - `4` stale `CODEX_RUNNING` folders:
    - `20260514_191435_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`
    - `20260514_192421_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`
    - `20260516_135309_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`
    - `20260516_142401_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`
- Git hygiene:
  - `auto_runs/` is ignored.
  - `AGENT_CONTRACT_VALIDATION_*.md` reports are not ignored and can become untracked noise.

## What To Keep
- Keep `main`.
- Keep the current working branch until its purpose is settled.
- Keep stale/failure run folders while they still support diagnosis and audit history.
- Keep the latest contract and hygiene reports while the policy is still being established.

## What Can Later Be Deleted Or Archived
- Branches that point to the same commit as `main`, after manual review.
- Older `PLAN_ONLY` and duplicate validation reports, once there is an explicit retention policy.
- Historical stale `CODEX_RUNNING` folders, after the related failure reports are no longer needed.

## What Must Not Be Deleted Yet
- Any run folder still needed to explain terminal-state, launcher, or timeout failures.
- Any branch with unique commits until its contents are reviewed.
- Any generated report until the operator decides whether reports are evidence to retain or disposable runtime noise.

## Remaining Risks
- Existing historical branches and reports still require a human retention policy.
- The first hygiene pass showed why normalization matters: short/full commit hash mismatch and UTF-8 BOMs in old status files can hide true state if not handled.
- `ws agent-validate` previously created dry-run branches because it passed `--branch`; R4 removed that flag so future validation runs stop adding branch noise.

## Next Recommended Step
Decide and document a retention policy before adding any apply-capable cleanup command:
- which branches may be deleted after review
- which report patterns should be ignored or retained
- how long stale run folders should remain before archive review
