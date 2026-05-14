# Task Queue

## Task 001: Stabilize ws command documentation
Goal:
Ensure ws help, START_HERE.md, and WORKSTATION_MANUAL.md are consistent.

Acceptance Criteria:
- ws help commands match documentation
- deprecated ai* aliases are explained as legacy
- docs show daily workflow clearly
- no scripts changed unless necessary

Risk:
low

## Task 002: Create daily workflow command
Goal:
Create or improve a single command that runs daily readiness checks.

Acceptance Criteria:
- command verifies ws, Ollama endpoint, active model, active KV, project registry, frontier status
- no big models are warmed
- output is concise
- report saved under D:\_ai_brain\reports

Risk:
low

## Task 003: Improve build loop reporting
Goal:
Make ws build reports easier to review.

Acceptance Criteria:
- build_report.md has clear sections
- status.txt is one of planned, blocked, passed, failed, skipped
- ws open-build latest prints readable summary
- no project files are modified during plan-only mode

Risk:
medium

## Task 004: Add PRD-to-task splitter
Goal:
Create a local-first workflow that turns a PRD into atomic tasks.

Acceptance Criteria:
- command accepts PRD markdown
- outputs a task queue file
- uses local Hermes only
- does not modify project source
- works with 8192 context

Risk:
medium

## Task 005: Strengthen frontier packet workflow
Goal:
Improve packet creation for Codex review.

Acceptance Criteria:
- packet includes local context, question, constraints, and safety notice
- redaction always runs before escalation
- Codex remains explicit only
- Gemini remains manual/disabled until safe
- Claude remains disabled

Risk:
medium

## Task 006: Add workstation self-audit
Goal:
Make ws audit-workstation output more actionable.

Acceptance Criteria:
- audit groups issues by severity
- cleanup candidates are clearly separated from do-not-touch files
- no delete operations
- cleanup apply remains archive-only

Risk:
low

## Task 007: Create night-run design, not implementation
Goal:
Design a future bounded overnight workflow.

Acceptance Criteria:
- plan only
- includes max task count, max attempts, max files, stop conditions, no deploy, no secrets
- does not implement unattended apply mode yet

Risk:
low
