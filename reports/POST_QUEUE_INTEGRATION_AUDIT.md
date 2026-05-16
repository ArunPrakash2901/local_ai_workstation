# Post-Queue Integration Audit

Date: 2026-05-16  
Scope: shallow post-queue audit of the seven completed `workstation_control_plane` tasks. No apply flow, night-run flow, cloud apply flow, cleanup flow, or project-repo mutation was run.

## 1. Branch State

- Current branch: `agent/workstation_control_plane/001-20260516_172407`
- This work is on an agent branch, not `main`.

## 2. Changed / Untracked Files Grouped By Workstream

Inventory snapshot was taken from `git status --short` before this audit report was created.

### Task 001 documentation stabilization

- `START_HERE.md`
- `WORKSTATION_MANUAL.md`

### Task 002 `ws ready`

- `scripts/ws` - `ready` help entry and dispatcher wiring
- `scripts/ws_readiness.sh`

### Task 003 build reporting / `ollama_call.py`

- `scripts/ollama_call.py`
- `scripts/ws_build.sh`
- `scripts/ws_build_report.sh`
- `scripts/ws` - `open-build` summary/report display hunk

### Task 004 `task-split --llm`

- `scripts/ws_task_split.sh`
- `prompts/task_splitter.md`

### Task 005 frontier workflow

- `scripts/ws_escalate.sh`
- `scripts/ws_make_packet.sh`

### Task 006 `audit-workstation`

- `scripts/ws_audit_workstation.sh`

### Task 007 night-run design

- `plans/NIGHT_RUN_DESIGN.md`

### R13.2 report parser / line-ending policy

- `.gitattributes`
- `scripts/ws_agent_run.ps1`
- `reports/R13_2_REPORT_PARSER_LINE_ENDINGS.md`

### Generated reports / noise

- `reports/READINESS_20260516_214641.md`
- `reports/READINESS_20260516_214707.md`
- `reports/READINESS_20260516_220551.md`
- `reports/READINESS_20260516_221052.md`
- `prompts/global_system.md`
- `prompts/graphify_first.md`
- `prompts/learning_assistant.md`
- `prompts/local_debugger.md`
- `prompts/product_builder.md`
- `prompts/project_auditor.md`
- `reports/AGENT_CONTRACT_VALIDATION_20260516_151517.md`
- `reports/GEMINI_RECOVERY_REPORT.md`
- `reports/R10_LOCAL_LOOP_REVIEW_HANDOFF.md`
- `reports/R11_SUPERVISED_CLOUD_APPLY_DESIGN.md`
- `reports/R12_1_APPLY_READY_DISPATCH_FIX.md`
- `reports/R12_2_STALE_RUN_ACKNOWLEDGEMENT.md`
- `reports/R12_3_STALE_RUN_BLOCKER_DEEP_DIAGNOSIS.md`
- `reports/R12_4_APPLY_READY_BASH_FIX.md`
- `reports/R12_APPLY_READY_IMPLEMENTATION.md`
- `reports/R13_1_AGENT_RUN_WS_SYNTAX_FIX.md`
- `reports/R5B_CLOUD_CANARY_FAILURE_DIAGNOSIS.md`
- `reports/R5_INDEPENDENT_LOOP_DESIGN.md`
- `reports/R6_1_LOOP_PLAN_FIX.md`
- `reports/R6_LOOP_PLAN_IMPLEMENTATION.md`
- `reports/R7_LOOP_STATUS_IMPLEMENTATION.md`
- `reports/R8_SUPERVISED_LOOP_START_DESIGN.md`
- `reports/R9_LOOP_START_LOCAL_PLAN_IMPLEMENTATION.md`
- `scripts/ai_apply_ollama_profile.ps1`

Notes:

- `git diff --ignore-space-at-eol` showed no semantic diff for the prompt files, historical report files, or `scripts/ai_apply_ollama_profile.ps1`; they appear to be line-ending-only churn caused by the new line-ending policy rather than part of the seven tasks.
- `scripts/ws` contains unrelated hunks for Task 002 and Task 003, so it should be partially staged rather than committed whole with either task.

## 3. Files That Appear Unrelated To The Seven Tasks

These files do not appear to belong to Tasks 001-007 and should not be mixed into those task commits without an explicit decision:

