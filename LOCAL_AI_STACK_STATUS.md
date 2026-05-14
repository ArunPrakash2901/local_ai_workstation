# Local AI Stack Status

## Overview
This machine has been configured as an optimized local AI development workstation. The focus is on stable, responsive inference for 7B-14B models, integrated tightly with Graphify for codebase intelligence.

## Hardware & Environment
- **CPU**: Intel Core i9-13900HX (24C/32T)
- **RAM**: 64GB DDR5
- **GPU**: NVIDIA RTX 4070 Laptop (8GB VRAM)
- **OS**: Windows 11 + WSL2 (Ubuntu, Mirrored Networking mode)

## Storage & Paths
- **Control Centre**: `D:\_ai_brain`
- **Models Path**: `D:\ollama\models`
- **Graphify Global Graph**: `~/.graphify/global-graph.json` (inside WSL)
- **Available Drive Space**: ~26GB on C: (WARNING: Low), ~408GB on D:

## Core Stack
- **Runtime**: Ollama v0.23.0
- **Model**: `hermes3:8b` (Q4_0)
- **Knowledge Graph**: Graphify (installed in WSL isolated venv)
- **Networking**: Ollama bound to `0.0.0.0:11434`, accessible via `localhost:11434` in WSL.

## Performance Profile (8k Context)
- **Speed**: ~50 tokens/second
- **VRAM**: ~6.2 GB loaded
- **Prompt Caching**: Active & highly effective
- **Flash Attention**: Active (`OLLAMA_FLASH_ATTENTION=1`)
- **Model Retention**: 30 minutes (`OLLAMA_KEEP_ALIVE=30m`)

## Optional Engines (Evaluated but Skipped)
- **llama.cpp**: Skipped. Ollama handles our llama.cpp abstraction perfectly.
- **ExLlama/TabbyAPI**: Skipped. Unnecessary maintenance overhead for marginal speed gains.
- **vLLM**: Skipped. 8GB VRAM is insufficient for vLLM's memory allocation model.

## Graphify Status
- **Installation**: Active in `D:\_ai_brain\runtimes\graphify_venv`
- **Global Graph**: Active. Projects indexed:
  - `portfolio_website` (372 nodes)
  - `GSP` (7 nodes)
  - `LLM-engineer-handbook` (7 nodes)
  - `Melbourne-Oil-Scarcity-outlook` (6 nodes)
  - `Simulation` (32 nodes)
- **Safety**: `D:\.graphifyignore` explicitly blocks raw data (.csv, .db, .parquet), media, secrets, weights, and caches.

## Quant & Product Workflow Support
### Quant Workflow
This setup supports feature engineering, EDA, and strategy backtesting. By leveraging Graphify on your strategy repositories (e.g., `GSP`, `Simulation`), the AI can comprehend your pipeline structure. 
**Rule**: Never inspect broker keys or real credentials. Raw data files (.csv, .parquet) are blocked by `.graphifyignore` to prevent graph bloat. Use the AI to reason about the *logic* (Python/R files), not the *raw datasets*.

### Product Workflow
For projects like `portfolio_website`, Graphify mapped 372 nodes across components, hooks, and utilities. The AI can now trace dependencies natively (e.g., how `useScroll` is used).
**Rule**: Never inspect production `.env` files. Ensure you run `graphify update .` locally when making massive architectural changes.

## Cloud & Escalation Rules
- **Rule 1**: Cloud AI (Gemini/Claude) is for **hard reasoning only**, not for large corpus dumps.
- **Rule 2**: When escalating to Cloud AI, provide compressed Graphify summaries (`graphify explain <module>`), do not upload raw private folders.
- **Hardware Upgrade**: Do not upgrade right now. Your CPU/RAM is top-tier. Your 8GB GPU is the only bottleneck. Consider upgrading to an RTX 3090/4090 Desktop/Server *only* if the 8GB VRAM becomes a daily blocker for larger context windows. Do not buy Jetson devices or eGPUs.

## Bounded Build Loop Status
- **Command**: `ws build <project_key> <task_file> [flags]`
- **Default**: `--plan-only`, no project file modifications.
- **Apply Mode**: `--apply --branch` allows bounded changes only when a guarded unified diff is available.
- **Escalation**: Codex can be used only with explicit `--escalate codex`; Gemini remains manual packet review only; Claude is disabled.
- **Run Artifacts**: `D:\_ai_brain\build_runs\<timestamp>_<project>_<task>`.
- **Safety**: No deletes, no deploys, no migrations, no secrets/raw datasets/model files, no dependency installs unless a future task explicitly permits and the guard is extended.

## Task Lifecycle Status
- **Canonical Folders**: `D:\_ai_brain\tasks\inbox`, `active`, `generated`, `reviewed`, `completed`, `blocked`.
- **Commands**: `ws task-new`, `ws task-split`, `ws task-status`, `ws task-next`, `ws task-review`, `ws task-complete`, `ws task-block`.
- **Rule**: `ws build` does not auto-complete tasks. Completion/blocking requires explicit lifecycle commands.
- **Review Packets**: `ws task-review <task> --with codex` creates/redacts a packet only; sending still requires explicit `ws escalate codex latest`.

## Closed-Loop Auto Runner Status
- **Command**: `ws auto <project_key> <task_file> [flags]`
- **Default**: bounded local planning and apply loop with no auto-commit or auto-push.
- **Apply Mode**: `--apply --branch` allows guarded changes only when the task stays within file limits and safety checks.
- **Escalation**: Codex is explicit only with `--auto-escalate codex`; Gemini stays manual packet review only; Claude is disabled.
- **Artifacts**: `D:\_ai_brain\auto_runs\<timestamp>_<project>_<task>`.
- **Safety**: no deletes, no deploys, no model warmups, no qwen2.5:32b automatic use, no secrets/raw datasets/model files, no dependency installs unless explicitly allowed by a future task.
