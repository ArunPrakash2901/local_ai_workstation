# R15: Branch and Stale-Run Cleanup Plan

Date: 2026-05-16  
Scope: read-only cleanup planning only. No cleanup actions executed.

## 1. Current Main/Origin Status

- `HEAD`: `46e30e1`
- `main`: `46e30e1`
- `origin/main`: `46e30e1`
- Result: local `main` and `origin/main` are aligned.
- Note: this is newer than the prior milestone base `d1909cc` due post-merge review commit.

## 2. Unresolved `CODEX_RUNNING` Folder: Decision

Exact unresolved folder:

- `D:\_ai_brain\auto_runs\20260516_142401_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`

Observed state:

- `status.txt`: `CODEX_RUNNING`
- `final_report.md`: missing
- `codex_stdout.log`: missing
- `codex_stderr.log`: missing
- `codex_exit_code.txt`: missing
- `heartbeat.log`: only startup lines, no periodic `still running` entries
- `stale_reviewed.md`: missing

Decision:

- Mark reviewed now: **No**
- Investigate further first: **Yes**
- Keep as diagnostic evidence: **Yes**
- Archive later: **Yes**, after investigation + reviewed marker is added

Rationale:

- This run appears more abrupt than the three already reviewed stale runs (no continuing heartbeat / no terminal artifacts), so it should be reviewed as a distinct failure mode before archival.

## 3. Reviewed `CODEX_RUNNING` Folders: Decision

Exact reviewed folders:

- `D:\_ai_brain\auto_runs\20260514_191435_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`
- `D:\_ai_brain\auto_runs\20260514_192421_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`
- `D:\_ai_brain\auto_runs\20260516_135309_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run`

Observed state:

- All three still show `status.txt = CODEX_RUNNING`
- All three include `stale_reviewed.md` with manual reviewed timestamps

Decision:

- Keep for now: **Yes**
- Archive later: **Yes**
- Ignore permanently: **No**

Rationale:

- They are acknowledged historical stale runs and no longer active blockers, but still useful as retention evidence until the archive phase is executed.

## 4. Branch Categories

### A) Safe deletion candidates because they point to `main`

- `agent/workstation_control_plane/001-20260516_172407`
- `post-queue-workstation-updates`

`main` itself points to main and must be kept.

### B) Safe deletion candidates because they are fully merged

From `git branch --merged main`, excluding `main` and the two branches above:

- `agent/workstation_control_plane/001-20260516_150312`
- `agent/workstation_control_plane/001-20260516_150712`
- `agent/workstation_control_plane/001-20260516_151453`
- `agent/workstation_control_plane/001-20260516_151525`
- `agent/workstation_control_plane/001-20260516_151725`
- `agent/workstation_control_plane/001-20260516_152159`
- `agent/workstation_control_plane/001-20260516_152438`
- `fix/agent-run-terminal-state`
- `r3-agent-contract-validation`
- `r4-agent-hygiene`
- `r4-retention-policy`
- `r5-independent-loop-design`
- `r6-loop-plan`

### C) Branches with unique commits that must be kept (for now)

All branches in `git branch --no-merged main`:

- `agent/workstation_control_plane/001-20260514_180631`
- `agent/workstation_control_plane/001-20260514_184552`
- `agent/workstation_control_plane/001-20260514_190116`
- `agent/workstation_control_plane/001-20260514_190139`
- `agent/workstation_control_plane/001-20260514_191435`
- `agent/workstation_control_plane/001-20260514_192421`
- `agent/workstation_control_plane/001-20260516_134950`
- `agent/workstation_control_plane/001-20260516_135309`
- `agent/workstation_control_plane/001-20260516_141744`
- `agent/workstation_control_plane/001-20260516_141946`
- `agent/workstation_control_plane/001-20260516_142131`
- `agent/workstation_control_plane/001-20260516_142401`
- `ai-build/workstation_control_plane/001-20260514_121729`
- `auto/workstation_control_plane/001-20260514_132600`
- `auto/workstation_control_plane/001-20260514_132933`
- `auto/workstation_control_plane/001-20260514_135652`
- `auto/workstation_control_plane/001-20260514_135819`
- `auto/workstation_control_plane/001-20260514_140737`
- `auto/workstation_control_plane/001-20260514_141649`
- `auto/workstation_control_plane/001-20260514_142439`
- `auto/workstation_control_plane/001-20260514_143348`
- `auto/workstation_control_plane/001-20260514_144046`
- `auto/workstation_control_plane/001-20260514_144405`
- `auto/workstation_control_plane/001-20260514_144614`
- `auto/workstation_control_plane/001-20260514_144755`
- `auto/workstation_control_plane/001-20260514_145241`
- `auto/workstation_control_plane/001-20260514_150735`
- `auto/workstation_control_plane/001-20260514_151709`
- `auto/workstation_control_plane/001-20260514_151736`
- `auto/workstation_control_plane/001-20260514_151852`
- `auto/workstation_control_plane/001-20260514_152040`
- `auto/workstation_control_plane/001-20260514_152135`
- `auto/workstation_control_plane/001-20260514_152230`
- `auto/workstation_control_plane/001-20260514_152259`
- `auto/workstation_control_plane/001-20260514_152403`
- `auto/workstation_control_plane/001-20260514_152646`
- `auto/workstation_control_plane/001-20260514_152822`
- `auto/workstation_control_plane/001-20260514_153004`
- `auto/workstation_control_plane/001-20260514_153141`
- `auto/workstation_control_plane/001-20260514_153408`
- `auto/workstation_control_plane/001-20260514_153628`
- `auto/workstation_control_plane/001-20260514_153810`
- `auto/workstation_control_plane/001-20260514_154416`
- `auto/workstation_control_plane/001-20260514_154441`
- `auto/workstation_control_plane/001-20260514_154556`
- `auto/workstation_control_plane/001-20260514_154612`
- `auto/workstation_control_plane/001-20260514_154800`
- `auto/workstation_control_plane/001-20260514_154818`
- `auto/workstation_control_plane/001-20260514_155234`
- `auto/workstation_control_plane/001-20260514_155415`
- `codex-handoff/workstation_control_plane/001-20260514_172335`
- `codex-handoff/workstation_control_plane/001-20260514_172418`
- `codex-handoff/workstation_control_plane/001-20260514_173046`
- `codex/workstation_control_plane/001-20260514_160940-Stabilize_ws_command_documentation`
- `codex/workstation_control_plane/001-20260514_161026-Stabilize_ws_command_documentation`
- `codex/workstation_control_plane/001-20260514_161137-Stabilize_ws_command_documentation`
- `codex/workstation_control_plane/001-20260514_162415-Stabilize_ws_command_documentation`
- `codex/workstation_control_plane/001-20260514_162524-Stabilize_ws_command_documentation`
- `codex/workstation_control_plane/001-20260514_162705-Stabilize_ws_command_documentation`

