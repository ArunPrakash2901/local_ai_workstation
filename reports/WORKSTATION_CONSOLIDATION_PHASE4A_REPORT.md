# Workstation Consolidation Phase 4A Report

Generated: 2026-05-14

## Scope

Low-risk path abstraction refactor only. No folders were moved, no junctions were created, `OLLAMA_MODELS` was not changed, no models were benchmarked or pulled, and no frontier providers were called.

## Scripts Updated

These read-only/status/listing scripts now source `ws_env.sh` safely and use `WS_HOME`/`MODEL_HOME` where applicable, while keeping live-path fallbacks:

- `scripts/ws_path_status.sh`
- `scripts/ws_task_status.sh`
- `scripts/ws_cleanup_status.sh`
- `scripts/ws_frontier_status.sh`
- `scripts/ai_project.sh`
- `scripts/ai_list_projects.sh`
- `scripts/ai_model_current.sh`
- `scripts/ai_models.sh`
- `scripts/ai_kv_profiles.sh`

No `ws_project.sh`, `ws_list_projects.sh`, or `ai_moe_list.sh` script exists in the current scripts folder, so those were not updated.

## Scripts Intentionally Skipped

Skipped because they modify files, run build/apply flows, manage models, call frontier tooling, archive/move files, or are outside Phase 4A scope:

- `scripts/ws_build.sh`
- `scripts/ws_apply_guard.sh`
- `scripts/ws_escalate.sh`
- `scripts/ws_make_packet.sh`
- `scripts/ws_redact_packet.sh`
- `scripts/ws_cleanup_apply.sh`
- `scripts/ws_cleanup_plan.sh`
- `scripts/ws_task_split.sh`
- `scripts/ws_task_new.sh`
- `scripts/ws_task_complete.sh`
- `scripts/ws_task_block.sh`
- `scripts/ai_model_bench.sh`
- `scripts/ai_model_pull.sh`
- `scripts/ai_model_use.sh`
- `scripts/ai_model_warm.sh`
- `scripts/benchmark_ollama.sh`
- `scripts/benchmark_ollama_v2.sh`
- PowerShell scripts

## Hardcoded Path Counts

Scoped count excludes runtimes, model folders, run/build artifacts, archives, cleanup artifacts, frontier logs/responses, graphify output, and `.log` files.

Before Phase 4A scoped file counts:

| Pattern | Files |
| --- | ---: |
| `/mnt/d/_ai_brain` | 60 |
| `D:\_ai_brain` | 23 |
| `/mnt/d/ollama/models` | 14 |
| `D:\ollama\models` | 12 |

After Phase 4A scoped file and occurrence counts:

| Pattern | Files | Occurrences |
| --- | ---: | ---: |
| `/mnt/d/_ai_brain` | 60 | 187 |
| `D:\_ai_brain` | 23 | 114 |
| `/mnt/d/ollama/models` | 15 | 20 |
| `D:\ollama\models` | 12 | 37 |

The file-count did not materially drop because Phase 4A deliberately preserves fallback literals and migration documentation still records old paths. In the updated scripts, repeated operational literals were reduced to a single fallback assignment per script, and all live control-plane paths now flow through `WS_HOME` after initialization.

## Validation Results

Passed:

```bash
source ~/.bashrc
ws help
ws paths
ws projects
ws project workstation_control_plane
ws model
ws models
ws kv
ws moe
ws frontier
ws task-status
ws cleanup-status
ws runs
```

Syntax and line-ending checks passed for all updated scripts.

## Failures

None in validation.

## Current Runtime State

- `WS_HOME=/mnt/d/_ai_brain`
- `WS_PARENT=/mnt/d/Local_AI_Workstation`
- `MODEL_HOME=/mnt/d/ollama/models`
- `WS_MIGRATION_MODE=live_paths`
- `OLLAMA_MODELS` remains `D:\ollama\models`

Nothing was moved.

## Recommended Phase 4B

Continue with low-to-medium risk control-plane scripts that write only inside `WS_HOME`, still preserving fallbacks:

1. `ws_task_next.sh`
2. `ws_task_review_packet.sh`
3. `ws_build_report.sh`
4. `ws_context_pack.sh`
5. `ws_task_parser.sh`

Do not update apply/archive/escalation/model mutation scripts until a later phase.
