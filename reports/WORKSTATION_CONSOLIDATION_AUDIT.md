# Workstation Consolidation Audit

Generated: 2026-05-14

## Decision

Stop after Phase 1. Do not move anything yet.

Reason: the current workstation is live and working, but the audit found many hardcoded references to `D:\_ai_brain` and `/mnt/d/_ai_brain`, Python virtual environments created in-place under that path, a WSL alias pointing at the old path, and Ollama currently using `D:\ollama\models` with `hermes3:8b` loaded. Moving now would risk breaking `ws`, Graphify, virtualenv entrypoints, and Ollama model discovery unless compatibility links and environment changes are staged very carefully.

## Current Sizes

| Path | Exists | Size |
| --- | --- | --- |
| `D:\_ai_brain` | yes | 0.34 GB |
| `D:\ollama\models` | yes | 42.09 GB |
| `D:\Local_AI_Workstation` | no | 0 GB |

D: free space at audit time: 365.99 GB.

## Current Runtime State

`ws` alias in WSL:

```bash
alias ws='bash /mnt/d/_ai_brain/scripts/ws'
```

`WS_HOME` is not currently set.

`OLLAMA_MODELS`:

```text
D:\ollama\models
```

Ollama API is reachable. Model tags visible:

- `deepseek-coder-v2:lite`
- `hermes3:8b`
- `llama3.1:8b`
- `phi3.5:latest`
- `qwen2.5-coder:7b`
- `qwen2.5:32b`

Loaded model at audit time:

- `hermes3:8b`

## Hardcoded Reference Summary

Scanned under `D:\_ai_brain`, avoiding obvious large/noisy paths where possible. Generated Graphify/cache/run artifacts still contain many historical references and are not migration-critical unless old-path compatibility is removed.

| Reference | Matches / files found |
| --- | --- |
| `/mnt/d/_ai_brain` | 115 files |
| `D:\_ai_brain` | 24 files |
| `D:\ollama\models` or `/mnt/d/ollama/models` | 7 files |

## Key Hardcoded Control Plane References

These are migration-relevant because they affect live commands, registries, aliases, venvs, or documentation:

- `~/.bashrc`: `alias ws='bash /mnt/d/_ai_brain/scripts/ws'`
- `registry/projects.yaml`: `workstation_control_plane` points to `D:\_ai_brain` and `/mnt/d/_ai_brain`
- `scripts/ws`
- `scripts/ai_ask.sh`
- `scripts/ai_audit.sh`
- `scripts/ai_daily_restore.sh`
- `scripts/ai_debug.sh`
- `scripts/ai_global_ask.sh`
- `scripts/ai_graph.sh`
- `scripts/ai_kv_profiles.sh`
- `scripts/ai_kv_use.sh`
- `scripts/ai_list_projects.sh`
- `scripts/ai_model_current.sh`
- `scripts/ai_model_use.sh`
- `scripts/ai_model_warm.sh`
- `scripts/ai_models.sh`
- `scripts/ai_project.sh`
- `scripts/ai_run_task.sh`
- `scripts/ws_apply_guard.sh`
- `scripts/ws_audit_workstation.sh`
- `scripts/ws_build.sh`
- `scripts/ws_cleanup_apply.sh`
- `scripts/ws_cleanup_plan.sh`
- `scripts/ws_cleanup_status.sh`
- `scripts/ws_context_pack.sh`
- `scripts/ws_escalate.sh`
- `scripts/ws_frontier_status.sh`
- `scripts/ws_make_packet.sh`
- `scripts/ws_redact_packet.sh`
- `scripts/ws_task_*.sh`
- `runtimes/graphify_venv/pyvenv.cfg`
- `runtimes/workstation_venv/pyvenv.cfg`
- venv console scripts under `runtimes/*_venv/bin`
- `prompts/global_system.md`
- `START_HERE.md`
- `WORKSTATION_MANUAL.md`
- `LOCAL_AI_STACK_STATUS.md`
- `FINAL_RECOMMENDED_PROFILE.md`

## Ollama Model Path References

