# Task 004: Add PRD-to-task splitter

Source:
prd

Project:
workstation_control_plane

Status:
generated

Goal:
Create a local-first workflow that turns a PRD into atomic tasks.

Acceptance Criteria:
- command accepts PRD markdown
- outputs a task queue file
- uses local Hermes only
- does not modify project source
- works with 8192 context

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
```
