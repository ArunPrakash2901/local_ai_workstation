# Pre-Commit Blockers Fix Report

Date: 2026-05-16  
Task: remove pre-commit cleanup overreach before splitting the workstation-control-plane batch into commits.

## What Was Fixed

1. Reverted incidental prompt/report churn back to `HEAD`.
   - Reverted legacy `prompts/*.md` files except `prompts/task_splitter.md`.
   - Reverted historical `reports/R*.md`, old AGENT/GEMINI reports, and `reports/AGENT_CONTRACT_VALIDATION_20260516_151517.md`.
   - Reverted unrelated line-ending-only churn in `scripts/ai_apply_ollama_profile.ps1`.
2. Preserved the real current-batch work.
   - Kept the seven-task implementation files.
   - Kept `.gitattributes`, `.gitignore`, `reports/R13_2_REPORT_PARSER_LINE_ENDINGS.md`, and the current audit reports.
   - Kept `scripts/ws_agent_run.ps1` because it contains the live R13.2 parser fix, not incidental churn.
3. Narrowed the line-ending policy so it does not dirty historical Markdown.
   - Kept LF enforcement for Bash (`*.sh`, `scripts/ws`).
   - Kept CRLF enforcement for the current Windows-native agent runner (`scripts/ws_agent_run.ps1`).
   - Removed the broad `*.md text eol=lf` rule because it was the source of the prompt/report normalization wave.
   - Replaced the broad `*.ps1 text eol=crlf` rule with a targeted runner rule so unrelated legacy PowerShell files stay out of this batch.
4. Preserved the readiness-report ignore policy.
   - `reports/READINESS_*.md` remains ignored via `.gitignore`.

## Why The Reverted Files Were Noise

- `git diff --ignore-space-at-eol` showed no semantic diff for the reverted prompt set, most historical reports, or `scripts/ai_apply_ollama_profile.ps1`.
- The remaining legacy AGENT report diff only reflected stored-output newline normalization, not an intentional current-task change.
- The broad Markdown end-of-line rule caused restored historical Markdown to become dirty again immediately, so the rule itself had to be narrowed.
- Keeping those edits would have made commit splitting unsafe by mixing unrelated historical normalization into the seven-task batch.

## Current Expected Dirty Set

- Task work:
  - `START_HERE.md`
  - `WORKSTATION_MANUAL.md`
  - `scripts/ws`
  - `scripts/ws_readiness.sh`
  - `scripts/ollama_call.py`
  - `scripts/ws_build.sh`
  - `scripts/ws_build_report.sh`
  - `scripts/ws_task_split.sh`
  - `scripts/ws_make_packet.sh`
  - `scripts/ws_escalate.sh`
  - `scripts/ws_audit_workstation.sh`
  - `prompts/task_splitter.md`
  - `plans/NIGHT_RUN_DESIGN.md`
- Policy / report files:
  - `.gitattributes`
  - `.gitignore`
  - `scripts/ws_agent_run.ps1`
  - `reports/POST_QUEUE_INTEGRATION_AUDIT.md`
  - `reports/PRE_COMMIT_BLOCKERS_FIX.md`
  - `reports/R13_2_REPORT_PARSER_LINE_ENDINGS.md`

## Environment Note

- `ws ready` may still report Ollama unreachable on `localhost:11434`.
- That remains an environmental condition unless separate evidence proves otherwise; this cleanup intentionally did not change readiness logic to mask it.

## Validation Performed

- `git status --short`: reduced to current task/policy/report files only.
- `git diff --stat`: reduced from the historical prompt/report wave to the current batch surface.
- `bash -n scripts/ws`: passed.
- changed-shell-script syntax checks: passed.
- `ws help`: passed.
- `ws agent-hygiene`: passed.
- `ws ready`: passed on the current run; Ollama was reachable during validation.
