# WS CRLF / WSL Compatibility Repair Report

Date: 2026-05-14
Scope: `D:\_ai_brain\scripts` and WSL `~/.bashrc` only.

## Files Converted From CRLF To LF

None required. All target WSL shell scripts under `D:\_ai_brain\scripts` scanned as LF during this repair.

Target set checked:

- all `.sh` files under `D:\_ai_brain\scripts`
- extensionless shell script: `ws`
- PowerShell `.ps1` files were not modified

Final WSL CR check: no carriage returns found in target shell scripts.

## Scripts Made Executable

The executable bit was applied/verified for all `.sh` scripts and `ws` under `D:\_ai_brain\scripts`, including:

- `ws`
- `ai_ask.sh`
- `ai_daily_restore.sh`
- `ai_model_current.sh`
- `ai_models.sh`
- `ai_kv_profiles.sh`
- `benchmark_ollama.sh`
- `benchmark_ollama_v2.sh`
- `ws_frontier_status.sh`
- `ws_make_packet.sh`
- `ws_redact_packet.sh`

## `ws help`

Pass.

Validated with:

```bash
bash /mnt/d/_ai_brain/scripts/ws help
source ~/.bashrc
ws help
```

Both paths showed help output without CRLF errors.

## `ws` Alias

Pass.

WSL `~/.bashrc` contains exactly one `ws` alias:

```bash
alias ws='bash /mnt/d/_ai_brain/scripts/ws'
```

## Existing AI Aliases

Pass. Existing aliases were present/repaired in `~/.bashrc`:

- `ailist`
- `aiproj`
- `aiask`
- `aiglobal`
- `aimodels`
- `aimodel`
- `aiuse`
- `aikv`
- `aidaily`

Additional workstation aliases restored: `aigraph`, `aiaudit`, `aidebug`, `aitask`, `aipullmodel`, `aibenchmodel`, `aiwarmmodel`, `aiunloadmodel`, `aikvuse`.

## Safe Command Validation

Pass.

Validated only these safe commands:

```bash
ws help
ws projects
ws model
ws kv
```

Current safe state:

- active profile: `hermes_default`
- active model: `hermes3:8b`
- mode: `daily`
- active KV profile: `stable_default`
- KV type: `default`
- context: `8192` model / `8192` KV

## Safe Daily Restore

Pass.

`ws daily` exists and was run. It restored `hermes_default`, `hermes3:8b`, `stable_default` KV, and `8192` context.

It did not reference or warm `qwen2.5:32b`. It requested an unload using `hermes3:8b` with `keep_alive=0` and left Ollama with no loaded models according to `/api/ps`.

## Ollama Access From WSL

Pass.

Ollama is reachable from WSL via HTTP:

```bash
curl http://localhost:11434/api/tags
curl http://localhost:11434/api/ps
```

The `ollama` CLI was not found in WSL, which is acceptable because Ollama is installed on Windows and the HTTP API is reachable.

Loaded models from `/api/ps` after daily restore:

```json
{"models":[]}
```

No 32B model was loaded.

## Scripts Still Failing

None found during the requested safe validation.

## Commands To Run Next

Open a new WSL shell, or run:

```bash
source ~/.bashrc
```

Then verify manually:

```bash
ws help
ws projects
ws model
ws kv
curl http://localhost:11434/api/ps
```

Do not run benchmarks, big-model warmups, or frontier escalation commands unless you intentionally choose to later.
