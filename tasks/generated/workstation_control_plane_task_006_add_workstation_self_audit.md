# Task 006: Add workstation self-audit

Source:
prd

Project:
workstation_control_plane

Status:
generated

Goal:
Make ws audit-workstation output more actionable.

Acceptance Criteria:
- audit groups issues by severity
- cleanup candidates are clearly separated from do-not-touch files
- no delete operations
- cleanup apply remains archive-only

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
low

Escalation:
none

Original Task Content:
```markdown
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
```