### D) Branches needing human review

- `agent/workstation_control_plane/001-20260516_142401` (paired to unresolved stale run)
- All non-merged `auto/*`, `codex/*`, and `codex-handoff/*` branches before any deletion decision
- Any branch with an `origin/*` upstream where remote retention policy must be confirmed first

## 5. Proposed Future Cleanup Commands (Do Not Run Yet)

```bash
# DO NOT RUN YET — R15 planning only

# 0) Safety snapshot before cleanup
# git status --short
# git branch -vv
# git branch --merged main
# git branch --no-merged main
# ws agent-hygiene

# 1) Investigate unresolved stale run first
# ls -la D:/_ai_brain/auto_runs/20260516_142401_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run
# cat D:/_ai_brain/auto_runs/20260516_142401_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run/heartbeat.log

# 2) If investigation confirms stale historical run, mark reviewed (no deletion)
# ws agent-mark-stale-reviewed 20260516_142401_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run

# 3) Delete branches that point to main (keep main)
# git branch -d post-queue-workstation-updates
# git branch -d agent/workstation_control_plane/001-20260516_172407

# 4) Delete fully merged branches (already contained in main history)
# git branch -d agent/workstation_control_plane/001-20260516_150312
# git branch -d agent/workstation_control_plane/001-20260516_150712
# git branch -d agent/workstation_control_plane/001-20260516_151453
# git branch -d agent/workstation_control_plane/001-20260516_151525
# git branch -d agent/workstation_control_plane/001-20260516_151725
# git branch -d agent/workstation_control_plane/001-20260516_152159
# git branch -d agent/workstation_control_plane/001-20260516_152438
# git branch -d fix/agent-run-terminal-state
# git branch -d r3-agent-contract-validation
# git branch -d r4-agent-hygiene
# git branch -d r4-retention-policy
# git branch -d r5-independent-loop-design
# git branch -d r6-loop-plan

# 5) Re-run hygiene checks
# ws agent-hygiene
# git branch -vv
# git branch --merged main
# git branch --no-merged main
```

## 6. What Must Be Backed Up Before Cleanup

- Latest hygiene report used for decision baseline:
  - `D:\_ai_brain\reports\AGENT_HYGIENE_20260516_231137.md`
- Milestone review context:
  - `D:\_ai_brain\reports\R14_POST_MERGE_MILESTONE_REVIEW.md`
- This cleanup plan:
  - `D:\_ai_brain\reports\R15_BRANCH_AND_STALE_RUN_CLEANUP_PLAN.md`
- Run metadata for stale runs before any archival phase:
  - `status.txt`, `heartbeat.log`, `stale_reviewed.md` (when present), branch/create metadata files in each affected run folder

## 7. Validation Required After Cleanup

- `git status --short`
- `git branch -vv`
- `git branch --merged main`
- `git branch --no-merged main`
- `ws agent-hygiene`
- `ws loop-status`
- `ws ready`

Success criteria:

- No accidental deletion of `main`
- Unresolved stale-run count reduced only if explicitly marked reviewed
- Reviewed stale-run count increases predictably by one only after explicit mark step
- Remaining branch inventory matches planned deletions exactly

## 8. Cleanup Execution Mode Recommendation

- Recommended mode: **semi-automated**
- Why:
  - Manual review is required for unresolved stale-run diagnosis and unique-commit branches.
  - Scripted execution is appropriate only for already-approved branch lists (point-to-main and fully merged).
  - This balances safety (human gate) with repeatability (commanded batch).

## 9. Recommendation for R16

R16 should be an **execution report** for approved cleanup actions with before/after evidence:

1. Explicit pre-flight snapshot (branch lists + hygiene counts)
2. Exact commands executed (only approved subset from this plan)
3. Post-cleanup validation outputs
4. Residual backlog:
   - unresolved/ reviewed stale-run counts
   - remaining non-merged branch groups requiring follow-up