- `prompts/global_system.md`
- `prompts/graphify_first.md`
- `prompts/learning_assistant.md`
- `prompts/local_debugger.md`
- `prompts/product_builder.md`
- `prompts/project_auditor.md`
- `reports/AGENT_CONTRACT_VALIDATION_20260516_151517.md`
- `reports/GEMINI_RECOVERY_REPORT.md`
- `reports/R10_LOCAL_LOOP_REVIEW_HANDOFF.md`
- `reports/R11_SUPERVISED_CLOUD_APPLY_DESIGN.md`
- `reports/R12_1_APPLY_READY_DISPATCH_FIX.md`
- `reports/R12_2_STALE_RUN_ACKNOWLEDGEMENT.md`
- `reports/R12_3_STALE_RUN_BLOCKER_DEEP_DIAGNOSIS.md`
- `reports/R12_4_APPLY_READY_BASH_FIX.md`
- `reports/R12_APPLY_READY_IMPLEMENTATION.md`
- `reports/R13_1_AGENT_RUN_WS_SYNTAX_FIX.md`
- `reports/R5B_CLOUD_CANARY_FAILURE_DIAGNOSIS.md`
- `reports/R5_INDEPENDENT_LOOP_DESIGN.md`
- `reports/R6_1_LOOP_PLAN_FIX.md`
- `reports/R6_LOOP_PLAN_IMPLEMENTATION.md`
- `reports/R7_LOOP_STATUS_IMPLEMENTATION.md`
- `reports/R8_SUPERVISED_LOOP_START_DESIGN.md`
- `reports/R9_LOOP_START_LOCAL_PLAN_IMPLEMENTATION.md`
- `scripts/ai_apply_ollama_profile.ps1`
- `reports/READINESS_20260516_214641.md`
- `reports/READINESS_20260516_214707.md`
- `reports/READINESS_20260516_220551.md`
- `reports/READINESS_20260516_221052.md`

## 4. Dispatcher Parse / Help Surface

- `bash -n scripts/ws`: passed.
- Syntax check over changed shell scripts: passed for `scripts/ws_audit_workstation.sh`, `scripts/ws_build.sh`, `scripts/ws_build_report.sh`, `scripts/ws_escalate.sh`, `scripts/ws_make_packet.sh`, `scripts/ws_task_split.sh`, and `scripts/ws_readiness.sh`.
- `ws help`: passed and exposes the expected public surfaces:
  - `ready`
  - `task-split`
  - `audit-workstation`
  - task lifecycle commands
  - agent / loop commands
  - build commands
- `night-run` is not exposed in `ws help`, which is correct because Task 007 is design-only.

## 5. `ws ready` Failure Classification

Observed output from `ws ready`:

- `[FAIL] Ollama is NOT reachable on localhost:11434.`
- `[FAIL] WSL cannot reach Ollama.`
- `[FAIL] Could not query loaded models.`

Assessment:

- Most likely cause: Ollama is not running or is not listening on Windows `localhost:11434`.
- Why: the readiness path first fails from Windows PowerShell against `http://localhost:11434/api/tags`, then fails again from WSL, then fails to query `api/ps`. If this were only a WSL-routing issue, the Windows-local probe would be expected to pass.
- Current evidence does not point to a readiness-script bug or incorrect localhost / host routing.
- Strict classification from available evidence: `Ollama not running` is the best-supported answer; `unknown` would only be necessary if a later process/socket check disproves that inference.

## 6. Is `ws ready` Blocking Before Commit?

- No, not by itself.
- The command executed and produced the intended timestamped readiness report. The failure is environmental, not a demonstrated implementation failure.
- It should block claims of full workstation readiness and should be green before merge to `main`, but it does not need to block splitting and committing the code changes once the code/documentation issues below are corrected.

## 7. Bash CRLF Protection

- `.gitattributes` correctly protects Bash files from CRLF:
  - `*.sh text eol=lf`
  - `scripts/ws text eol=lf`
- That covers the shell scripts changed in this batch plus the extensionless dispatcher.

## 8. `scripts/ws_agent_run.ps1` Line-Ending Policy

- The policy is appropriate after narrowing: `scripts/ws_agent_run.ps1 text eol=crlf` matches the fact that the changed runner is Windows-native PowerShell without forcing unrelated legacy PowerShell scripts into the same commit.
- Git currently warns that `scripts/ws_agent_run.ps1` will be converted from LF to CRLF the next time Git touches it. That is consistent with the declared policy and is limited to the intentionally changed runner.

## 9. Wired But Untested Surface

- Fully new command:
  - `ws ready` is wired and was exercised.
- New or changed behavior not exercised by the allowed validation set:
  - `task-split --llm`
  - revised `open-build` summary output
  - revised `audit-workstation` report layout
  - revised frontier escalation behavior in `scripts/ws_escalate.sh`
