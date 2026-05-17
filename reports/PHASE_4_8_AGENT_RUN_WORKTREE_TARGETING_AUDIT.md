# Phase 4.8: Agent-Run Worktree Targeting Audit

Date: 2026-05-18  
Mode: Audit/design only. No provider execution, no apply, no worktree mutation.

## Scope Audited

- [ws](/mnt/d/_ai_brain/scripts/ws)
- [ws_agent_run.ps1](/mnt/d/_ai_brain/scripts/ws_agent_run.ps1)
- [ws_apply_ready.sh](/mnt/d/_ai_brain/scripts/ws_apply_ready.sh)
- [ws_feature_run.sh](/mnt/d/_ai_brain/scripts/ws_feature_run.sh)
- [projects.yaml](/mnt/d/_ai_brain/registry/projects.yaml)
- Latest feature apply-ready report:
  - [feature_apply_ready_20260518_000014.md](/mnt/d/_ai_brain/features/workstation_control_plane/stabilize-ws-command-documentation/runs/feature_apply_ready_20260518_000014.md)
- Current feature:
  - `/mnt/d/_ai_brain/features/workstation_control_plane/stabilize-ws-command-documentation`
- Current worktree:
  - `/mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830`

## Validation Snapshot (Requested)

- `ws feature-status`: `VALIDATED_LOCAL`
- `ws worktree-review /mnt/d/_ai_brain/worktrees/workstation_control_plane/001_20260516_135830`: `BEHIND_MAIN`
- `ws ready`: pass
- `ws agent-hygiene`: pass
- `git status --short`: clean
- `git diff --stat`: no tracked diff summary (only line-ending warnings printed by Git)

Important current drift:

- Worktree HEAD: `5d0e01d9857426c689caeed568c811a3418a4053`
- Main HEAD: `c4ec3dba093941e4c466cf53655c81064204379e`
- Current reviewed worktree is not READY now; it is behind main.

## Findings

### 1) Does `ws agent-run` currently resolve project repo path only from `registry/projects.yaml`?

Yes.

- `ws` passes only `-ProjectKey` and `-TaskFile` into `ws_agent_run.ps1` ([ws](/mnt/d/_ai_brain/scripts/ws):170).
- `ws_agent_run.ps1` resolves repo via `Get-ProjectPath($ProjectKey)` reading `registry/projects.yaml` ([ws_agent_run.ps1](/mnt/d/_ai_brain/scripts/ws_agent_run.ps1):210, [ws_agent_run.ps1](/mnt/d/_ai_brain/scripts/ws_agent_run.ps1):409).
- There is no `-RepoPath` or `-WorktreePath` input in current `Run-Agent`.

### 2) Can it be safely pointed at a worktree without changing registry state?

No.

Current architecture has no safe per-run repo override. The only way to redirect today would be editing `projects.yaml` for `workstation_control_plane`, which is global state and unsafe for concurrent/other commands.

### 3) Does `ws apply-ready` support worktree paths or only project keys?

Only project keys (plus task file).

- Usage: `ws apply-ready <project_key> <task_file>` ([ws_apply_ready.sh](/mnt/d/_ai_brain/scripts/ws_apply_ready.sh):20).
- Repo path is resolved from registry `windows_path` for that project key ([ws_apply_ready.sh](/mnt/d/_ai_brain/scripts/ws_apply_ready.sh):37, [ws_apply_ready.sh](/mnt/d/_ai_brain/scripts/ws_apply_ready.sh):50).
- No worktree path argument exists.

### 4) Would running `ws agent-run` from main mutate main or the worktree?

It would mutate the repo path resolved for the project key, which is currently main (`D:\_ai_brain`), not the isolated worktree.

- `workstation_control_plane` in registry points to `D:\_ai_brain` / `/mnt/d/_ai_brain` ([projects.yaml](/mnt/d/_ai_brain/registry/projects.yaml):82).
- `Run-Agent` runs git and Codex against that resolved repo path ([ws_agent_run.ps1](/mnt/d/_ai_brain/scripts/ws_agent_run.ps1):409, [ws_agent_run.ps1](/mnt/d/_ai_brain/scripts/ws_agent_run.ps1):481).
- With `--branch`, it executes `git checkout -B ...` in that repo path ([ws_agent_run.ps1](/mnt/d/_ai_brain/scripts/ws_agent_run.ps1):422), still inside the main working copy.

### 5) What changes are required for safe worktree-targeted agent runs?

Required minimum changes:

