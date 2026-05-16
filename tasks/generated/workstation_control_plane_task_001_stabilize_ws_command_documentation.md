# Task 001: Stabilize ws command documentation

Source:
prd

Project:
workstation_control_plane

Status:
generated

Goal:
Ensure ws help, START_HERE.md, and WORKSTATION_MANUAL.md are consistent.

Acceptance Criteria:
- ws help commands match documentation
- deprecated ai* aliases are explained as legacy
- docs show daily workflow clearly
- no scripts changed unless necessary

Allowed Files:
- START_HERE.md
- WORKSTATION_MANUAL.md
- scripts/ws

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

Notes:
- Planning and dry-run may inspect broader context.
- Apply mode is restricted to the explicit Allowed Files list above.
- Change scripts/ws only if its help text must match the documentation.

Original Task Content:
```markdown
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
```