- Therefore the risk is not an untested brand-new top-level command, but several untested new behaviors.

## 10. `READINESS_*.md` Handling

- `reports/READINESS_*.md` is not currently ignored; `.gitignore` only covers `reports/AGENT_CONTRACT_VALIDATION_*.md` and `reports/AGENT_HYGIENE_*.md`.
- Recommendation: ignore timestamped readiness reports by default and only curate a deliberate exemplar when one is needed for documentation or incident evidence.
- Current `READINESS_*.md` files should not be mixed into the feature commits.

## 11. Cloud / Destructive Workflow Check

- No new cloud or destructive workflow appears to have been accidentally enabled.
- Evidence:
  - `scripts/ws_escalate.sh` became stricter for Gemini: it now exits into manual-only handling instead of attempting automated send.
  - `plans/NIGHT_RUN_DESIGN.md` is a design document only; `ws help` exposes no `night-run` command.
  - `ws help` still labels `cleanup-apply` as requiring `--apply`.
- This batch tightens frontier behavior rather than broadening unattended execution.

## 12. Recommended Commit Split

`scripts/ws` requires partial staging because it contains unrelated hunks.

1. `docs(workstation): stabilize daily workflow docs`
   - `START_HERE.md`
   - `WORKSTATION_MANUAL.md`

2. `feat(ws): add daily readiness command`
   - `scripts/ws_readiness.sh`
   - `scripts/ws` - only the `ready` help and dispatcher hunks

3. `feat(build): improve local build reporting`
   - `scripts/ollama_call.py`
   - `scripts/ws_build.sh`
   - `scripts/ws_build_report.sh`
   - `scripts/ws` - only the `open-build` summary hunk

4. `feat(tasks): add llm-assisted task splitting`
   - `scripts/ws_task_split.sh`
   - `prompts/task_splitter.md`

5. `chore(frontier): keep escalation manual-first`
   - `scripts/ws_escalate.sh`
   - `scripts/ws_make_packet.sh`

6. `feat(audit): improve workstation audit reporting`
   - `scripts/ws_audit_workstation.sh`

7. `docs(workstation): add night-run design`
   - `plans/NIGHT_RUN_DESIGN.md`

8. `fix(agent-run): preserve porcelain parsing and line endings`
   - `.gitattributes`
   - `scripts/ws_agent_run.ps1`
   - `reports/R13_2_REPORT_PARSER_LINE_ENDINGS.md`

Do not include in the above commits without a separate explicit decision:

- all prompt-template line-ending-only churn
- all historical report line-ending-only churn
- `scripts/ai_apply_ollama_profile.ps1`
- `reports/READINESS_*.md`

If the line-ending-only normalization is intentionally retained, it should be isolated in a separate cleanup commit such as:

- `chore(repo): normalize tracked text line endings`

## 13. Must Fix Before The First Commit

1. Repair the documentation regression in `WORKSTATION_MANUAL.md`: the daily workflow code block closes after `ws task-status`, leaving subsequent workflow commands outside the block.
2. Decide whether to keep or discard the unrelated line-ending-only churn. It should not be silently bundled into the seven-task commits.
3. Decide policy for `reports/READINESS_*.md` before staging; they are currently unignored timestamped artifacts.
4. Clear or deliberately exclude the current whitespace issues before committing. `git diff --check` reported trailing whitespace in several touched files and an added blank line at EOF in `scripts/ws_build.sh`.

## 14. Validation Required Before Merge To `main`

Minimum repeat checks:

- `bash -n scripts/ws`
- syntax check all changed shell scripts
- `ws help`
- `ws ready`
- `ws agent-validate`
- `ws agent-hygiene`

Additional targeted validation required because current changes were not exercised by this audit:

- run `task-split --llm` against a safe sample PRD once Ollama is reachable
- run `ws audit-workstation` and inspect the generated report structure
- run `ws open-build latest` against an existing build run and verify the summary view
- verify the revised frontier escalation flow remains manual-only for Gemini and explicit for Codex

Merge gate:

- `ws ready` should be green on the intended workstation before merging to `main`.
- The commit series should exclude unrelated normalization noise unless it is deliberately isolated.
- The documentation and whitespace issues listed above should be resolved before the first commit is created.

## Audit Evidence Collected

- `git status --short`
- `git diff --stat`
- `git diff --name-only`
- `bash -n scripts/ws`
- shell syntax checks on changed shell scripts
- `ws help`
- `ws ready`
- `ws agent-validate`
- `ws agent-hygiene`
- shallow diffs for changed task files