1. Add explicit repo/worktree targeting input to agent execution path.
2. Require that target path is a valid git worktree under approved roots.
3. Require fresh worktree review for the exact target path and branch.
4. Require commit/branch freshness checks immediately before provider launch.
5. Preserve default safety: legacy `ws agent-run` remains registry-main path unless explicit worktree mode is selected.
6. Record feature/worktree lineage in run artifacts.
7. Enforce allowed-file boundaries relative to target worktree root.
8. Add post-run validation gates that can block completion on scope violations.

### 6) Should we add a new command or new flags?

Recommendation:

- Keep current `ws agent-run` unchanged as legacy registry-key mode.
- Add a distinct execution entrypoint for worktrees to avoid ambiguous behavior.

Preferred shape:

1. `ws feature-run <feature> --execute-via-agent --worktree <path> --from-apply-ready <report> --dry-run`
2. Later (after dry-run hardening): same command without `--dry-run` to invoke `ws_agent_run.ps1`.

Alternate acceptable shape:

- Add `ws agent-run --repo <path>` but only if paired with strict mandatory flags:
  - `--feature <path>`
  - `--from-dry-run <report>`
  - `--from-apply-ready <report>`
  - `--worktree-review <report>`

A separate mode/command is safer than silently overloading current project-key behavior.

### 7) How should Allowed Files be interpreted relative to the worktree root?

Use normalized repo-relative paths rooted at the target worktree.

Rules:

- Treat allowlist entries as repository-relative paths (for example `scripts/ws`).
- Normalize path separators and reject `..` traversal.
- Reject absolute paths in allowlist and in changed-file checks.
- Compare against `git status --porcelain` / `git diff --name-only` outputs from the target worktree.
- Any change outside allowlist is a scope violation regardless of branch cleanliness.

### 8) How should run folders link to feature/worktree lineage?

Each run should include machine-readable linkage fields:

- `feature_path`
- `feature_id`
- `project_key`
- `worktree_path`
- `worktree_branch`
- `worktree_head_commit`
- `main_head_commit_at_start`
- `dry_run_report_path`
- `apply_ready_report_path`
- `worktree_review_report_path`

Current gap:

- `ws_agent_run.ps1` writes into `auto_runs/...` with task and codex artifacts, but no explicit feature/worktree linkage model today.

### 9) What extra validation is required after agent-run completes?

Required post-run checks:

1. Re-check target worktree git status and branch.
2. Enumerate changed files and enforce allowlist strictly.
3. Confirm no out-of-scope file changes.
4. Confirm no changes occurred in main working copy unintentionally.
5. Generate run-scoped validation report and link it into feature loop log.
6. Re-run `ws feature-validate` style checks before any completion state transition.

### 10) What should happen if Codex quota fails?

Do not retry automatically.

Required behavior:

- classify run as `QUOTA_BLOCKED` (or equivalent explicit quota state)
- preserve stdout/stderr/exit artifacts
- append feature loop event
- set next action to manual handoff/review path, not automatic re-execution
- keep provider/browser automation flags false unless explicitly changed by later approved flows

### 11) What should happen if agent-run changes files outside Allowed Files?

Treat as hard scope violation.

Required behavior:

- classify run as `ALLOWED_FILES_VIOLATION`
- mark execution as failed/blocked for supervised flow
- capture offending file list in run and feature evidence
- require human approval before any cleanup or retry
- do not auto-commit or auto-continue

### 12) What should be the next safest implementation phase?

Recommended next phase: **Phase 4.9 worktree-targeted agent-run dry-run adapter**.

Implement only planning/preflight, no provider invocation:

1. Add feature-owned command to prepare agent execution context for a specific worktree.
2. Validate exact path/branch/commit/report lineage and fail closed on drift.
3. Emit exact would-run command and run metadata package.
4. Keep execution boundary at `HANDOFF_ONLY` until this dry-run adapter proves stable.

## Additional Risk Observed

`ws feature-run --apply --worktree --from-dry-run` currently emits `HANDOFF_ONLY` intentionally, which is correct.  
However, current worktree status is now `BEHIND_MAIN`, so any future execution enablement must require **fresh** READY validation tied to the same worktree path and current commit pair, not just historical READY evidence.

## Conclusion

Current `ws agent-run` is not safely worktree-targetable. It is registry-key anchored and would operate on the main repo path for `workstation_control_plane`.  
Execution should remain blocked at handoff until a dedicated worktree-targeted dry-run execution adapter is implemented with strict path/report/commit gating.
