# Task 005: Strengthen frontier packet workflow

Source:
prd

Project:
workstation_control_plane

Status:
generated

Goal:
Improve packet creation for Codex review.

Acceptance Criteria:
- packet includes local context, question, constraints, and safety notice
- redaction always runs before escalation
- Codex remains explicit only
- Gemini remains manual/disabled until safe
- Claude remains disabled

Allowed Files:
- not specified

Denied Files:
- .env
- credentials
- raw datasets
- data/*
- models/*
- node_modules/*
- .git/*

Test Command:


Risk:
medium

Escalation:
none

Original Task Content:
```markdown
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
```
