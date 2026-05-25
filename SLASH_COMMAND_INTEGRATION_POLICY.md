# Slash Command Integration Policy

This policy defines how short human/operator slash commands map to canonical workstation commands.

## Core Rules

1. `ws`/Bash commands are canonical.
2. Slash commands are short human/operator shortcuts.
3. Slash commands must not mirror long `ws` command names.
4. Slash commands should be one word where possible, or two hyphenated words maximum.
5. Slash commands must map to known canonical `ws` commands.
6. Slash commands must not bypass safety registry rules.
7. Slash commands inherit safety class, dry-run behavior, and confirmation behavior from the mapped `ws` command.
8. Slash commands must not accept arbitrary shell strings.
9. Slash command previews should show the mapped canonical `ws` command where useful.
10. Existing lanes do not require full backfill in this policy slice.
11. New features should include a slash-command planning/metadata entry when practical.

## Canonical Surface Doctrine

- Human/operator surface: short slash commands, for example `/design`.
- Machine/agent surface: explicit `ws` command with full arguments.
- Safety source of truth: `registry/ws_command_safety.yaml` and `WS_COMMAND_SAFETY_MATRIX.md`.

## Example Short Command Families

Product Lane:
- `/product`
- `/scope`
- `/prd`
- `/wireframe`
- `/design`
- `/tech`
- `/impl`
- `/review`
- `/approve`

Discovery Lane:
- `/discover`
- `/intake`
- `/ingest`
- `/handoff`

Exchange Lane:
- `/exchange`
- `/dispatch`
- `/import`

Runtime Lane:
- `/sessions`
- `/start`
- `/cleanup`

Knowledge Lane:
- `/inventory`

Repo Context Lane:
- `/repo`
- `/context`
- `/graph`
- `/map`

## Immediate Mapping Added In This Slice

Slash command:
- `/design`

Default action:
- Preview Open Design adapter for the current product.

Canonical mapped command:
- `ws product-design-adapter-preview --product <current_product> --tool open-design --dry-run`

Planned subaction mapping:
- `/design render`
- `ws product-design-render --product <current_product> --tool open-design --dry-run`
- `/design prepare`
- `ws product-design-run-prepare --product <current_product> --tool open-design --confirm`
- `/design status`
- `ws product-design-run-status --product <current_product> --tool open-design`
- `/design probe`
- `ws product-design-runtime-probe --tool open-design --dry-run`
- `/design install-check`
- `ws product-design-install-checklist --tool open-design --dry-run`
- `/design runtime`
- `ws product-design-runtime-report --tool open-design --dry-run`
- `/design review`
- `ws product-design-run-review --product <current_product> --tool open-design --dry-run`
- `/design review-write`
- `ws product-design-run-review --product <current_product> --tool open-design --confirm`

Repo Context Lane Mapping:
- `/repo inventory <path>` -> `ws repo-context inventory --project <path> --dry-run`
- `/repo plan <path>` -> `ws repo-context graphify-plan --project <path> --dry-run`
- `/repo summarize <path>` -> `ws repo-context summarize --graph <path> --dry-run`
- `/repo handoff <path>` -> `ws repo-context handoff --packet <path> --target gemini --dry-run`
- `/repo audit` -> `ws repo-context audit`

- `/context list` -> `ws repo-context packet-list`
- `/context review <path>` -> `ws repo-context packet-review --packet <path> --dry-run`
- `/context approve <path>` -> `ws repo-context packet-approve --packet <path> --confirm`
- `/context packet <project> <task>` -> `ws repo-context packet --project <project> --task <task> --dry-run`

- `/graph list` -> `ws repo-context graphify-plan-list`
- `/graph review <path>` -> `ws repo-context graphify-plan-review --plan <path> --dry-run`
- `/graph approve <path>` -> `ws repo-context graphify-plan-approve --plan <path> --confirm`
- `/graph run <path>` -> `ws repo-context graphify-run --plan <path> --confirm`
- `/graph intake <path>` -> `ws repo-context graphify-intake --run <path> --dry-run`
- `/graph status <path>` -> `ws repo-context graphify-run-status --plan <path>`

Safety inheritance:
- safety class: `PURE_READ`
- writes: `false`
- tool execution: `false`

## Non-Goals In This Slice

- No global slash dispatcher implementation.
- No automatic conversion of all existing commands to slash aliases.
- No bypass of existing `ws` argument validation or safety policy.
