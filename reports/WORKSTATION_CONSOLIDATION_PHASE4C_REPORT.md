# Workstation Consolidation Phase 4C Report

Generated: 2026-05-14

## Scope

Phase 4C refactored local task lifecycle scripts to use the central path abstraction while preserving the live runtime.

No folders were moved. No junctions were created. `OLLAMA_MODELS` was not changed. No build apply, cleanup apply, model benchmark, model pull, warmup, or frontier escalation was run.

## Current Path State

- `WS_HOME=/mnt/d/_ai_brain`
- `WS_PARENT=/mnt/d/Local_AI_Workstation`
- `MODEL_HOME=/mnt/d/ollama/models`
- `WS_MIGRATION_MODE=live_paths`

## Scripts Updated

The following scripts now source `ws_env.sh` safely and use `WS_HOME` for control-plane paths:

- `/mnt/d/_ai_brain/scripts/ws_task_new.sh`
- `/mnt/d/_ai_brain/scripts/ws_task_split.sh`
- `/mnt/d/_ai_brain/scripts/ws_task_complete.sh`
- `/mnt/d/_ai_brain/scripts/ws_task_block.sh`
- `/mnt/d/_ai_brain/scripts/ws_task_review_packet.sh`

`ws_task_status.sh` was inspected and left unchanged because it was already path-aware enough for this phase.

Each updated script preserves fallback defaults:

- `WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"`
- `MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"`

## Scripts Inspected But Skipped

The following scripts were reviewed but intentionally deferred:

- `ws_build.sh`
- `ws_apply_guard.sh`
- `ws_escalate.sh`
- `ws_make_packet.sh`
- `ws_redact_packet.sh`
- `ws_cleanup_apply.sh`
- model pull scripts
- model benchmark scripts
- model warm/unload scripts
- PowerShell scripts
- any script that moves, archives, deletes, applies patches, calls frontier providers, or mutates models

## Smoke Tasks Created

Two temporary smoke tasks were created under `tasks/inbox` and then moved:

- `/mnt/d/_ai_brain/tasks/inbox/20260514_111939_smoke_lifecycle_block_task.md`
- `/mnt/d/_ai_brain/tasks/inbox/20260514_111939_smoke_lifecycle_complete_task.md`

They were then moved to:

- `/mnt/d/_ai_brain/tasks/blocked/20260514_111939_smoke_lifecycle_block_task.md`
- `/mnt/d/_ai_brain/tasks/completed/20260514_111939_smoke_lifecycle_complete_task.md`

These are temporary smoke-test tasks and do not touch any project source.

## Validation Results

Passed:

```bash
bash -n /mnt/d/_ai_brain/scripts/ws_task_new.sh
bash -n /mnt/d/_ai_brain/scripts/ws_task_split.sh
bash -n /mnt/d/_ai_brain/scripts/ws_task_complete.sh
bash -n /mnt/d/_ai_brain/scripts/ws_task_block.sh
bash -n /mnt/d/_ai_brain/scripts/ws_task_status.sh
bash -n /mnt/d/_ai_brain/scripts/ws_task_review_packet.sh
```

Line-ending checks passed: all updated scripts are LF.

Executable bits were ensured for all updated scripts.

Safe command validation passed:

```bash
ws help
ws paths
ws task-status
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md
ws task-status
ws task-next workstation_control_plane
```

The `ws task-split` smoke run created:

- `/mnt/d/_ai_brain/tasks/generated/split_20260514_111732`
- `/mnt/d/_ai_brain/tasks/generated/split_20260514_111845`

The generated output was not fully reliable:

- one run produced a generated task file with an empty `Project:` field before the fallback was applied
- another run produced a README-only split folder because the local model output was not parseable into task headings

That is a content-quality risk in the split workflow, not a path abstraction failure.

`ws task-next workstation_control_plane` worked after the smoke tasks were created and returned the expected inbox task:

- `/mnt/d/_ai_brain/tasks/inbox/20260514_111939_smoke_lifecycle_complete_task.md`

After the smoke moves, task status is:

- `inbox: 0`
- `active: 0`
- `completed: 2`
- `blocked: 2`
- `generated: 6`
- `reviewed: 0`

## Remaining Migration Risks

- `ws_task_split.sh` still depends on local Hermes output being parseable into task headings.
- Generated PRD splits may need prompt tuning before they are fully dependable.
- Build apply, escalation, cleanup apply, and model mutation scripts remain intentionally deferred.
- Documentation still contains live-path references by design.

## Recommended Phase 4D

Continue with the task lifecycle support scripts that stay local and do not mutate project code:

1. `ws_task_review_packet.sh` follow-up cleanup if needed
2. `ws_task_status.sh` only if additional path-awareness or output formatting is needed
3. `ws_task_parser.sh` follow-up only if the generated PRD format needs stronger normalization
4. `ws_build_report.sh` follow-up only if task lifecycle recommendations need refinement

Keep these deferred until a later phase:

- `ws_build.sh`
- `ws_apply_guard.sh`
- `ws_escalate.sh`
- `ws_make_packet.sh`
- `ws_redact_packet.sh`
- `ws_cleanup_apply.sh`
- model pull/warm/benchmark scripts