Files referencing `D:\ollama\models`:

- `FINAL_RECOMMENDED_PROFILE.md`
- `START_HERE.md`
- `LOCAL_AI_STACK_STATUS.md`
- `reports/machine_state_20260511.md`
- `cleanup/reports/WORKSTATION_AUDIT_*.md`

Machine/user environment currently reports `OLLAMA_MODELS=D:\ollama\models`.

## Scripts / Configs / Docs That Would Need Updates

Minimum safe-update set if compatibility links are retained:

- `~/.bashrc` can continue pointing to `/mnt/d/_ai_brain` if `D:\_ai_brain` becomes a junction.
- `registry/projects.yaml` should eventually update `workstation_control_plane` canonical path to `D:\Local_AI_Workstation\control_plane`, but only after validation.
- Docs should describe new canonical layout and old compatibility paths.
- `FINAL_RECOMMENDED_PROFILE.md`, `LOCAL_AI_STACK_STATUS.md`, and `START_HERE.md` should mention the new model path only after Ollama is verified.

Do not aggressively rewrite all scripts first. A junction-first migration is safer because many scripts and venv entrypoints use `/mnt/d/_ai_brain`.

## Compatibility Links Required

Yes.

Recommended compatibility links:

- `D:\_ai_brain` -> `D:\Local_AI_Workstation\control_plane`
- `D:\ollama\models` -> `D:\Local_AI_Workstation\models\ollama`

Without the first link, `ws`, WSL aliases, scripts, registry references, Graphify venv entrypoints, and old run artifacts are likely to break.

Without the second link, Ollama may not find models until `OLLAMA_MODELS` is updated and all Ollama processes are restarted.

## Migration Risks

High-risk items:

- Moving `D:\_ai_brain` while `ws` depends on `/mnt/d/_ai_brain`.
- Moving venvs created under `/mnt/d/_ai_brain`; Python venv scripts often embed their creation path.
- Creating a junction requires the original `D:\_ai_brain` path to be absent, so the move and link must be atomic enough to avoid downtime.
- `OLLAMA_MODELS` is set to `D:\ollama\models`; moving models without stopping Ollama can break model discovery.
- `hermes3:8b` is currently loaded; model storage should not be moved while any model is loaded.
- Some generated artifacts under `graphify-out`, `runs`, `build_runs`, cleanup archives, and frontier responses embed old paths. These are historical and should not drive the migration, but they mean hardcoded-path scans will remain noisy.
- Updating machine-level environment variables may require elevated permissions or a new shell/session.

## Recommended Migration Strategy

Do not move immediately. Use a staged migration:

1. Create `D:\Local_AI_Workstation` target folders only after this report is reviewed.
2. Stop active model usage and unload Ollama models:
   ```bash
   ws unload
   curl http://localhost:11434/api/ps
   ```
3. Stop the Windows Ollama service/app before moving model storage.
4. Copy, do not move, `D:\_ai_brain` to `D:\Local_AI_Workstation\control_plane` first.
5. Validate copied control plane read-only.
6. Rename original `D:\_ai_brain` to a timestamped backup only when ready.
7. Create junction:
   ```powershell
   cmd /c mklink /J D:\_ai_brain D:\Local_AI_Workstation\control_plane
   ```
8. Validate old path still works:
   ```bash
   source ~/.bashrc
   ws help
   ws projects
   ws model
   ws kv
   ws frontier
   ```
9. Only after control-plane validation, handle Ollama models separately.
10. For models, prefer copy/rename/link only while Ollama is stopped:
    ```powershell
    [Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "D:\Local_AI_Workstation\models\ollama", "User")
    cmd /c mklink /J D:\ollama\models D:\Local_AI_Workstation\models\ollama
    ```
11. Restart Ollama and validate:
    ```bash
    curl http://localhost:11434/api/tags
    ```

## Recommendation

Stop here for now. The working system should not be moved until a dedicated migration window, with Ollama stopped and an explicit rollback plan ready.

Next safe step is Phase 2 only: create the target folder skeleton and README, without moving control-plane or model files.
